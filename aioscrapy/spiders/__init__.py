
"""
Spider module for aioscrapy.
aioscrapy的爬虫模块。

This module contains the base Spider class that all spiders must inherit from.
It provides the core functionality for creating and managing spiders.
此模块包含所有爬虫必须继承的基础Spider类。
它提供了创建和管理爬虫的核心功能。
"""

import time
from typing import Optional, Union

from aioscrapy import signals
from aioscrapy.exceptions import DontCloseSpider
from aioscrapy.http.request import Request
from aioscrapy.http.response import Response
from aioscrapy.statscollectors import StatsCollector
from aioscrapy.utils.tools import call_helper
from aioscrapy.utils.url import url_is_from_spider


class Spider(object):
    """
    Base class for aioscrapy spiders. All spiders must inherit from this class.
    aioscrapy爬虫的基类。所有爬虫必须继承自此类。

    This class provides the core functionality for creating and managing spiders,
    including request generation, response parsing, and signal handling.
    此类提供了创建和管理爬虫的核心功能，包括请求生成、响应解析和信号处理。

    Attributes:
        name: The name of the spider. Must be unique. 爬虫的名称，必须唯一。
        proxy: Optional proxy handler. 可选的代理处理器。
        dupefilter: Optional duplicate filter. 可选的重复过滤器。
        custom_settings: Dictionary of settings to override project settings. 用于覆盖项目设置的设置字典。
        stats: Statistics collector. 统计收集器。
        pause: Whether the spider is paused. 爬虫是否暂停。
        start_urls: List of URLs to start crawling from. 开始爬取的URL列表。
    """

    name: Optional[str] = None
    proxy: Optional["aioscrapy.proxy.AbsProxy"] = None
    dupefilter: Optional["aioscrapy.dupefilters.DupeFilterBase"] = None
    custom_settings: Optional[dict] = None
    stats: Optional[StatsCollector] = None

    pause: bool = False
    _pause_time: Optional[Union[int, float]] = None

    def __init__(self, name=None, **kwargs):
        """
        Initialize the spider.
        初始化爬虫。

        Args:
            name: Spider name. 爬虫名称。
            **kwargs: Additional arguments. 额外参数。
        """
        if name is not None:
            self.name = name
        elif not getattr(self, 'name', None):
            raise ValueError(f"{type(self).__name__} must have a name")
        self.__dict__.update(kwargs)
        if not hasattr(self, 'start_urls'):
            self.start_urls = []

    @property
    def pause_time(self) -> int:
        """
        Get the time until which the spider is paused.
        获取爬虫暂停的时间点。

        If not set, defaults to current time + 600 seconds.
        如果未设置，默认为当前时间 + 600秒。

        Returns:
            int: Unix timestamp when the pause ends.
                暂停结束的Unix时间戳。
        """
        if self._pause_time is None:
            self._pause_time = 600 + int(time.time())
        return self._pause_time

    @pause_time.setter
    def pause_time(self, value: Union[int, float]):
        """
        Set the time until which the spider is paused.
        设置爬虫暂停的时间点。

        Args:
            value: Unix timestamp or duration in seconds.
                  Unix时间戳或持续时间（秒）。
                  - If None, pause indefinitely.
                    如果为None，则无限期暂停。
                  - If less than current time, treated as duration.
                    如果小于当前时间，则视为持续时间。
                  - Otherwise, treated as absolute timestamp.
                    否则，视为绝对时间戳。
        """
        self.pause = True
        if value is None:
            self._pause_time = float('inf')
        elif value < time.time():
            self._pause_time = value + int(time.time())
        else:
            self._pause_time = value

    @classmethod
    async def from_crawler(cls, crawler, *args, **kwargs):
        """
        Create a spider instance from a crawler.
        从爬虫引擎创建爬虫实例。

        Args:
            crawler: The crawler instance. 爬虫引擎实例。
            *args: Additional arguments. 额外参数。
            **kwargs: Additional keyword arguments. 额外关键字参数。

        Returns:
            Spider instance. 爬虫实例。
        """
        spider = cls(*args, **kwargs)
        spider._set_crawler(crawler)
        return spider

    def _set_crawler(self, crawler):
        """
        Set the crawler for this spider.
        为此爬虫设置爬虫引擎。

        This method is called by the from_crawler class method to set up the crawler
        for this spider. It connects signal handlers and sets up settings.
        此方法由from_crawler类方法调用，为此爬虫设置爬虫引擎。
        它连接信号处理程序并设置配置。

        Args:
            crawler: The crawler instance to use.
                    要使用的爬虫引擎实例。
        """
        # Store the crawler instance
        # 存储爬虫引擎实例
        self.crawler = crawler

        # Get settings from the crawler
        # 从爬虫引擎获取设置
        self.settings = crawler.settings

        # Determine if the spider should close when idle
        # 确定爬虫在空闲时是否应该关闭
        self.close_on_idle = self.settings.get("CLOSE_SPIDER_ON_IDLE", True)

        # Connect signal handlers
        # 连接信号处理程序
        crawler.signals.connect(self.close, signals.spider_closed)
        crawler.signals.connect(self.spider_idle, signal=signals.spider_idle)

    async def start_requests(self):
        """
        Generate initial requests for the spider.
        生成爬虫的初始请求。

        This method must return an iterable of Request objects.
        此方法必须返回一个包含Request对象的可迭代对象。

        By default, it generates Request objects from the spider's start_urls.
        默认情况下，它从爬虫的start_urls生成Request对象。

        Returns:
            An iterable of Request objects. 包含Request对象的可迭代对象。
        """
        if not self.start_urls and hasattr(self, 'start_url'):
            raise AttributeError(
                "Crawling could not start: 'start_urls' not found "
                "or empty (but found 'start_url' attribute instead, "
                "did you miss an 's'?)")

        for url in self.start_urls:
            yield Request(url)

    async def request_from_dict(self, d: dict):
        """
        Create a Request object from a dictionary.
        从字典创建Request对象。

        This method can be overridden in subclasses to customize the request creation process.
        It is typically used for deserializing requests from storage or message queues.
        可以在子类中重写此方法以自定义请求创建过程。
        它通常用于从存储或消息队列中反序列化请求。

        Args:
            d: Dictionary containing request data. 包含请求数据的字典。
               Expected keys include:
               预期的键包括：
               - url: The URL to request (required)
                     要请求的URL（必需）
               - callback: Name of the callback method (optional)
                          回调方法的名称（可选）
               - method: HTTP method (optional, default: 'GET')
                        HTTP方法（可选，默认：'GET'）
               - headers: HTTP headers (optional)
                         HTTP头（可选）
               - body: Request body (optional)
                      请求体（可选）
               - cookies: Cookies (optional)
                         Cookie（可选）
               - meta: Request metadata (optional)
                      请求元数据（可选）

        Returns:
            Request: A Request object, or None if the request cannot be created.
                    Request对象，如果无法创建请求则为None。
        """
        # This is a placeholder implementation that should be overridden in subclasses
        # 这是一个应该在子类中重写的占位符实现
        return None

    async def _parse(self, response: Response, **kwargs):
        """
        Internal parse method that calls the user-defined parse method.
        调用用户定义的parse方法的内部解析方法。

        This method is used internally by the crawler to call the spider's parse method.
        It uses call_helper to handle the parse method call, which supports both
        async and non-async parse methods.
        此方法由爬虫引擎内部使用，用于调用爬虫的parse方法。
        它使用call_helper来处理parse方法调用，支持异步和非异步parse方法。

        Args:
            response: The response to parse.
                     要解析的响应。
            **kwargs: Additional keyword arguments to pass to the parse method.
                     传递给parse方法的额外关键字参数。

        Returns:
            The result of the parse method.
            parse方法的结果。
        """
        return await call_helper(self.parse, response)

    async def parse(self, response: Response):
        """
        Default callback used to process downloaded responses.
        用于处理下载响应的默认回调方法。

        This method must be implemented in subclasses.
        必须在子类中实现此方法。

        Args:
            response: The response to process. 要处理的响应。

        Returns:
            An iterable of Request and/or item objects. 包含Request和/或数据项对象的可迭代对象。
        """
        raise NotImplementedError(f'{self.__class__.__name__}.parse callback is not defined')

    @classmethod
    def update_settings(cls, settings):
        """
        Update settings with spider custom settings.
        使用爬虫自定义设置更新设置。

        Args:
            settings: The settings to update. 要更新的设置。
        """
        settings.setdict(cls.custom_settings or {}, priority='spider')

    @classmethod
    def handles_request(cls, request):
        """
        Check if this spider can handle the given request.
        检查此爬虫是否可以处理给定的请求。

        Args:
            request: The request to check. 要检查的请求。

        Returns:
            True if this spider can handle the request, False otherwise.
            如果此爬虫可以处理该请求，则返回True，否则返回False。
        """
        return url_is_from_spider(request.url, cls)

    @staticmethod
    def close(spider, reason):
        """
        Signal handler for the spider_closed signal.
        爬虫关闭信号的处理函数。

        Args:
            spider: The spider being closed. 正在关闭的爬虫。
            reason: The reason for closing the spider. 关闭爬虫的原因。
        """
        closed = getattr(spider, 'closed', None)
        if callable(closed):
            return closed(reason)

    def __str__(self):
        """
        Return a string representation of the spider.
        返回爬虫的字符串表示。

        Returns:
            str: A string representation of the spider, including its class name,
                 name, and memory address.
                 爬虫的字符串表示，包括其类名、名称和内存地址。
        """
        return f"<{type(self).__name__} {self.name!r} at 0x{id(self):0x}>"

    # Make __repr__ use the same implementation as __str__
    # 使__repr__使用与__str__相同的实现
    __repr__ = __str__

    @classmethod
    def start(cls, setting_path=None, use_windows_selector_eventLoop: bool = False):
        """
        Start crawling using this spider.
        使用此爬虫开始爬取。

        This is a convenience method that creates a CrawlerProcess, adds the spider,
        and starts the crawling process.
        这是一个便捷方法，它创建一个CrawlerProcess，添加爬虫，并启动爬取过程。

        Args:
            setting_path: Path to settings module. 设置模块的路径。
            use_windows_selector_eventLoop: Whether to use Windows selector event loop. 是否使用Windows选择器事件循环。
        """
        from aioscrapy.crawler import CrawlerProcess
        from aioscrapy.utils.project import get_project_settings

        settings = get_project_settings()
        if setting_path is not None:
            settings.setmodule(setting_path)
        cp = CrawlerProcess(settings)
        cp.crawl(cls)
        cp.start(use_windows_selector_eventLoop)

    def spider_idle(self):
        """
        Signal handler for the spider_idle signal.
        爬虫空闲信号的处理函数。

        This method is called when the spider has no more requests to process.
        当爬虫没有更多请求要处理时，调用此方法。

        If CLOSE_SPIDER_ON_IDLE is False, it raises DontCloseSpider to prevent the spider from closing.
        如果CLOSE_SPIDER_ON_IDLE为False，它会引发DontCloseSpider以防止爬虫关闭。
        """
        if not self.close_on_idle:
            raise DontCloseSpider
