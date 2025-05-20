"""
Crawler Module
爬虫模块

This module provides the core classes for managing the crawling process in AioScrapy.
It defines the Crawler, CrawlerRunner, and CrawlerProcess classes that coordinate
the execution of spiders and manage their lifecycle.
此模块提供了AioScrapy中管理爬取过程的核心类。它定义了协调爬虫执行和管理其生命周期的
Crawler、CrawlerRunner和CrawlerProcess类。

The main classes are:
主要类包括：

1. Crawler: The main class that coordinates a single crawling process
           协调单个爬取过程的主要类
2. CrawlerRunner: Manages multiple crawlers
                 管理多个爬虫
3. CrawlerProcess: Extends CrawlerRunner to run crawlers in the current process
                  扩展CrawlerRunner以在当前进程中运行爬虫

These classes handle the initialization and shutdown of all components needed for
crawling, such as the engine, extensions, signals, and database connections.
这些类处理爬取所需的所有组件的初始化和关闭，例如引擎、扩展、信号和数据库连接。
"""
import asyncio
import pprint
import signal
import sys
import warnings
from typing import Optional, Type, Union, Any

from zope.interface.exceptions import DoesNotImplement

try:
    # zope >= 5.0 only supports MultipleInvalid
    from zope.interface.exceptions import MultipleInvalid
except ImportError:
    MultipleInvalid = None

from zope.interface.verify import verifyClass
from aioscrapy.logformatter import LogFormatter
from aioscrapy import Spider
from aioscrapy.settings import overridden_settings, Settings
from aioscrapy.utils.log import configure_logging, logger
from aioscrapy.utils.misc import load_object, load_instance
from aioscrapy.spiderloader import ISpiderLoader
from aioscrapy.exceptions import AioScrapyDeprecationWarning
from aioscrapy.db import db_manager

from aioscrapy.utils.tools import async_generator_wrapper
from aioscrapy.middleware import ExtensionManager
from aioscrapy.core.engine import ExecutionEngine
from aioscrapy.signalmanager import SignalManager
from aioscrapy.utils.ossignal import install_shutdown_handlers, signal_names
from aioscrapy.statscollectors import StatsCollector


