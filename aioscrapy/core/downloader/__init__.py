import asyncio
import logging
import random
from abc import abstractmethod
from collections import deque
from datetime import datetime
from time import time
from typing import Optional, Set, Deque, Tuple, Callable, TypeVar

from aioscrapy import signals, Request, Spider
from aioscrapy.core.downloader.handlers import DownloadHandlerManager
from aioscrapy.dupefilters import DupeFilterBase
from aioscrapy.http import Response
from aioscrapy.middleware import DownloaderMiddlewareManager
from aioscrapy.proxy import AbsProxy
from aioscrapy.settings import Settings
from aioscrapy.signalmanager import SignalManager
from aioscrapy.utils.httpobj import urlparse_cached
from aioscrapy.utils.misc import load_instance
from aioscrapy.utils.tools import call_helper

logger = logging.getLogger('aioscrapy.downloader')


class BaseDownloaderMeta(type):

    def __instancecheck__(cls, instance):
        return cls.__subclasscheck__(type(instance))

    def __subclasscheck__(cls, subclass):
        return (
                hasattr(subclass, "fetch") and callable(subclass.fetch)
                and hasattr(subclass, "needs_backout") and callable(subclass.needs_backout)
        )


class BaseDownloader(metaclass=BaseDownloaderMeta):

    @classmethod
    async def from_crawler(cls, crawler) -> "BaseDownloader":
        return cls()

    async def close(self) -> None:
        pass

    @abstractmethod
    async def fetch(self, request: Request) -> None:
        raise NotImplementedError()

    @abstractmethod
    def needs_backout(self) -> bool:
        raise NotImplementedError()


DownloaderTV = TypeVar("DownloaderTV", bound="Downloader")


class Slot:
    """Downloader slot"""

    def __init__(self, concurrency: int, delay: float, randomize_delay: bool) -> None:
        self.concurrency = concurrency
        self.delay = delay
        self.randomize_delay = randomize_delay

        self.active: Set[Request] = set()
        self.transferring: Set[Request] = set()
        self.queue: Deque[Request] = deque()
        self.lastseen: float = 0
        self.delay_lock: bool = False

    def free_transfer_slots(self):
        return self.concurrency - len(self.transferring)

    def download_delay(self) -> float:
        if self.randomize_delay:
            return random.uniform(0.5 * self.delay, 1.5 * self.delay)
        return self.delay

    def __repr__(self):
        cls_name = self.__class__.__name__
        return "%s(concurrency=%r, delay=%0.2f, randomize_delay=%r)" % (
            cls_name, self.concurrency, self.delay, self.randomize_delay)

    def __str__(self):
        return (
                "<downloader.Slot concurrency=%r delay=%0.2f randomize_delay=%r "
                "len(active)=%d len(queue)=%d len(transferring)=%d lastseen=%s>" % (
                    self.concurrency, self.delay, self.randomize_delay,
                    len(self.active), len(self.queue), len(self.transferring),
                    datetime.fromtimestamp(self.lastseen).isoformat()
                )
        )


def _get_concurrency_delay(concurrency: int, spider: Spider, settings: Settings) -> Tuple[int, float]:
    delay = settings.getfloat('DOWNLOAD_DELAY')
    if hasattr(spider, 'download_delay'):
        delay = spider.download_delay

    if hasattr(spider, 'max_concurrent_requests'):
        concurrency = spider.max_concurrent_requests

    return concurrency, delay


