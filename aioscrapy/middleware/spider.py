"""
Spider Middleware manager

See documentation in docs/topics/spider-middleware.rst
"""
from itertools import islice
from typing import AsyncIterable, Iterable, Callable, Union

from aioscrapy.exceptions import _InvalidOutput
from aioscrapy.utils.conf import build_component_list

from aioscrapy.http import Request, Response
from aioscrapy import Spider
from aioscrapy.settings import Settings
from aioscrapy.utils.tools import async_generator_wrapper
from aioscrapy.utils.tools import call_helper
from aioscrapy.middleware.absmanager import AbsMiddlewareManager


def _fname(f):
    return "{}.{}".format(
        f.__self__.__class__.__name__,
        f.__func__.__name__
    )


class SpiderMiddlewareManager(AbsMiddlewareManager):
    component_name = 'spider middleware'

    @classmethod
    def _get_mwlist_from_settings(cls, settings: Settings):
        return build_component_list(settings.getwithbase('SPIDER_MIDDLEWARES'))

    def _add_middleware(self, mw):
        super(SpiderMiddlewareManager, self)._add_middleware(mw)
        if hasattr(mw, 'process_spider_input'):
            self.methods['process_spider_input'].append(mw.process_spider_input)
        if hasattr(mw, 'process_start_requests'):
            self.methods['process_start_requests'].appendleft(mw.process_start_requests)
        process_spider_output = getattr(mw, 'process_spider_output', None)
        self.methods['process_spider_output'].appendleft(process_spider_output)
        process_spider_exception = getattr(mw, 'process_spider_exception', None)
        self.methods['process_spider_exception'].appendleft(process_spider_exception)

    async def scrape_response(self, scrape_func: Callable, response: Response, request: Request, spider: Spider):

        async def process_spider_input(response_) -> Union[AsyncIterable, Iterable]:
            for method in self.methods['process_spider_input']:
                try:
                    result = await call_helper(method, response=response_, spider=spider)
                    if result is not None:
                        raise _InvalidOutput(
                            f"Middleware {_fname(method)} must return None or raise an exception, got {type(result)}"
                        )
                except _InvalidOutput:
                    raise
                except BaseException as exception:
                    iterable_or_exception = await call_helper(scrape_func, exception, request)
                    if iterable_or_exception is exception:
                        raise iterable_or_exception
                    return iterable_or_exception
            return await call_helper(scrape_func, response_, request)

        async def _evaluate_iterable(result: Union[AsyncIterable, Iterable], exception_processor_index):
            try:
                # 将所有非AsyncGeneratorType变成AsyncGeneratorType对象
                async for r in await async_generator_wrapper(result):
                    yield r
            except BaseException as ex:
                exception_result = await process_spider_exception(ex, exception_processor_index)
                if isinstance(exception_result, BaseException):
                    raise exception_result
                async for r in _evaluate_iterable(exception_result, exception_processor_index):
                    yield r

        async def process_spider_exception(exception, start_index=0):
            # don't handle _InvalidOutput exception
            if isinstance(exception, _InvalidOutput):
                raise exception
            method_list = islice(self.methods['process_spider_exception'], start_index, None)
            for method_index, method in enumerate(method_list, start=start_index):
                if method is None:
                    continue
                result = await call_helper(method, response=response, exception=exception, spider=spider)
                if isinstance(result, AsyncIterable):
                    # stop exception handling by handing control over to the
                    # process_spider_output chain if an iterable has been returned
                    return await process_spider_output(result, method_index + 1)
                elif result is None:
                    continue
                else:
                    raise _InvalidOutput(
                            f"Middleware {_fname(method)}  must return None or an iterable, got {type(result)}"
                        )
            raise exception

        async def process_spider_output(result, start_index=0):
            # items in this iterable do not need to go through the process_spider_output
            # chain, they went through it already from the process_spider_exception method

            method_list = islice(self.methods['process_spider_output'], start_index, None)
            for method_index, method in enumerate(method_list, start=start_index):
                if method is None:
                    continue
                try:
                    # might fail directly if the output value is not a generator
                    result = await call_helper(method, response=response, result=result, spider=spider)
                except BaseException as ex:
                    exception_result = await process_spider_exception(ex, method_index + 1)
                    if isinstance(exception_result, BaseException):
                        raise
                    return exception_result
                if isinstance(result, AsyncIterable):
                    result = _evaluate_iterable(result, method_index + 1)
                else:
                    raise _InvalidOutput(f"Middleware {_fname(method)} must return an iterable, got {type(result)}")

            return result

        async def process_callback_output(result: Union[AsyncIterable, Iterable]):
            result: AsyncIterable = _evaluate_iterable(result, 0)
            return await process_spider_output(result)

        try:
            _iterable = await process_spider_input(response)
        except BaseException as exc:
            return await process_spider_exception(exc)
        else:
            return await process_callback_output(_iterable)

    async def process_start_requests(self, start_requests, spider):
        return await self._process_chain('process_start_requests', start_requests, spider)
