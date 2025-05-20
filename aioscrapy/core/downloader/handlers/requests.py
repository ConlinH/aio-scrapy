"""
Download handler implementation using requests.
使用requests的下载处理程序实现。

This module provides a download handler that uses the requests library to perform HTTP/HTTPS requests.
It runs synchronous requests in a thread pool to make it compatible with the async framework.
此模块提供了一个使用requests库执行HTTP/HTTPS请求的下载处理程序。
它在线程池中运行同步请求，使其与异步框架兼容。
"""

import asyncio

import requests
from requests.exceptions import RequestException as RequestsError

from aioscrapy import Request
from aioscrapy.core.downloader.handlers import BaseDownloadHandler
from aioscrapy.exceptions import DownloadError
from aioscrapy.http import HtmlResponse
from aioscrapy.settings import Settings
from aioscrapy.utils.log import logger


class RequestsDownloadHandler(BaseDownloadHandler):
    """
    Download handler that uses requests to perform HTTP/HTTPS requests.
    使用requests执行HTTP/HTTPS请求的下载处理程序。

    This handler implements the BaseDownloadHandler interface using the requests
    library, which is a popular synchronous HTTP client for Python. Since requests
    is synchronous, this handler runs it in a thread pool to make it compatible
    with the async framework.
    此处理程序使用requests库实现BaseDownloadHandler接口，requests是Python中流行的
    同步HTTP客户端。由于requests是同步的，此处理程序在线程池中运行它，使其与异步框架兼容。
    """

    def __init__(self, settings):
        """
        Initialize the RequestsDownloadHandler.
        初始化RequestsDownloadHandler。

        Args:
            settings: The settings object containing configuration for the handler.
                     包含处理程序配置的设置对象。
        """
        self.settings: Settings = settings

        # SSL verification setting
        # SSL验证设置
        self.verify_ssl: bool = self.settings.get("VERIFY_SSL", True)

    @classmethod
    def from_settings(cls, settings: Settings):
        """
        Create a download handler from settings.
        从设置创建下载处理程序。

        This is a factory method that creates a new RequestsDownloadHandler
        instance with the given settings.
        这是一个工厂方法，使用给定的设置创建一个新的RequestsDownloadHandler实例。

        Args:
            settings: The settings to use for the handler.
                     用于处理程序的设置。

        Returns:
            RequestsDownloadHandler: A new download handler instance.
                                    一个新的下载处理程序实例。
        """
        return cls(settings)

    async def download_request(self, request: Request, _) -> HtmlResponse:
        """
        Download a request using requests.
        使用requests下载请求。

        This method implements the BaseDownloadHandler.download_request interface.
        It wraps the actual download logic in _download_request and handles
        requests-specific exceptions.
        此方法实现了BaseDownloadHandler.download_request接口。
        它将实际的下载逻辑包装在_download_request中，并处理requests特定的异常。

        Args:
            request: The request to download.
                    要下载的请求。
            _: The spider (not used in this implementation).
               爬虫（在此实现中未使用）。

        Returns:
            HtmlResponse: The response from the server.
                         来自服务器的响应。

        Raises:
            DownloadError: If a RequestsError occurs during the download.
                          如果在下载过程中发生RequestsError。
        """
        try:
            return await self._download_request(request)
        except RequestsError as e:
            # Wrap requests-specific exceptions in a generic DownloadError
            # 将requests特定的异常包装在通用的DownloadError中
            raise DownloadError(real_error=e) from e

    async def _download_request(self, request: Request) -> HtmlResponse:
        """
        Internal method to perform the actual download using requests.
        使用requests执行实际下载的内部方法。

        This method configures and uses the requests library to perform the request,
        handling SSL settings, proxies, cookies, and other request parameters.
        Since requests is synchronous, it runs in a thread pool using asyncio.to_thread.
        此方法配置并使用requests库执行请求，处理SSL设置、代理、Cookie和其他请求参数。
        由于requests是同步的，它使用asyncio.to_thread在线程池中运行。

        Args:
            request: The request to download.
                    要下载的请求。

        Returns:
            HtmlResponse: The response from the server.
                         来自服务器的响应。
        """
        # Configure request parameters
        # 配置请求参数
        kwargs = {
            'timeout': self.settings.get('DOWNLOAD_TIMEOUT'),
            'cookies': dict(request.cookies),
            'verify': request.meta.get('verify_ssl', self.verify_ssl),
            'allow_redirects': self.settings.getbool('REDIRECT_ENABLED', True) if request.meta.get(
                'dont_redirect') is None else request.meta.get('dont_redirect')
        }

        # Handle request body data
        # 处理请求体数据
        post_data = request.body or None
        if isinstance(post_data, dict):
            kwargs['json'] = post_data  # Send as JSON
                                       # 作为JSON发送
        else:
            kwargs['data'] = post_data  # Send as form data or raw bytes
                                       # 作为表单数据或原始字节发送

        # Set request headers
        # 设置请求头
        headers = request.headers or self.settings.get('DEFAULT_REQUEST_HEADERS')
        kwargs['headers'] = headers

        # Configure proxy if specified
        # 如果指定，配置代理
        proxy = request.meta.get("proxy")
        if proxy:
            kwargs["proxies"] = {'http': proxy, 'https': proxy}
            logger.debug(f"use proxy {proxy}: {request.url}")

        # Execute the request in a thread pool since requests is synchronous
        # 由于requests是同步的，在线程池中执行请求
        response = await asyncio.to_thread(requests.request, request.method, request.url, **kwargs)

        # Convert requests response to HtmlResponse
        # 将requests响应转换为HtmlResponse
        return HtmlResponse(
            response.url,
            status=response.status_code,
            headers=response.headers,
            body=response.content,
            cookies={k: v or '' for k, v in response.cookies.items()},
            encoding=response.encoding
        )

    async def close(self):
        """
        Close the download handler and release resources.
        关闭下载处理程序并释放资源。

        This method is called when the spider is closing. In this implementation,
        there are no persistent resources to clean up since the requests library
        doesn't maintain persistent connections between calls in this usage pattern.
        当爬虫关闭时调用此方法。在此实现中，没有需要清理的持久资源，
        因为在这种使用模式下，requests库不会在调用之间维护持久连接。
        """
        pass
