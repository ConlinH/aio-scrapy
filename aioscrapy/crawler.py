import logging
import pprint
import warnings
import asyncio
import signal
import sys

from zope.interface.exceptions import DoesNotImplement

try:
    # zope >= 5.0 only supports MultipleInvalid
    from zope.interface.exceptions import MultipleInvalid
except ImportError:
    MultipleInvalid = None

from zope.interface.verify import verifyClass
from scrapy import signals, Spider
from scrapy.settings import overridden_settings
from scrapy.utils.log import (
    get_scrapy_root_handler,
    install_scrapy_root_handler,
    LogCounterHandler,
    configure_logging,
)
from scrapy.utils.misc import load_object
from scrapy.interfaces import ISpiderLoader
from scrapy.exceptions import ScrapyDeprecationWarning

from aioscrapy.middleware import ExtensionManager
from aioscrapy.core.engine import ExecutionEngine
from aioscrapy.settings import AioSettings
from aioscrapy.signalmanager import SignalManager
from aioscrapy.utils.ossignal import install_shutdown_handlers, signal_names

logger = logging.getLogger(__name__)

_crawlers = {}


class Crawler:

    def __init__(self, spidercls, *args, settings=None, **kwargs):
        if isinstance(spidercls, Spider):
            raise ValueError('The spidercls argument must be a class, not an object')

        if isinstance(settings, dict) or settings is None:
            settings = AioSettings(settings)

        self.spidercls = spidercls
        self.settings = settings.copy()
        self.spidercls.update_settings(self.settings)

        self.signals = SignalManager(self)
        self.stats = load_object(self.settings['STATS_CLASS'])(self)

        handler = LogCounterHandler(self, level=self.settings.get('LOG_LEVEL'))
        logging.root.addHandler(handler)

        d = dict(overridden_settings(self.settings))
        logger.info("Overridden settings:\n%(settings)s",
                    {'settings': pprint.pformat(d)})

        if get_scrapy_root_handler() is not None:
            install_scrapy_root_handler(self.settings)
        self.__remove_handler = lambda: logging.root.removeHandler(handler)
        self.signals.connect(self.__remove_handler, signals.engine_stopped)

        lf_cls = load_object(self.settings['LOG_FORMATTER'])
        self.logformatter = lf_cls.from_crawler(self)
        self.extensions = ExtensionManager.from_crawler(self)
        self.settings.freeze()
        self.crawling = False
        self.spider = self._create_spider(*args, **kwargs)
        self.engine = None

    async def crawl(self):
        if self.crawling:
            raise RuntimeError("Crawling already taking place")
        self.crawling = True

        try:
            self.engine = self._create_engine()
            start_requests = iter(self.spider.start_requests())
            # await self.engine.open_spider(self.spider, start_requests)
            await self.engine.start(self.spider, start_requests)
        except Exception as e:
            logger.exception(e)
            self.crawling = False
            if self.engine is not None:
                await self.engine.close()
            raise e

    def _create_spider(self, *args, **kwargs):
        return self.spidercls.from_crawler(self, *args, **kwargs)

    def _create_engine(self):
        return ExecutionEngine(self, self.stop)

    async def stop(self):
        """Starts a graceful stop of the crawler and returns a deferred that is
        fired when the crawler is stopped."""
        if self.crawling:
            self.crawling = False
            await self.engine.stop()


class CrawlerRunner:

    @staticmethod
    def _get_spider_loader(settings):
        """ Get SpiderLoader instance from settings """
        cls_path = settings.get('SPIDER_LOADER_CLASS')
        loader_cls = load_object(cls_path)
        excs = (DoesNotImplement, MultipleInvalid) if MultipleInvalid else DoesNotImplement
        try:
            verifyClass(ISpiderLoader, loader_cls)
        except excs:
            warnings.warn(
                'SPIDER_LOADER_CLASS (previously named SPIDER_MANAGER_CLASS) does '
                'not fully implement scrapy.interfaces.ISpiderLoader interface. '
                'Please add all missing methods to avoid unexpected runtime errors.',
                category=ScrapyDeprecationWarning, stacklevel=2
            )
        return loader_cls.from_settings(settings.frozencopy())

    def __init__(self, settings=None):
        if isinstance(settings, dict) or settings is None:
            settings = AioSettings(settings)
        self.settings = settings
        self.spider_loader = self._get_spider_loader(settings)
        self.bootstrap_failed = False

    @property
    def spiders(self):
        warnings.warn("CrawlerRunner.spiders attribute is renamed to "
                      "CrawlerRunner.spider_loader.",
                      category=ScrapyDeprecationWarning, stacklevel=2)
        return self.spider_loader

    def create_crawler(self, crawler_or_spidercls, *args, **kwargs):
        if isinstance(crawler_or_spidercls, Spider):
            raise ValueError(
                'The crawler_or_spidercls argument cannot be a spider object, '
                'it must be a spider class (or a Crawler object)')
        if isinstance(crawler_or_spidercls, Crawler):
            return crawler_or_spidercls
        return self._create_crawler(crawler_or_spidercls, *args, **kwargs)

    def _create_crawler(self, spidercls, *args, **kwargs):
        if isinstance(spidercls, str):
            spidercls = self.spider_loader.load(spidercls)
        return Crawler(spidercls, *args, settings=self.settings, **kwargs)

    @staticmethod
    async def stop():
        return await asyncio.gather(*[c.stop() for c in _crawlers.values()])


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

    def run_crawler(self, crawler_or_spidercls, *args, **kwargs):
        if isinstance(crawler_or_spidercls, Spider):
            raise ValueError(
                'The crawler_or_spidercls argument cannot be a spider object, '
                'it must be a spider class (or a Crawler object)')
        crawler = self.crawl(crawler_or_spidercls, *args, **kwargs)
        asyncio.create_task(crawler.crawl())

    def crawl(self, crawler_or_spidercls, *args, **kwargs):
        crawler = _crawlers.get(crawler_or_spidercls)
        if crawler:
            return crawler
        crawler = self.create_crawler(crawler_or_spidercls, *args, **kwargs)
        return _crawlers.setdefault(crawler_or_spidercls, crawler)

    async def run(self):
        await asyncio.gather(*[crawler.crawl() for crawler in _crawlers.values()])
        await self.recycle_db_connect()

    def start(self):
        if not sys.platform.startswith('win'):
            try:
                import uvloop
                asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            except:
                pass
        asyncio.run(self.run())

    async def _graceful_stop_reactor(self):
        await self.stop()
        await self.recycle_db_connect()

    async def _stop_reactor(self, _=None):
        try:
            asyncio.get_event_loop().stop()
        except RuntimeError:
            pass

    @staticmethod
    async def recycle_db_connect():
        # 回收所以的链接
        from aioscrapy.connection import redis_manager, mysql_manager
        await redis_manager.close_all()
        await mysql_manager.close_all()