class Crawler:
    """
    The Crawler is the main class that coordinates the crawling process.
    Crawler是协调爬取过程的主要类。

    It holds references to the main components of the crawling process and manages
    their initialization and shutdown.
    它持有爬取过程中主要组件的引用，并管理它们的初始化和关闭。
    """

    def __init__(self, spidercls: Type[Spider], settings: Union[Settings, dict, None] = None) -> None:
        """
        Initialize a new Crawler.
        初始化一个新的Crawler。

        Args:
            spidercls: The Spider class to use for this crawler.
                      此爬虫使用的Spider类。
            settings: The settings to use for this crawler. Can be a Settings object,
                     a dictionary, or None (in which case default settings are used).
                     此爬虫使用的设置。可以是Settings对象、字典或None（在这种情况下使用默认设置）。

        Raises:
            ValueError: If spidercls is a Spider instance instead of a Spider class.
                       如果spidercls是Spider实例而不是Spider类。
        """
        if isinstance(spidercls, Spider):
            raise ValueError('The spidercls argument must be a class, not an object')

        if isinstance(settings, dict) or settings is None:
            settings = Settings(settings)

        self.spidercls = spidercls
        self.settings = settings.copy()
        self.spidercls.update_settings(self.settings)

        self.settings.freeze()
        self.signals: Optional[SignalManager] = None
        self.stats: Optional[StatsCollector] = None
        self.crawling = False
        self.spider: Optional[Spider] = None
        self.engine: Optional[ExecutionEngine] = None
        self.extensions: Optional[ExtensionManager] = None
        self.logformatter: Optional[LogFormatter] = None

    async def crawl(self, *args, **kwargs) -> None:
        """
        Start the crawling process.
        开始爬取过程。

        This method initializes all the components needed for crawling and starts the engine.
        此方法初始化爬取所需的所有组件并启动引擎。

        Args:
            *args: Arguments to pass to the spider's constructor.
                  传递给爬虫构造函数的参数。
            **kwargs: Keyword arguments to pass to the spider's constructor.
                     传递给爬虫构造函数的关键字参数。

        Raises:
            RuntimeError: If crawling is already taking place.
                         如果爬取已经在进行中。
            Exception: Any exception that occurs during the crawling process.
                      爬取过程中发生的任何异常。
        """
        try:
            configure_logging(self.spidercls, self.settings)

            if self.crawling:
                raise RuntimeError("Crawling already taking place")

            self.crawling = True
            self.signals = SignalManager(self)
            self.stats = load_object(self.settings['STATS_CLASS'])(self)

            logger.info(f"Overridden settings:\n{pprint.pformat(dict(overridden_settings(self.settings)))}")

            self.spider = await self.spidercls.from_crawler(self, *args, **kwargs)
            self.spider.stats = self.stats
            self.logformatter = await load_instance(self.settings['LOG_FORMATTER'], crawler=self)
            self.extensions = await ExtensionManager.from_crawler(self)
            self.engine = ExecutionEngine(self)
            # 创建所有数据库链接 (Create all database connections)
            await db_manager.from_crawler(self)
            start_requests = await async_generator_wrapper(self.spider.start_requests())
            await self.engine.start(self.spider, start_requests)
        except Exception as e:
            logger.exception(e)
            self.crawling = False
            if self.engine is not None:
                await self.engine.close()
            raise e

    async def stop(self, signum=None) -> None:
        """
        Starts a graceful stop of the crawler.
        开始优雅地停止爬虫。

        This method is called when the crawler needs to be stopped, either by user
        request or by a signal (e.g., SIGINT).
        当爬虫需要停止时调用此方法，可能是由用户请求或信号（例如SIGINT）触发。

        Args:
            signum: The signal number that triggered the stop, if any.
                   触发停止的信号编号（如果有）。
        """
        if signum is not None:
            asyncio.current_task().set_name(self.spidercls.name)
            logger.info(
                "Received  %(signame)s, shutting down gracefully. Send again to force" % {
                    'signame': signal_names[signum]
                }
            )
        if self.crawling:
            self.crawling = False
            await self.engine.stop()

    def _signal_shutdown(self, signum: Any, _) -> None:
        """
        Signal handler for shutdown signals.
        关闭信号的信号处理程序。

        This method is called when a shutdown signal (e.g., SIGINT) is received.
        当接收到关闭信号（例如SIGINT）时调用此方法。

        Args:
            signum: The signal number.
                   信号编号。
            _: The frame object (not used).
               帧对象（未使用）。
        """
        asyncio.create_task(self.stop(signum))


