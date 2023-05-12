import asyncio
import sys
from typing import Optional, Tuple, List, Union, Type, AnyStr

from aiomultiprocess import Process

from aioscrapy import Spider
from aioscrapy.crawler import CrawlerProcess
from aioscrapy.settings import Settings


def loop_initializer():
    if sys.platform.startswith('win'):
        return asyncio.windows_events.ProactorEventLoop()
    try:
        import uvloop
        return uvloop.EventLoopPolicy()
    except ImportError:
        pass

    return asyncio.new_event_loop()


def multi_process_run(*tasks: Union[Tuple[Type[Spider], Optional[AnyStr]], List]):
    for task in tasks:
        if isinstance(task, list):
            p = Process(target=_single_process_run_async, args=(*task,), loop_initializer=loop_initializer)
        else:
            p = Process(target=_single_process_run_async, args=(task,), loop_initializer=loop_initializer)
        p.start()


async def _single_process_run_async(*tasks: Tuple[Type[Spider], Optional[AnyStr]]):
    cp = CrawlerProcess()
    for spidercls, settings in tasks:
        if isinstance(settings, str):
            instance = Settings()
            instance.setmodule(settings)
            settings = instance
        cp.crawl(spidercls, settings=settings)
    await cp.run()


def single_process_run(*tasks: Tuple[Type[Spider], Optional[AnyStr]]):
    cp = CrawlerProcess()
    for spidercls, settings in tasks:
        if isinstance(settings, str):
            instance = Settings()
            instance.setmodule(settings)
            settings = instance
        cp.crawl(spidercls, settings=settings)
    cp.start()
