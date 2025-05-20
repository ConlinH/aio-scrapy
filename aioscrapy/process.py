"""
Process Management Module
进程管理模块

This module provides functions for running spiders in single or multiple processes.
It handles the creation and management of processes, as well as the initialization
of event loops appropriate for different platforms.
此模块提供了在单个或多个进程中运行爬虫的函数。它处理进程的创建和管理，
以及适合不同平台的事件循环的初始化。

The main functions are:
主要函数包括：

1. single_process_run: Run multiple spiders in a single process
                      在单个进程中运行多个爬虫
2. multi_process_run: Run multiple spiders in separate processes
                     在单独的进程中运行多个爬虫
3. loop_initializer: Initialize an appropriate event loop based on the platform
                    根据平台初始化适当的事件循环

This module is particularly useful for running multiple spiders concurrently,
either in the same process or in separate processes for better isolation and
resource utilization.
此模块对于并发运行多个爬虫特别有用，可以在同一进程中运行，也可以在单独的
进程中运行，以获得更好的隔离和资源利用。
"""
import asyncio
import sys
from typing import Optional, Tuple, List, Union, Type, AnyStr

from aiomultiprocess import Process

from aioscrapy import Spider
from aioscrapy.crawler import CrawlerProcess
from aioscrapy.settings import Settings


def loop_initializer():
    """
    Initialize and return an appropriate event loop based on the platform.
    根据平台初始化并返回适当的事件循环。

    This function selects the most efficient event loop implementation available
    for the current platform:
    此函数为当前平台选择最高效的事件循环实现：

    - On Windows, returns a ProactorEventLoop which is optimized for Windows I/O operations.
      在Windows上，返回ProactorEventLoop，它针对Windows I/O操作进行了优化。

    - On other platforms (Linux, macOS, etc.), tries to use uvloop if available,
      which is a fast drop-in replacement for the standard asyncio event loop.
      在其他平台（Linux、macOS等）上，尝试使用uvloop（如果可用），
      它是标准asyncio事件循环的快速替代品。

    - If uvloop is not available, falls back to the standard asyncio event loop.
      如果uvloop不可用，则回退到标准asyncio事件循环。

    This function is used by the process management functions to ensure that
    each process has an appropriate and efficient event loop.
    进程管理函数使用此函数来确保每个进程都有适当且高效的事件循环。

    Returns:
        An event loop or event loop policy appropriate for the current platform.
        适合当前平台的事件循环或事件循环策略。
    """
    # On Windows, use ProactorEventLoop which supports all asyncio features
    # 在Windows上，使用支持所有asyncio功能的ProactorEventLoop
    if sys.platform.startswith('win'):
        return asyncio.windows_events.ProactorEventLoop()

    # On other platforms, try to use uvloop which is much faster
    # 在其他平台上，尝试使用更快的uvloop
    try:
        import uvloop
        return uvloop.EventLoopPolicy()
    except ImportError:
        # If uvloop is not available, use the standard event loop
        # 如果uvloop不可用，则使用标准事件循环
        pass

    # Fall back to the standard asyncio event loop
    # 回退到标准asyncio事件循环
    return asyncio.new_event_loop()


def multi_process_run(*tasks: Union[Tuple[Type[Spider], Optional[AnyStr]], List]):
    """
    Run multiple spiders in separate processes.
    在单独的进程中运行多个爬虫。

    This function creates a new process for each task or list of tasks provided.
    Each process runs independently with its own event loop, allowing for true
    parallel execution across multiple CPU cores.
    此函数为提供的每个任务或任务列表创建一个新进程。每个进程都有自己的事件循环
    独立运行，允许在多个CPU核心上实现真正的并行执行。

    Using multiple processes provides better isolation between spiders and can
    improve performance on multi-core systems, but comes with higher memory
    overhead compared to running all spiders in a single process.
    使用多个进程可以提供更好的爬虫之间的隔离，并可以在多核系统上提高性能，
    但与在单个进程中运行所有爬虫相比，会带来更高的内存开销。

    Args:
        *tasks: Each task can be either a tuple of (Spider class, settings) or a list of such tuples.
               每个任务可以是(爬虫类, 设置)的元组，或者是这种元组的列表。

               If a task is a list, all spiders in that list will run in the same process.
               如果任务是列表，则该列表中的所有爬虫将在同一进程中运行。

               The settings parameter can be a string (path to settings module) or None.
               设置参数可以是字符串（设置模块的路径）或None。

    Example:
        ```python
        # Run two spiders in separate processes
        multi_process_run(
            (MySpider1, 'myproject.settings'),
            (MySpider2, 'myproject.settings')
        )

        # Run two spiders in one process, and a third in another process
        multi_process_run(
            [(MySpider1, 'myproject.settings'), (MySpider2, 'myproject.settings')],
            (MySpider3, 'myproject.settings')
        )
        ```
    """
    # Process each task
    # 处理每个任务
    for task in tasks:
        if isinstance(task, list):
            # If task is a list, run all spiders in that list in the same process
            # 如果任务是列表，则在同一进程中运行该列表中的所有爬虫
            p = Process(target=_single_process_run_async, args=(*task,), loop_initializer=loop_initializer)
        else:
            # If task is a single spider, run it in its own process
            # 如果任务是单个爬虫，则在其自己的进程中运行它
            p = Process(target=_single_process_run_async, args=(task,), loop_initializer=loop_initializer)

        # Start the process
        # 启动进程
        p.start()


