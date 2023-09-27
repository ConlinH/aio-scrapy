import pprint
from abc import ABCMeta, abstractmethod
from collections import defaultdict, deque

from aioscrapy.exceptions import NotConfigured
from aioscrapy.utils.log import logger
from aioscrapy.utils.misc import load_instance
from aioscrapy.utils.tools import call_helper


class AbsMiddlewareManager(object, metaclass=ABCMeta):
    """Base class for implementing middleware managers"""

    component_name = 'foo middleware'

    def __init__(self, *middlewares):
        self.middlewares = middlewares
        self.methods = defaultdict(deque)
        for mw in middlewares:
            self._add_middleware(mw)

    @classmethod
    @abstractmethod
    def _get_mwlist_from_settings(cls, settings):
        """get middleware list from settings"""

    @classmethod
    async def from_settings(cls, settings, crawler=None):
        mwlist = cls._get_mwlist_from_settings(settings)
        middlewares = []
        enabled = []
        for clspath in mwlist:
            try:
                middlewares.append(await load_instance(clspath, settings=settings, crawler=crawler))
                enabled.append(clspath)
            except NotConfigured as e:
                if e.args:
                    clsname = clspath.split('.')[-1]
                    logger.warning("Disabled %(clsname)s: %(eargs)s" % {'clsname': clsname, 'eargs': e.args[0]})

        logger.info(f"Enabled {cls.component_name}s:\n{pprint.pformat(enabled)}")
        return cls(*middlewares)

    @classmethod
    async def from_crawler(cls, crawler):
        return await cls.from_settings(crawler.settings, crawler)

    def _add_middleware(self, mw):
        if hasattr(mw, 'open_spider'):
            self.methods['open_spider'].append(mw.open_spider)
        if hasattr(mw, 'close_spider'):
            self.methods['close_spider'].appendleft(mw.close_spider)

    async def _process_parallel(self, methodname, obj, *args):
        return await self.process_parallel(self.methods[methodname], obj, *args)

    async def _process_chain(self, methodname, obj, *args):
        return await self.process_chain(self.methods[methodname], obj, *args)

    async def _process_chain_both(self, cb_methodname, eb_methodname, obj, *args):
        return await self.process_chain_both(self.methods[cb_methodname],
                                             self.methods[eb_methodname], obj, *args)

    async def open_spider(self, spider):
        return await self._process_parallel('open_spider', spider)

    async def close_spider(self, spider):
        return await self._process_parallel('close_spider', spider)

    @staticmethod
    async def process_parallel(callbacks, input_, *a, **kw):
        for callback in callbacks:
            await call_helper(callback, input_, *a, **kw)

    @staticmethod
    async def process_chain(callbacks, input_, *a, **kw):
        for callback in callbacks:
            input_result = await call_helper(callback, input_, *a, **kw)
            if input_result is not None:
                input_ = input_result
        return input_

    @staticmethod
    async def process_chain_both(callbacks, errbacks, input_, *a, **kw):
        for cb, eb in zip(callbacks, errbacks):
            try:
                input_ = await call_helper(cb, input_, *a, **kw)
            except(Exception, BaseException):
                input_ = await call_helper(eb, input_, *a, **kw)
            return input_
