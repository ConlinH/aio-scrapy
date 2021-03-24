import logging
import pprint
import asyncio

from scrapy import signals, Spider
from aioscrapy.middleware import ExtensionManager
from scrapy.settings import overridden_settings
from scrapy.utils.log import (
    get_scrapy_root_handler,
    install_scrapy_root_handler,
    LogCounterHandler,
)
from scrapy.utils.misc import load_object

from aioscrapy.core.engine import ExecutionEngine
from aioscrapy.settings import AioSettings
from aioscrapy.signalmanager import SignalManager
from aioscrapy.utils.ossignal import install_shutdown_handlers

logger = logging.getLogger(__name__)


class Crawler:

    def __init__(self, spidercls, settings=None):
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
        install_shutdown_handlers(self.stop_helper)
        self.settings.freeze()
        self.crawling = False
        self.spider = None
        self.engine = None

    async def crawl(self, *args, **kwargs):
        if self.crawling:
            raise RuntimeError("Crawling already taking place")
        self.crawling = True

        try:
            self.spider = self._create_spider(*args, **kwargs)
            self.engine = self._create_engine()
            start_requests = iter(self.spider.start_requests())
            # await self.engine.open_spider(self.spider, start_requests)
            await self.engine.start(self.spider, start_requests)
        except Exception as e:
            self.crawling = False
            if self.engine is not None:
                await self.engine.close()
            raise

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

    def stop_helper(self, *arg, **kw):
        asyncio.create_task(self.stop())