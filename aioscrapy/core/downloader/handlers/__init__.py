"""
Download handlers for different URL schemes.
不同URL方案的下载处理程序。

This module provides the base classes and manager for download handlers,
which are responsible for handling different URL schemes (http, https, ftp, etc.).
此模块提供了下载处理程序的基类和管理器，负责处理不同的URL方案（http、https、ftp等）。
"""

from abc import abstractmethod
from typing import Optional

from aioscrapy import signals, Request, Spider
from aioscrapy.exceptions import NotConfigured, NotSupported
from aioscrapy.http import HtmlResponse
from aioscrapy.utils.httpobj import urlparse_cached
from aioscrapy.utils.log import logger
from aioscrapy.utils.misc import load_instance
from aioscrapy.utils.python import without_none_values


class BaseDownloadHandler:
    """
    Base class for download handlers.
    下载处理程序的基类。

    Download handlers are responsible for handling requests with specific URL schemes
    (http, https, ftp, etc.). Each scheme has its own handler implementation.
    下载处理程序负责处理具有特定URL方案的请求（http、https、ftp等）。每个方案都有自己的处理程序实现。
    """

    @abstractmethod
    async def download_request(self, request: Request, spider: Spider):
        """
        Download the given request and return a response.
        下载给定的请求并返回响应。

        Args:
            request: The request to download.
                    要下载的请求。
            spider: The spider that generated the request.
                   生成请求的爬虫。

        Returns:
            A response object.
            响应对象。
        """
        raise NotImplementedError()

    @abstractmethod
    async def close(self):
        """
        Close the handler and release its resources.
        关闭处理程序并释放其资源。

        This method is called when the spider is closed.
        当爬虫关闭时调用此方法。
        """
        pass