class CrawlerRunner:
    """
    Class that manages multiple crawlers.
    管理多个爬虫的类。

    This class keeps track of all the crawlers started by it and provides
    methods to start and stop them.
    此类跟踪由它启动的所有爬虫，并提供启动和停止它们的方法。
    """

    crawlers = property(
        lambda self: self._crawlers,
        doc="Set of crawlers started by crawl and managed by this class."
            "由crawl方法启动并由此类管理的爬虫集合。"
    )

    @staticmethod
    def _get_spider_loader(settings: Settings) -> ISpiderLoader:
        """
        Get SpiderLoader instance from settings.
        从设置中获取SpiderLoader实例。

        This method loads the spider loader class specified in the settings and
        creates an instance of it.
        此方法加载设置中指定的爬虫加载器类并创建其实例。

        Args:
            settings: The settings object.
                     设置对象。

        Returns:
            An instance of the spider loader.
            爬虫加载器的实例。

        Warns:
            AioScrapyDeprecationWarning: If the spider loader class does not fully
                                        implement the ISpiderLoader interface.
                                        如果爬虫加载器类未完全实现ISpiderLoader接口。
        """
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

    def __init__(self, settings: Union[Settings, dict, None] = None) -> None:
        """
        Initialize a new CrawlerRunner.
        初始化一个新的CrawlerRunner。

        Args:
            settings: The settings to use for this crawler runner. Can be a Settings object,
                     a dictionary, or None (in which case default settings are used).
                     此爬虫运行器使用的设置。可以是Settings对象、字典或None（在这种情况下使用默认设置）。
        """
        if isinstance(settings, dict) or settings is None:
            settings = Settings(settings)
        self.settings = settings
        self.spider_loader = self._get_spider_loader(settings)
        self._crawlers = {}  # Dictionary of crawlers and their args/kwargs
                            # 爬虫及其参数/关键字参数的字典
        self._active = set()  # Set of active crawling tasks
                             # 活动爬取任务的集合
        self.bootstrap_failed = False  # Flag indicating if bootstrap failed
                                      # 指示引导是否失败的标志

    @property
    def spiders(self):
        """
        Deprecated property that returns the spider_loader.
        已弃用的属性，返回spider_loader。

        This property is deprecated and will be removed in a future version.
        此属性已弃用，将在未来版本中删除。

        Returns:
            The spider loader instance.
            爬虫加载器实例。

        Warns:
            AioScrapyDeprecationWarning: Always warns about deprecation.
                                        始终警告关于弃用。
        """
        warnings.warn("CrawlerRunner.spiders attribute is renamed to "
                      "CrawlerRunner.spider_loader.",
                      category=AioScrapyDeprecationWarning, stacklevel=2)
        return self.spider_loader

    def crawl_soon(
            self,
            crawler_or_spidercls: Union[Type[Spider], Crawler],
            *args,
            settings: Union[Settings, dict, None] = None,
            **kwargs
    ) -> None:
        """
        Schedule a crawler to run as soon as possible.
        安排爬虫尽快运行。

        This method creates a crawler (if needed) and schedules it to run.
        此方法创建爬虫（如果需要）并安排其运行。

        Args:
            crawler_or_spidercls: A Crawler instance or a Spider class.
                                 Crawler实例或Spider类。
            *args: Arguments to pass to the spider's constructor.
                  传递给爬虫构造函数的参数。
            settings: The settings to use for this crawler. Can be a Settings object,
                     a dictionary, or None (in which case default settings are used).
                     此爬虫使用的设置。可以是Settings对象、字典或None（在这种情况下使用默认设置）。
            **kwargs: Keyword arguments to pass to the spider's constructor.
                     传递给爬虫构造函数的关键字参数。
        """
        crawler = self.crawl(crawler_or_spidercls, settings=settings)
        self.crawlers.setdefault(crawler, (args, kwargs))
        self.active_crawler(crawler, *args, **kwargs)

    def active_crawler(self, crawler: Crawler, *args, **kwargs) -> None:
        """
        Activate a crawler by creating a task for it.
        通过为爬虫创建任务来激活它。

        This method creates an asyncio task for the crawler and adds it to the
        set of active tasks.
        此方法为爬虫创建一个asyncio任务，并将其添加到活动任务集中。

        Args:
            crawler: The crawler to activate.
                    要激活的爬虫。
            *args: Arguments to pass to the crawler's crawl method.
                  传递给爬虫crawl方法的参数。
            **kwargs: Keyword arguments to pass to the crawler's crawl method.
                     传递给爬虫crawl方法的关键字参数。
        """
        task = asyncio.create_task(crawler.crawl(*args, **kwargs), name=crawler.spidercls.name)
        self._active.add(task)

        def _done(result):
            """
            Callback for when the task is done.
            任务完成时的回调。

            This function is called when the task completes, either successfully
            or with an exception.
            当任务完成时调用此函数，无论是成功还是出现异常。

            Args:
                result: The task result.
                       任务结果。

            Returns:
                The task result.
                任务结果。
            """
            self.crawlers.pop(crawler, None)
            self._active.discard(task)
            self.bootstrap_failed |= not getattr(crawler, 'spider', None)
            return result

        task.add_done_callback(_done)

    def crawl(
            self,
            crawler_or_spidercls: Union[Type[Spider], Crawler],
            *args,
            settings: Union[Settings, dict, None] = None,
            **kwargs
    ) -> Crawler:
        """
        Create a crawler and add it to the crawlers dict.
        创建爬虫并将其添加到爬虫字典中。

        This method creates a crawler (if needed) and adds it to the crawlers dict,
        but does not start it.
        此方法创建爬虫（如果需要）并将其添加到爬虫字典中，但不启动它。

        Args:
            crawler_or_spidercls: A Crawler instance or a Spider class.
                                 Crawler实例或Spider类。
            *args: Arguments to pass to the spider's constructor.
                  传递给爬虫构造函数的参数。
            settings: The settings to use for this crawler. Can be a Settings object,
                     a dictionary, or None (in which case default settings are used).
                     此爬虫使用的设置。可以是Settings对象、字典或None（在这种情况下使用默认设置）。
            **kwargs: Keyword arguments to pass to the spider's constructor.
                     传递给爬虫构造函数的关键字参数。

        Returns:
            The crawler instance.
            爬虫实例。

        Raises:
            ValueError: If crawler_or_spidercls is a Spider instance instead of a Spider class.
                       如果crawler_or_spidercls是Spider实例而不是Spider类。
        """
        if isinstance(crawler_or_spidercls, Spider):
            raise ValueError(
                'The crawler_or_spidercls argument cannot be a spider object, '
                'it must be a spider class (or a Crawler object)')
        crawler = self.create_crawler(crawler_or_spidercls, settings or self.settings)
        self.crawlers.setdefault(crawler, (args, kwargs))
        return crawler

    def create_crawler(
            self,
            crawler_or_spidercls: Union[Type[Spider], Crawler, str],
            settings: Union[Settings, dict, None]
    ) -> Crawler:
        """
        Create a crawler instance.
        创建爬虫实例。

        This method creates a crawler instance from a spider class, a crawler instance,
        or a spider name. If a crawler instance is provided, it is returned as is.
        此方法从爬虫类、爬虫实例或爬虫名称创建爬虫实例。如果提供了爬虫实例，则按原样返回。

        Args:
            crawler_or_spidercls: A Crawler instance, a Spider class, or a spider name.
                                 Crawler实例、Spider类或爬虫名称。
            settings: The settings to use for this crawler. Can be a Settings object,
                     a dictionary, or None.
                     此爬虫使用的设置。可以是Settings对象、字典或None。

        Returns:
            Crawler: The crawler instance.
                    爬虫实例。

        Raises:
            ValueError: If crawler_or_spidercls is a Spider instance instead of a Spider class.
                       如果crawler_or_spidercls是Spider实例而不是Spider类。
        """
        # Check if crawler_or_spidercls is a Spider instance (not allowed)
        # 检查crawler_or_spidercls是否为Spider实例（不允许）
        if isinstance(crawler_or_spidercls, Spider):
            raise ValueError(
                'The crawler_or_spidercls argument cannot be a spider object, '
                'it must be a spider class (or a Crawler object)')

        # If crawler_or_spidercls is already a Crawler, return it
        # 如果crawler_or_spidercls已经是Crawler，则返回它
        if isinstance(crawler_or_spidercls, Crawler):
            return crawler_or_spidercls

        # Otherwise, create a new crawler
        # 否则，创建一个新的爬虫
        return self._create_crawler(crawler_or_spidercls, settings)

    def _create_crawler(
            self,
            spidercls: Union[Type[Spider], str],
            settings: Union[Settings, dict, None]
    ) -> Crawler:
        """
        Internal method to create a crawler instance.
        创建爬虫实例的内部方法。

        This method creates a crawler instance from a spider class or a spider name.
        If a spider name is provided, it is loaded using the spider loader.
        此方法从爬虫类或爬虫名称创建爬虫实例。如果提供了爬虫名称，则使用爬虫加载器加载它。

        Args:
            spidercls: A Spider class or a spider name.
                      Spider类或爬虫名称。
            settings: The settings to use for this crawler. Can be a Settings object,
                     a dictionary, or None.
                     此爬虫使用的设置。可以是Settings对象、字典或None。

        Returns:
            Crawler: The crawler instance.
                    爬虫实例。
        """
        # If spidercls is a string (spider name), load the spider class
        # 如果spidercls是字符串（爬虫名称），则加载爬虫类
        if isinstance(spidercls, str):
            spidercls = self.spider_loader.load(spidercls)

        # Create and return a new crawler instance
        # 创建并返回一个新的爬虫实例
        return Crawler(spidercls, settings=settings)

    async def stop(self, signum=None) -> None:
        """
        Stop all crawlers managed by this runner.
        停止此运行器管理的所有爬虫。

        This method calls the stop method of all crawlers managed by this runner.
        It waits for all crawlers to stop before returning.
        此方法调用此运行器管理的所有爬虫的stop方法。它在返回之前等待所有爬虫停止。

        Args:
            signum: The signal number that triggered the stop, if any.
                   触发停止的信号编号（如果有）。
                   This is passed to each crawler's stop method.
                   这将传递给每个爬虫的stop方法。
        """
        # Stop all crawlers concurrently and wait for them to finish
        # 并发停止所有爬虫并等待它们完成
        await asyncio.gather(*[c.stop(signum) for c in self.crawlers])


