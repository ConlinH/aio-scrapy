import asyncio
import logging
import pprint
import signal
import sys
import warnings
from typing import Optional

from zope.interface.exceptions import DoesNotImplement

try:
    # zope >= 5.0 only supports MultipleInvalid
    from zope.interface.exceptions import MultipleInvalid
except ImportError:
    MultipleInvalid = None

from zope.interface.verify import verifyClass
from aioscrapy import signals, Spider
from aioscrapy.settings import overridden_settings
from aioscrapy.utils.log import (
    get_scrapy_root_handler,
    install_scrapy_root_handler,
    LogCounterHandler,
    configure_logging,
)
from aioscrapy.utils.misc import load_object, load_instance
from aioscrapy.spiderloader import ISpiderLoader
from aioscrapy.exceptions import AioScrapyDeprecationWarning
from aioscrapy.db import db_manager

from aioscrapy.utils.tools import async_generator_wrapper
from aioscrapy.middleware import ExtensionManager
from aioscrapy.core.engine import ExecutionEngine
from aioscrapy.settings import Settings
from aioscrapy.signalmanager import SignalManager
from aioscrapy.utils.ossignal import install_shutdown_handlers, signal_names
from aioscrapy.statscollectors import StatsCollector

logger = logging.getLogger(__name__)


class Crawler:

    def __init__(self, spidercls, settings=None):

        if isinstance(spidercls, Spider):
            raise ValueError('The spidercls argument must be a class, not an object')

        if isinstance(settings, dict) or settings is None:
            settings = Settings(settings)

        self.spidercls: Spider = spidercls
        self.settings = settings.copy()
        self.spidercls.update_settings(self.settings)

        self.settings.freeze()
        self.signals: Optional[SignalManager] = None
        self.stats: Optional[StatsCollector] = None
        self.crawling = False
        self.spider: Optional[Spider] = None
        self.engine: Optional[ExecutionEngine] = None
        self.extensions: Optional[ExecutionEngine] = None
        self.logformatter: Optional[ExecutionEngine] = None

    async def crawl(self, *args, **kwargs):
        try:
            if self.crawling:
                raise RuntimeError("Crawling already taking place")

            self.crawling = True
            self.signals = SignalManager(self)
            self.stats = load_object(self.settings['STATS_CLASS'])(self)

            handler = LogCounterHandler(self, level=self.settings.get('LOG_LEVEL'))
            logging.root.addHandler(handler)

            d = dict(overridden_settings(self.settings))
            logger.info("Overridden settings:\n%(settings)s", {'settings': pprint.pformat(d)})

            if get_scrapy_root_handler() is not None:
                install_scrapy_root_handler(self.settings)
            self.signals.connect(lambda: logging.root.removeHandler(handler), signals.engine_stopped)

            self.spider = await self.spidercls.from_crawler(self, *args, **kwargs)
            self.logformatter = await load_instance(self.settings['LOG_FORMATTER'], crawler=self)
            self.extensions = await ExtensionManager.from_crawler(self)
            self.engine = ExecutionEngine(self)
            # 创建所有数据库链接
            await db_manager.from_crawler(self)
            start_requests = await async_generator_wrapper(self.spider.start_requests())
            await self.engine.start(self.spider, start_requests)
        except Exception as e:
            logger.exception(e)
            self.crawling = False
            if self.engine is not None:
                await self.engine.close()
            raise e

    async def stop(self):
        """Starts a graceful stop of the crawler and returns a deferred that is
        fired when the crawler is stopped."""
        if self.crawling:
            self.crawling = False
            await self.engine.stop()