class DownloadHandlerManager:
    """
    Manager for download handlers.
    下载处理程序的管理器。

    This class manages download handlers for different URL schemes.
    It lazily loads handlers when they are first needed and keeps track
    of which schemes are supported.
    此类管理不同URL方案的下载处理程序。它在首次需要时懒加载处理程序，并跟踪支持哪些方案。
    """

    def __init__(self, crawler):
        """
        Initialize the download handler manager.
        初始化下载处理程序管理器。

        Args:
            crawler: The crawler instance that this manager belongs to.
                    此管理器所属的爬虫实例。
        """
        self._crawler = crawler

        # Load scheme handlers configuration from settings
        # 从设置加载方案处理程序配置
        # First try DOWNLOAD_HANDLERS_MAP[DOWNLOAD_HANDLERS_TYPE], then fall back to DOWNLOAD_HANDLERS
        # 首先尝试DOWNLOAD_HANDLERS_MAP[DOWNLOAD_HANDLERS_TYPE]，然后回退到DOWNLOAD_HANDLERS
        self._schemes: dict = without_none_values(
            crawler.settings.get('DOWNLOAD_HANDLERS_MAP', {}).get(crawler.settings.get('DOWNLOAD_HANDLERS_TYPE')) or
            crawler.settings.getwithbase('DOWNLOAD_HANDLERS')
        )

        # Dictionary of scheme -> handler instance
        # 方案 -> 处理程序实例的字典
        self._handlers: dict = {}  # stores instanced handlers for schemes

        # Dictionary of scheme -> error message for failed handlers
        # 方案 -> 失败处理程序的错误消息的字典
        self._notconfigured: dict = {}  # remembers failed handlers

        # Connect to engine_stopped signal to close handlers
        # 连接到engine_stopped信号以关闭处理程序
        crawler.signals.connect(self._close, signals.engine_stopped)

    @classmethod
    def from_crawler(cls, crawler) -> "DownloadHandlerManager":
        """
        Create a download handler manager from a crawler.
        从爬虫创建下载处理程序管理器。

        This is a factory method that creates a new download handler manager
        instance with the given crawler.
        这是一个工厂方法，使用给定的爬虫创建一个新的下载处理程序管理器实例。

        Args:
            crawler: The crawler instance that will use this manager.
                    将使用此管理器的爬虫实例。

        Returns:
            DownloadHandlerManager: A new download handler manager instance.
                                   一个新的下载处理程序管理器实例。
        """
        return cls(crawler)

    async def _get_handler(self, scheme: str) -> Optional[BaseDownloadHandler]:
        """
        Lazy-load the download handler for a scheme.
        懒加载方案的下载处理程序。

        This method only loads the handler on the first request for that scheme.
        此方法仅在首次请求该方案时加载处理程序。

        Args:
            scheme: The URL scheme to get a handler for (e.g., 'http', 'https', 'ftp').
                   要获取处理程序的URL方案（例如，'http'、'https'、'ftp'）。

        Returns:
            BaseDownloadHandler: The handler for the scheme, or None if no handler
                                is available or could be loaded.
                                方案的处理程序，如果没有可用或无法加载的处理程序，则为None。
        """
        # Return cached handler if available
        # 如果可用，返回缓存的处理程序
        if scheme in self._handlers:
            return self._handlers[scheme]

        # Return None if we already know this scheme is not configured
        # 如果我们已经知道此方案未配置，则返回None
        if scheme in self._notconfigured:
            return None

        # Return None if no handler is defined for this scheme
        # 如果没有为此方案定义处理程序，则返回None
        if scheme not in self._schemes:
            self._notconfigured[scheme] = 'no handler available for that scheme'
            return None

        # Load the handler for this scheme
        # 加载此方案的处理程序
        return await self._load_handler(scheme)

    async def _load_handler(self, scheme: str) -> Optional[BaseDownloadHandler]:
        """
        Load a download handler for a scheme.
        加载方案的下载处理程序。

        This method attempts to load the handler class specified in the settings
        for the given scheme.
        此方法尝试加载设置中为给定方案指定的处理程序类。

        Args:
            scheme: The URL scheme to load a handler for.
                   要加载处理程序的URL方案。

        Returns:
            BaseDownloadHandler: The loaded handler, or None if the handler
                                could not be loaded.
                                加载的处理程序，如果无法加载处理程序，则为None。
        """
        # Get the handler class path from settings
        # 从设置获取处理程序类路径
        path: str = self._schemes[scheme]

        try:
            # Load the handler class
            # 加载处理程序类
            dh: BaseDownloadHandler = await load_instance(
                path,
                settings=self._crawler.settings,
            )
        except NotConfigured as ex:
            # Handler explicitly raised NotConfigured
            # 处理程序明确引发NotConfigured
            self._notconfigured[scheme] = str(ex)
            return None
        except Exception as ex:
            # Any other exception during loading
            # 加载期间的任何其他异常
            logger.exception(f'Loading "{path}" for scheme "{scheme}"')
            self._notconfigured[scheme] = str(ex)
            return None
        else:
            # Successfully loaded the handler
            # 成功加载处理程序
            self._handlers[scheme] = dh
            return dh

    async def download_request(self, request: Request, spider: Spider) -> HtmlResponse:
        """
        Download a request using the appropriate handler for its URL scheme.
        使用适合其URL方案的处理程序下载请求。

        This method determines the URL scheme of the request, gets the appropriate
        handler, and delegates the download to that handler.
        此方法确定请求的URL方案，获取适当的处理程序，并将下载委托给该处理程序。

        Args:
            request: The request to download.
                    要下载的请求。
            spider: The spider that generated the request.
                   生成请求的爬虫。

        Returns:
            HtmlResponse: The response from the handler.
                         来自处理程序的响应。

        Raises:
            NotSupported: If no handler is available for the request's URL scheme.
                         如果请求的URL方案没有可用的处理程序。
        """
        # Extract the scheme from the URL (http, https, ftp, etc.)
        # 从URL提取方案（http、https、ftp等）
        scheme = urlparse_cached(request).scheme

        # Get the handler for this scheme
        # 获取此方案的处理程序
        handler: BaseDownloadHandler = await self._get_handler(scheme)

        # Raise an exception if no handler is available
        # 如果没有可用的处理程序，则引发异常
        if not handler:
            raise NotSupported("Unsupported URL scheme '%s': %s" %
                               (scheme, self._notconfigured[scheme]))

        # Delegate the download to the handler
        # 将下载委托给处理程序
        return await handler.download_request(request, spider)

    async def _close(self, *_a, **_kw) -> None:
        """
        Close all download handlers.
        关闭所有下载处理程序。

        This method is called when the engine is stopped. It closes all
        download handlers that have been loaded.
        当引擎停止时调用此方法。它关闭所有已加载的下载处理程序。

        Args:
            *_a: Variable positional arguments from the signal (not used).
                 来自信号的可变位置参数（未使用）。
            **_kw: Variable keyword arguments from the signal (not used).
                  来自信号的可变关键字参数（未使用）。
        """
        # Close each handler
        # 关闭每个处理程序
        for dh in self._handlers.values():
            await dh.close()