class CrawlerProcess(CrawlerRunner):
    """
    A class to run multiple crawlers in a process.
    在一个进程中运行多个爬虫的类。

    This class extends CrawlerRunner by adding support for running the crawlers
    in the current process and handling shutdown signals.
    此类通过添加对在当前进程中运行爬虫和处理关闭信号的支持来扩展CrawlerRunner。
    """

    def __init__(
            self,
            settings: Union[Settings, dict, None] = None,
            install_root_handler: bool = True
    ) -> None:
        """
        Initialize a new CrawlerProcess.
        初始化一个新的CrawlerProcess。

        Args:
            settings: The settings to use for this crawler process. Can be a Settings object,
                     a dictionary, or None (in which case default settings are used).
                     此爬虫进程使用的设置。可以是Settings对象、字典或None（在这种情况下使用默认设置）。
            install_root_handler: Whether to install the root handler for logging.
                                 是否安装日志记录的根处理程序。
        """
        super().__init__(settings)
        install_shutdown_handlers(self._signal_shutdown)

    def _signal_shutdown(self, signum: Any, _) -> None:
        """
        Signal handler for the first shutdown signal.
        第一个关闭信号的信号处理程序。

        This method is called when the first shutdown signal (e.g., SIGINT) is received.
        当接收到第一个关闭信号（例如SIGINT）时调用此方法。

        It installs a new signal handler for the second signal and starts the shutdown process.
        它为第二个信号安装新的信号处理程序，并开始关闭过程。

        Args:
            signum: The signal number.
                   信号编号。
            _: The frame object (not used).
               帧对象（未使用）。
        """
        install_shutdown_handlers(self._signal_kill)
        asyncio.create_task(self.stop(signum))

    def _signal_kill(self, signum: Any, _) -> None:
        """
        Signal handler for the second shutdown signal.
        第二个关闭信号的信号处理程序。

        This method is called when the second shutdown signal (e.g., SIGINT) is received.
        当接收到第二个关闭信号（例如SIGINT）时调用此方法。

        It forces an unclean shutdown of the process.
        它强制进程进行不干净的关闭。

        Args:
            signum: The signal number.
                   信号编号。
            _: The frame object (not used).
               帧对象（未使用）。
        """
        install_shutdown_handlers(signal.SIG_IGN)
        signame = signal_names[signum]
        logger.info('Received %(signame)s twice, forcing unclean shutdown' % {'signame': signame})
        asyncio.create_task(self._stop_reactor())

    async def run(self) -> None:
        """
        Run all crawlers until they finish.
        运行所有爬虫直到它们完成。

        This method activates all crawlers and waits for them to finish.
        此方法激活所有爬虫并等待它们完成。

        After all crawlers have finished, it recycles the database connections.
        在所有爬虫完成后，它回收数据库连接。
        """
        try:
            for crawler, (args, kwargs) in self.crawlers.items():
                self.active_crawler(crawler, *args, **kwargs)
            while self._active:
                await asyncio.gather(*self._active)
        finally:
            await self.recycle_db_connect()

    def start(self, use_windows_selector_eventLoop: bool = False) -> None:
        """
        Start the crawler process.
        启动爬虫进程。

        This method sets up the event loop and runs the crawlers.
        此方法设置事件循环并运行爬虫。

        Args:
            use_windows_selector_eventLoop: Whether to use the Windows selector event loop
                                           instead of the ProactorEventLoop on Windows.
                                           是否在Windows上使用Windows选择器事件循环而不是ProactorEventLoop。
        """
        if sys.platform.startswith('win'):
            if use_windows_selector_eventLoop:
                asyncio.set_event_loop_policy(asyncio.windows_events.WindowsSelectorEventLoopPolicy())
            else:
                asyncio.set_event_loop(asyncio.windows_events.ProactorEventLoop())
        else:
            try:
                import uvloop
                asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            except ImportError:
                pass
        asyncio.run(self.run())

    async def _stop_reactor(self) -> None:
        """
        Stop the reactor (event loop).
        停止反应器（事件循环）。

        This method is called when a forced shutdown is requested.
        当请求强制关闭时调用此方法。

        It tries to recycle database connections before stopping the event loop.
        它在停止事件循环之前尝试回收数据库连接。
        """
        try:
            await self.recycle_db_connect()
        finally:
            asyncio.get_event_loop().stop()

    async def recycle_db_connect(self) -> None:
        """
        Recycle database connections.
        回收数据库连接。

        This method closes all database connections if there are no active crawlers.
        如果没有活动的爬虫，此方法将关闭所有数据库连接。
        """
        # recycle pool of db_manager
        if not len(self._active):
            await db_manager.close_all()