async def _single_process_run_async(*tasks: Tuple[Type[Spider], Optional[AnyStr]]):
    """
    Run multiple spiders in a single process asynchronously.
    在单个进程中异步运行多个爬虫。

    This is an internal helper function used by multi_process_run. It creates a
    CrawlerProcess, adds all the specified spiders to it, and then runs them
    concurrently within the same process.
    这是一个由multi_process_run使用的内部辅助函数。它创建一个CrawlerProcess，
    将所有指定的爬虫添加到其中，然后在同一进程中并发运行它们。

    The function handles the conversion of settings from string paths to Settings
    objects if needed.
    如果需要，该函数会处理将设置从字符串路径转换为Settings对象。

    Args:
        *tasks: Tuples of (Spider class, settings).
               (爬虫类, 设置)的元组。

               Each tuple contains a Spider class and its settings.
               每个元组包含一个爬虫类及其设置。

               The settings parameter can be a string (path to settings module) or None.
               If it's a string, it will be converted to a Settings object.
               设置参数可以是字符串（设置模块的路径）或None。
               如果是字符串，它将被转换为Settings对象。
    """
    # Create a crawler process to run all spiders
    # 创建一个爬虫进程来运行所有爬虫
    cp = CrawlerProcess()

    # Add each spider to the crawler process
    # 将每个爬虫添加到爬虫进程
    for spidercls, settings in tasks:
        # Convert string settings to Settings objects if needed
        # 如果需要，将字符串设置转换为Settings对象
        if isinstance(settings, str):
            instance = Settings()
            instance.setmodule(settings)
            settings = instance

        # Add the spider to the crawler process
        # 将爬虫添加到爬虫进程
        cp.crawl(spidercls, settings=settings)

    # Run all spiders concurrently and wait for them to finish
    # 并发运行所有爬虫并等待它们完成
    await cp.run()


def single_process_run(*tasks: Tuple[Type[Spider], Optional[AnyStr]]):
    """
    Run multiple spiders in a single process.
    在单个进程中运行多个爬虫。

    This function creates a CrawlerProcess and runs all provided spiders in it.
    The spiders run concurrently within the same process using asyncio.
    此函数创建一个CrawlerProcess并在其中运行所有提供的爬虫。
    爬虫使用asyncio在同一进程中并发运行。

    Running multiple spiders in a single process uses less memory than running
    them in separate processes, but doesn't provide the same level of isolation
    or parallel execution across CPU cores.
    在单个进程中运行多个爬虫比在单独的进程中运行它们使用更少的内存，
    但不提供相同级别的隔离或跨CPU核心的并行执行。

    Args:
        *tasks: Tuples of (Spider class, settings).
               (爬虫类, 设置)的元组。

               Each tuple contains a Spider class and its settings.
               每个元组包含一个爬虫类及其设置。

               The settings parameter can be a string (path to settings module) or None.
               If it's a string, it will be converted to a Settings object.
               设置参数可以是字符串（设置模块的路径）或None。
               如果是字符串，它将被转换为Settings对象。

    Example:
        ```python
        # Run two spiders in a single process
        single_process_run(
            (MySpider1, 'myproject.settings'),
            (MySpider2, 'myproject.settings')
        )
        ```
    """
    # Create a crawler process to run all spiders
    # 创建一个爬虫进程来运行所有爬虫
    cp = CrawlerProcess()

    # Add each spider to the crawler process
    # 将每个爬虫添加到爬虫进程
    for spidercls, settings in tasks:
        # Convert string settings to Settings objects if needed
        # 如果需要，将字符串设置转换为Settings对象
        if isinstance(settings, str):
            instance = Settings()
            instance.setmodule(settings)
            settings = instance

        # Add the spider to the crawler process
        # 将爬虫添加到爬虫进程
        cp.crawl(spidercls, settings=settings)

    # Start the crawler process and block until all spiders are finished
    # 启动爬虫进程并阻塞直到所有爬虫完成
    cp.start()