class CrawlerRunner:
    crawlers = property(
        lambda self: self._crawlers,
        doc="Set of :class:`crawlers <scrapy.crawler.Crawler>` started by "
            ":meth:`crawl` and managed by this class."
    )

    @staticmethod
    def _get_spider_loader(settings):
        """ Get SpiderLoader instance from settings """
        cls_path = settings.get('SPIDER_LOADER_CLASS')
        loader_cls = load_object(cls_path)
        excs = (DoesNotImplement, MultipleInvalid) if MultipleInvalid else DoesNotImplement
        try:
            verifyClass(ISpiderLoader, loader_cls)
        except excs as e:
            warnings.warn(
                'SPIDER_LOADER_CLASS (previously named SPIDER_MANAGER_CLASS) does '
                'not fully implement scrapy.interfaces.ISpiderLoader interface. '
                'Please add all missing methods to avoid unexpected runtime errors.',
                category=AioScrapyDeprecationWarning, stacklevel=2
            )
        return loader_cls.from_settings(settings.frozencopy())

    def __init__(self, settings=None):
        if isinstance(settings, dict) or settings is None:
            settings = Settings(settings)
        self.settings = settings
        self.spider_loader = self._get_spider_loader(settings)
        self._crawlers = {}
        self._active = set()
        self.bootstrap_failed = False

    @property
    def spiders(self):
        warnings.warn("CrawlerRunner.spiders attribute is renamed to "
                      "CrawlerRunner.spider_loader.",
                      category=AioScrapyDeprecationWarning, stacklevel=2)
        return self.spider_loader

    def crawl_soon(self, crawler_or_spidercls, *args, settings=None, **kwargs):
        crawler = self.crawl(crawler_or_spidercls, settings=settings)
        self.crawlers.setdefault(crawler, (args, kwargs))
        self.active_crawler(crawler, *args, **kwargs)

    def active_crawler(self, crawler, *args, **kwargs):
        task = asyncio.create_task(crawler.crawl(*args, **kwargs))
        self._active.add(task)

        def _done(result):
            self.crawlers.pop(crawler, None)
            self._active.discard(task)
            self.bootstrap_failed |= not getattr(crawler, 'spider', None)
            return result

        task.add_done_callback(_done)

    def crawl(self, crawler_or_spidercls, *args, settings=None, **kwargs):
        if isinstance(crawler_or_spidercls, Spider):
            raise ValueError(
                'The crawler_or_spidercls argument cannot be a spider object, '
                'it must be a spider class (or a Crawler object)')
        crawler = self.create_crawler(crawler_or_spidercls, settings or self.settings)
        self.crawlers.setdefault(crawler, (args, kwargs))
        return crawler

    def create_crawler(self, crawler_or_spidercls, settings):
        if isinstance(crawler_or_spidercls, Spider):
            raise ValueError(
                'The crawler_or_spidercls argument cannot be a spider object, '
                'it must be a spider class (or a Crawler object)')
        if isinstance(crawler_or_spidercls, Crawler):
            return crawler_or_spidercls
        return self._create_crawler(crawler_or_spidercls, settings)

    def _create_crawler(self, spidercls, settings):
        if isinstance(spidercls, str):
            spidercls = self.spider_loader.load(spidercls)
        return Crawler(spidercls, settings=settings)

    async def stop(self):
        return await asyncio.gather(*[c.stop() for c in self.crawlers])


class CrawlerProcess(CrawlerRunner):

    def __init__(self, settings=None, install_root_handler=True):
        super().__init__(settings)
        install_shutdown_handlers(self._signal_shutdown)
        configure_logging(self.settings, install_root_handler)

    def _signal_shutdown(self, signum, _):
        install_shutdown_handlers(self._signal_kill)
        signame = signal_names[signum]
        logger.info("Received %(signame)s, shutting down gracefully. Send again to force ",
                    {'signame': signame})
        asyncio.create_task(self._graceful_stop_reactor())

    def _signal_kill(self, signum, _):
        install_shutdown_handlers(signal.SIG_IGN)
        signame = signal_names[signum]
        logger.info('Received %(signame)s twice, forcing unclean shutdown',
                    {'signame': signame})
        asyncio.create_task(self._stop_reactor())

    async def run(self):
        for crawler, (args, kwargs) in self.crawlers.items():
            self.active_crawler(crawler, *args, **kwargs)
        while self._active:
            await asyncio.gather(*self._active)
        await self.recycle_db_connect()

    def start(self):
        if sys.platform.startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        else:
            try:
                import uvloop
                asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            except ImportError:
                pass
        asyncio.run(self.run())

    async def _graceful_stop_reactor(self):
        await self.stop()
        await self.recycle_db_connect()

    async def _stop_reactor(self):
        try:
            await self.recycle_db_connect()
        finally:
            asyncio.get_event_loop().stop()

    async def recycle_db_connect(self):
        # 回收所以的链接
        if not len(self._active):
            await db_manager.close_all()
