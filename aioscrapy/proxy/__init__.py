"""
Proxy module for aioscrapy.
aioscrapy的代理模块。

This module provides the abstract base class for proxy handlers in aioscrapy.
It defines the interface that all proxy handlers must implement and provides
common functionality for proxy management.
此模块提供了aioscrapy中代理处理程序的抽象基类。
它定义了所有代理处理程序必须实现的接口，并提供了代理管理的通用功能。
"""

from abc import ABCMeta, abstractmethod

from aioscrapy.utils.log import logger
from aioscrapy.utils.python import global_object_name


class AbsProxy(metaclass=ABCMeta):
    """
    Abstract base class for proxy handlers.
    代理处理程序的抽象基类。

    This class defines the interface that all proxy handlers must implement
    and provides common functionality for proxy management, including adding
    proxies to requests, removing invalid proxies, and checking proxy validity.
    此类定义了所有代理处理程序必须实现的接口，并提供了代理管理的通用功能，
    包括向请求添加代理、移除无效代理和检查代理有效性。

    Attributes:
        use_proxy (bool): Whether to use proxies.
                         是否使用代理。
        max_count (int): Maximum number of proxies to maintain.
                        要维护的最大代理数量。
        min_count (int): Minimum number of proxies to maintain.
                        要维护的最小代理数量。
        allow_status_code (list): HTTP status codes that are allowed even with a proxy.
                                 即使使用代理也允许的HTTP状态码。
        cache (list): List of available proxies.
                     可用代理列表。
    """

    def __init__(self, settings):
        """
        Initialize the proxy handler.
        初始化代理处理程序。

        Args:
            settings: The aioscrapy settings object.
                     aioscrapy设置对象。
        """
        self.use_proxy = settings.getbool('USE_PROXY', False)
        self.max_count = settings.getint('PROXY_MAX_COUNT', 16)
        self.min_count = settings.getint('PROXY_MIN_COUNT', 1)
        self.allow_status_code = settings.get('PROXY_ALLOW_STATUS_CODE', [404])
        self.cache = []

    async def add_proxy(self, request):
        """
        Add a proxy to the request if proxy usage is enabled.
        如果启用了代理使用，则向请求添加代理。

        This method checks if proxy usage is enabled both globally and for the
        specific request. If so, it gets a proxy from the pool and adds it to
        the request's meta. Otherwise, it removes any existing proxy from the request.
        此方法检查代理使用是否在全局和特定请求中都启用。如果是，它从池中获取代理
        并将其添加到请求的meta中。否则，它会从请求中移除任何现有的代理。

        Args:
            request: The request to add a proxy to.
                    要添加代理的请求。

        Returns:
            The modified request.
            修改后的请求。
        """
        if self.use_proxy and request.use_proxy:
            # Get a proxy and add it to the request's meta
            # 获取代理并将其添加到请求的meta中
            request.meta['proxy'] = await self.get()
        else:
            # Remove any existing proxy from the request
            # 从请求中移除任何现有的代理
            request.meta.pop('proxy', None)
        return request

    def remove(self, proxy, reason=None):
        """
        Remove a proxy from the cache.
        从缓存中移除代理。

        This method removes a proxy from the cache when it's determined to be invalid
        or no longer usable. It logs the removal with the provided reason.
        当确定代理无效或不再可用时，此方法从缓存中移除代理。它记录移除的原因。

        Args:
            proxy: The proxy to remove.
                  要移除的代理。
            reason: The reason for removing the proxy. Can be a callable, an exception,
                   or any other object that can be converted to a string.
                   移除代理的原因。可以是可调用对象、异常或任何其他可以转换为字符串的对象。
        """
        # If reason is callable, call it to get the actual reason
        # 如果reason是可调用的，调用它以获取实际原因
        if callable(reason):
            reason = reason()

        # If reason is an exception, use its class name
        # 如果reason是异常，使用其类名
        if isinstance(reason, Exception):
            reason = global_object_name(reason.__class__)

        # Remove the proxy if it's in the cache
        # 如果代理在缓存中，则移除它
        if proxy in self.cache:
            logger.info(f"remove proxy: {proxy}, reason: {reason}")
            self.cache.remove(proxy)

    def check(self, request, response=None, exception=None):
        """
        Check if a proxy is still valid based on response or exception.
        根据响应或异常检查代理是否仍然有效。

        This method checks if a proxy should be removed based on the response status code
        or an exception that occurred during the request. If the response status code is
        not in the allowed list or if an exception occurred, the proxy is removed.
        此方法根据响应状态码或请求期间发生的异常检查是否应该移除代理。
        如果响应状态码不在允许列表中或发生异常，则移除代理。

        Args:
            request: The request that was made.
                    发出的请求。
            response: The response received, if any.
                     收到的响应（如果有）。
            exception: The exception that occurred, if any.
                      发生的异常（如果有）。
        """
        # If proxy usage is disabled, do nothing
        # 如果禁用了代理使用，则不执行任何操作
        if not self.use_proxy:
            return

        # Check if the response status code is not allowed
        # 检查响应状态码是否不被允许
        if response and response.status >= 400 and response.status not in self.allow_status_code:
            self.remove(request.meta.get('proxy'), f"Don't allow response status code:{response.status}")

        # Check if an exception occurred
        # 检查是否发生异常
        if exception and isinstance(exception, BaseException):
            self.remove(request.meta.get('proxy'), exception)

    @classmethod
    @abstractmethod
    async def from_crawler(cls, crawler) -> "AbsProxy":
        """
        Create a proxy handler instance from a crawler.
        从爬虫创建代理处理程序实例。

        This class method is used to create a proxy handler instance from a crawler.
        It is called by the crawler when initializing the proxy handler.
        此类方法用于从爬虫创建代理处理程序实例。
        它在初始化代理处理程序时由爬虫调用。

        Args:
            crawler: The crawler instance.
                    爬虫实例。

        Returns:
            AbsProxy: A proxy handler instance.
                     代理处理程序实例。
        """
        pass

    @abstractmethod
    async def get(self) -> str:
        """
        Get a proxy from the pool.
        从池中获取代理。

        This method is called when a proxy is needed for a request.
        It should return a proxy in the format 'scheme://host:port'.
        当请求需要代理时调用此方法。
        它应该以'scheme://host:port'格式返回代理。

        Returns:
            str: A proxy string in the format 'scheme://host:port'.
                 格式为'scheme://host:port'的代理字符串。
        """
        pass