class Downloader(BaseDownloader):
    DOWNLOAD_SLOT: str = 'download_slot'

    def __init__(
            self,
            crawler,
            handler: DownloadHandlerManager,
            middleware: DownloaderMiddlewareManager,
            *,
            proxy: Optional[AbsProxy] = None,
            dupefilter: Optional[DupeFilterBase] = None,
    ):
        self.settings: Settings = crawler.settings
        self.signals: SignalManager = crawler.signals
        self.spider: Spider = crawler.spider
        self.spider.proxy = proxy
        self._call_engine: Callable = crawler.engine.handle_downloader_output

        self.middleware = middleware
        self.handler = handler
        self.proxy = proxy
        self.dupefilter = dupefilter

        self.total_concurrency: int = self.settings.getint('CONCURRENT_REQUESTS')
        self.domain_concurrency: int = self.settings.getint('CONCURRENT_REQUESTS_PER_DOMAIN')
        self.ip_concurrency: int = self.settings.getint('CONCURRENT_REQUESTS_PER_IP')
        self.randomize_delay: bool = self.settings.getbool('RANDOMIZE_DOWNLOAD_DELAY')

        self.active: Set[Request] = set()
        self.slots: dict = {}
        self.running: bool = True
        asyncio.create_task(self._slot_gc(60))

    @classmethod
    async def from_crawler(cls, crawler) -> "Downloader":
        return cls(
            crawler,
            await call_helper(DownloadHandlerManager.for_crawler, crawler),
            await call_helper(DownloaderMiddlewareManager.from_crawler, crawler),
            proxy=crawler.settings.get("PROXY_HANDLER") and await load_instance(crawler.settings["PROXY_HANDLER"],
                                                                                crawler=crawler),
            dupefilter=crawler.settings.get('DUPEFILTER_CLASS') and await load_instance(
                crawler.settings['DUPEFILTER_CLASS'], crawler=crawler)
        )

    async def fetch(self, request: Request) -> None:
        self.active.add(request)
        key, slot = self._get_slot(request, self.spider)
        request.meta[self.DOWNLOAD_SLOT] = key

        slot.active.add(request)
        slot.queue.append(request)
        await self._process_queue(slot)

    async def _process_queue(self, slot: Slot) -> None:
        if slot.delay_lock:
            return

        now = time()
        delay = slot.download_delay()
        if delay:
            penalty = delay - now + slot.lastseen
            if penalty > 0:
                slot.delay_lock = True
                await asyncio.sleep(penalty)
                slot.delay_lock = False
                asyncio.create_task(self._process_queue(slot))
                return

        while slot.queue and slot.free_transfer_slots() > 0:
            request = slot.queue.popleft()
            slot.transferring.add(request)
            asyncio.create_task(self._download(slot, request))
            if delay:
                break

    async def _download(self, slot: Slot, request: Request) -> None:
        result = None
        try:
            if self.dupefilter and not request.dont_filter and await self.dupefilter.request_seen(request):
                self.dupefilter.log(request, self.spider)
                return
            slot.lastseen = time()
            result = await self.middleware.process_request(self.spider, request)
            if result is None:
                self.proxy and await self.proxy.add_proxy(request)
                result = await self.handler.download_request(request, self.spider)
        except BaseException as exc:
            self.proxy and self.proxy.check(request, exception=exc)
            result = await self.middleware.process_exception(self.spider, request, exc)
        else:
            if isinstance(result, Response):
                try:
                    self.proxy and self.proxy.check(request, response=result)
                    result = await self.middleware.process_response(self.spider, request, result)
                except BaseException as exc:
                    result = exc
        finally:
            slot.transferring.remove(request)
            slot.active.remove(request)
            self.active.remove(request)
            if isinstance(result, Response):
                await self.signals.send_catch_log(signal=signals.response_downloaded,
                                                  response=result,
                                                  request=request,
                                                  spider=self.spider)
            await self._call_engine(result, request)
            await self._process_queue(slot)

    async def close(self) -> None:
        self.running = False
        self.dupefilter and await self.dupefilter.close()

    async def _slot_gc(self, age=60):
        while self.running:
            await asyncio.sleep(age)
            for key, slot in list(self.slots.items()):
                logger.debug(slot)
                if not slot.active and slot.lastseen + slot.delay < (time() - age):
                    self.slots.pop(key)

    def needs_backout(self):
        return len(self.active) >= self.total_concurrency

    def _get_slot(self, request, spider):
        key = self._get_slot_key(request, spider)
        if key not in self.slots:
            conc = self.ip_concurrency if self.ip_concurrency else self.domain_concurrency
            conc, delay = _get_concurrency_delay(conc, spider, self.settings)
            self.slots[key] = Slot(conc, delay, self.randomize_delay)
        return key, self.slots[key]

    def _get_slot_key(self, request, spider):
        if self.DOWNLOAD_SLOT in request.meta:
            return request.meta[self.DOWNLOAD_SLOT]

        if self.ip_concurrency:
            return request.meta.get("proxy", '')
        else:
            return urlparse_cached(request).hostname or ''
