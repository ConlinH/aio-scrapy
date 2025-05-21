"""
Download handler implementation using httpx.
使用httpx的下载处理程序实现。

This module provides a download handler that uses httpx to perform HTTP/HTTPS requests.
It supports HTTP/2, SSL customization, proxies, and cookies.
此模块提供了一个使用httpx执行HTTP/HTTPS请求的下载处理程序。
它支持HTTP/2、SSL自定义、代理和Cookie。
"""

import ssl

import httpx
from httpx import HTTPError as HttpxError

from aioscrapy import Request
from aioscrapy.core.downloader.handlers import BaseDownloadHandler
from aioscrapy.exceptions import DownloadError
from aioscrapy.http import HtmlResponse
from aioscrapy.settings import Settings
from aioscrapy.utils.log import logger


class HttpxDownloadHandler(BaseDownloadHandler):
    """
    Download handler that uses httpx to perform HTTP/HTTPS requests.
    使用httpx执行HTTP/HTTPS请求的下载处理程序。

    This handler implements the BaseDownloadHandler interface using the httpx
    library, which provides modern HTTP client features including HTTP/2 support,
    connection pooling, and async capabilities.
    此处理程序使用httpx库实现BaseDownloadHandler接口，该库提供现代HTTP客户端功能，
    包括HTTP/2支持、连接池和异步功能。
    """

    def __init__(self, settings):
        """
        Initialize the HttpxDownloadHandler.
        初始化HttpxDownloadHandler。

        Args:
            settings: The settings object containing configuration for the handler.
                     包含处理程序配置的设置对象。
        """
        self.settings: Settings = settings

        # Arguments to pass to httpx AsyncClient constructor
        # 传递给httpx AsyncClient构造函数的参数
        self.httpx_args: dict = self.settings.get('HTTPX_ARGS', {})

        # SSL verification setting
        # SSL验证设置
        self.verify_ssl: bool = self.settings.get("VERIFY_SSL", True)

        # SSL protocol version to use (e.g., ssl.PROTOCOL_TLSv1_2)
        # 要使用的SSL协议版本（例如，ssl.PROTOCOL_TLSv1_2）
        self.ssl_protocol = self.settings.get("SSL_PROTOCOL")

        # Fix for non-standard HTTP headers in responses
        # 修复响应中的非标准HTTP头
        if self.settings.getbool("FIX_HTTPX_HEADER", True):
            import h11
            import re
            h11._readers.header_field_re = re.compile(b"(?P<field_name>.*?):[ \t](?P<field_value>.*?)")

    @classmethod
    def from_settings(cls, settings: Settings):
        """
        Create a download handler from settings.
        从设置创建下载处理程序。

        This is a factory method that creates a new HttpxDownloadHandler
        instance with the given settings.
        这是一个工厂方法，使用给定的设置创建一个新的HttpxDownloadHandler实例。

        Args:
            settings: The settings to use for the handler.
                     用于处理程序的设置。

        Returns:
            HttpxDownloadHandler: A new download handler instance.
                                 一个新的下载处理程序实例。
        """
        return cls(settings)

    async def download_request(self, request: Request, _) -> HtmlResponse:
        """
        Download a request using httpx.
        使用httpx下载请求。

        This method implements the BaseDownloadHandler.download_request interface.
        It wraps the actual download logic in _download_request and handles
        httpx-specific exceptions.
        此方法实现了BaseDownloadHandler.download_request接口。
        它将实际的下载逻辑包装在_download_request中，并处理httpx特定的异常。

        Args:
            request: The request to download.
                    要下载的请求。
            _: The spider (not used in this implementation).
               爬虫（在此实现中未使用）。

        Returns:
            HtmlResponse: The response from the server.
                         来自服务器的响应。

        Raises:
            DownloadError: If an HttpxError occurs during the download.
                          如果在下载过程中发生HttpxError。
        """
        try:
            return await self._download_request(request)
        except HttpxError as e:
            # Wrap httpx-specific exceptions in a generic DownloadError
            # 将httpx特定的异常包装在通用的DownloadError中
            raise DownloadError(real_error=e) from e

    async def _download_request(self, request: Request) -> HtmlResponse:
        """
        Internal method to perform the actual download using httpx.
        使用httpx执行实际下载的内部方法。

        This method configures and uses an httpx.AsyncClient to perform the request,
        handling SSL settings, proxies, cookies, and other request parameters.
        此方法配置并使用httpx.AsyncClient执行请求，处理SSL设置、代理、Cookie和其他请求参数。

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
            'data': request.body or None
        }

        # Set request headers
        # 设置请求头
        headers = request.headers or self.settings.get('DEFAULT_REQUEST_HEADERS')
        kwargs['headers'] = headers

        # Configure httpx client session
        # 配置httpx客户端会话
        session_args = self.httpx_args.copy()
        session_args.setdefault('http2', True)  # Enable HTTP/2 by default
                                               # 默认启用HTTP/2
        session_args.update({
            'verify': request.meta.get('verify_ssl', self.verify_ssl),
            'follow_redirects': self.settings.getbool('REDIRECT_ENABLED', True) if request.meta.get(
                'dont_redirect') is None else request.meta.get('dont_redirect'),
            'max_redirects': self.settings.getint('REDIRECT_MAX_TIMES', 20),
        })

        # Configure SSL settings if specified
        # 如果指定，配置SSL设置
        ssl_ciphers = request.meta.get('TLS_CIPHERS')
        ssl_protocol = request.meta.get('ssl_protocol', self.ssl_protocol)
        if ssl_ciphers or ssl_protocol:
            if ssl_protocol:
                # Create SSL context with specific protocol
                # 使用特定协议创建SSL上下文
                context = ssl.SSLContext(protocol=ssl_protocol)
            else:
                # Use default SSL context
                # 使用默认SSL上下文
                context = ssl.create_default_context()

            # Set SSL ciphers if specified
            # 如果指定，设置SSL密码
            ssl_ciphers and context.set_ciphers(ssl_ciphers)
            session_args['verify'] = context

        # Configure proxy if specified
        # 如果指定，配置代理
        proxy = request.meta.get("proxy")
        if proxy:
            session_args["proxies"] = proxy
            logger.debug(f"使用代理{proxy}抓取: {request.url}")

        # Perform the request
        # 执行请求
        async with httpx.AsyncClient(**session_args) as session:
            response = await session.request(request.method, request.url, **kwargs)
            content = response.read()

        # Convert httpx response to HtmlResponse
        # 将httpx响应转换为HtmlResponse
        return HtmlResponse(
            str(response.url),
            status=response.status_code,
            headers=response.headers,
            body=content,
            cookies={j.name: j.value or '' for j in response.cookies.jar},
            encoding=response.encoding
        )

    async def close(self):
        """
        Close the download handler and release resources.
        关闭下载处理程序并释放资源。

        This method is called when the spider is closing. In this implementation,
        there are no persistent resources to clean up since httpx.AsyncClient
        is created and closed for each request.
        当爬虫关闭时调用此方法。在此实现中，没有需要清理的持久资源，
        因为httpx.AsyncClient是为每个请求创建和关闭的。
        """
        pass
