"""

Download handler implementation using aiohttp.
使用aiohttp的下载处理程序实现。

This module provides a download handler that uses aiohttp to perform HTTP/HTTPS requests.
It supports features like browser impersonation, proxies, and cookies.
此模块提供了一个使用aiohttp执行HTTP/HTTPS请求的下载处理程序。
它支持浏览器模拟、代理和Cookie等功能。
"""
import asyncio
import re
import ssl
from typing import Optional

import aiohttp
from aiohttp.client_exceptions import ClientError

from aioscrapy import Request
from aioscrapy.core.downloader.handlers import BaseDownloadHandler
from aioscrapy.exceptions import DownloadError
from aioscrapy.http import HtmlResponse
from aioscrapy.settings import Settings
from aioscrapy.utils.log import logger


class AioHttpDownloadHandler(BaseDownloadHandler):
    """
    Download handler that uses aiohttp to download HTTP/HTTPS requests.
    使用aiohttp下载HTTP/HTTPS请求的下载处理程序。

    This handler implements the BaseDownloadHandler interface using the aiohttp
    library to perform HTTP/HTTPS requests.
    此处理程序使用aiohttp库执行HTTP/HTTPS请求，实现了BaseDownloadHandler接口。
    """

    session: Optional[aiohttp.ClientSession] = None  # Shared session when USE_SESSION is True
                                                    # 当USE_SESSION为True时的共享会话

    def __init__(self, settings: Settings):
        """
        Initialize the AioHttpDownloadHandler.
        初始化AioHttpDownloadHandler。

        Args:
            settings: The settings object containing configuration for the handler.
                     包含处理程序配置的设置对象。
        """
        self.settings = settings

        # Arguments to pass to aiohttp.ClientSession constructor
        # 传递给aiohttp.ClientSession构造函数的参数
        self.aiohttp_client_session_args: dict = settings.getdict('AIOHTTP_CLIENT_SESSION_ARGS')

        # SSL verification setting
        # SSL验证设置
        self.verify_ssl: Optional[bool] = settings.get("VERIFY_SSL")

        # SSL protocol version (e.g., ssl.PROTOCOL_TLSv1_2)
        # SSL协议版本（例如，ssl.PROTOCOL_TLSv1_2）
        self.ssl_protocol = settings.get("SSL_PROTOCOL")  # ssl.PROTOCOL_TLSv1_2

        # Whether to use a persistent session for all requests
        # 是否对所有请求使用持久会话
        self.use_session: bool = settings.getbool("USE_SESSION", False)

    @classmethod
    def from_settings(cls, settings: Settings):
        """
        Create a download handler from settings.
        从设置创建下载处理程序。

        This is a factory method that creates a new AioHttpDownloadHandler
        instance with the given settings.
        这是一个工厂方法，使用给定的设置创建一个新的AioHttpDownloadHandler实例。

        Args:
            settings: The settings to use for the handler.
                     用于处理程序的设置。

        Returns:
            AioHttpDownloadHandler: A new download handler instance.
                                   一个新的下载处理程序实例。
        """
        return cls(settings)

    def get_session(self, *args, **kwargs) -> aiohttp.ClientSession:
        """
        Get or create a shared aiohttp ClientSession.
        获取或创建共享的aiohttp ClientSession。

        This method returns the existing session if one exists, or creates
        a new one if none exists yet. This is used when USE_SESSION is True
        to reuse the same session for multiple requests.
        如果会话已存在，此方法返回现有会话；如果尚不存在，则创建一个新会话。
        当USE_SESSION为True时使用此方法，为多个请求重用相同的会话。

        Args:
            *args: Positional arguments to pass to aiohttp.ClientSession constructor.
                  传递给aiohttp.ClientSession构造函数的位置参数。
            **kwargs: Keyword arguments to pass to aiohttp.ClientSession constructor.
                     传递给aiohttp.ClientSession构造函数的关键字参数。

        Returns:
            aiohttp.ClientSession: The shared client session.
                                  共享的客户端会话。
        """
        if self.session is None:
            self.session = aiohttp.ClientSession(*args, **kwargs)
        return self.session

    async def download_request(self, request: Request, spider) -> HtmlResponse:
        """
        Download a request using aiohttp.
        使用aiohttp下载请求。

        This method implements the BaseDownloadHandler.download_request interface.
        It wraps the actual download logic in _download_request and handles
        aiohttp-specific exceptions.
        此方法实现了BaseDownloadHandler.download_request接口。
        它将实际的下载逻辑包装在_download_request中，并处理aiohttp特定的异常。

        Args:
            request: The request to download.
                    要下载的请求。
            spider: The spider making the request. This parameter is required by the
                   BaseDownloadHandler interface but is not used in this implementation.
                   发出请求的爬虫。此参数是BaseDownloadHandler接口所需的，但在此实现中未使用。
                   It is included to maintain compatibility with the interface and to allow
                   subclasses to use it if needed.
                   包含它是为了保持与接口的兼容性，并允许子类在需要时使用它。

        Returns:
            HtmlResponse: The response from the server.
                         来自服务器的响应。

        Raises:
            DownloadError: If an aiohttp ClientError occurs during the download.
                          如果在下载过程中发生aiohttp ClientError。
        """
        try:
            # The spider parameter is intentionally unused in this implementation
            # 在此实现中有意不使用spider参数
            return await self._download_request(request)
        except ClientError as e:
            # Wrap aiohttp-specific exceptions in a generic DownloadError
            # 将aiohttp特定的异常包装在通用的DownloadError中
            raise DownloadError(real_error=e) from e

    async def _download_request(self, request: Request) -> HtmlResponse:
        """
        Perform the actual download of a request using aiohttp.
        使用aiohttp执行请求的实际下载。

        This method handles the details of configuring and performing the HTTP request,
        including SSL settings, proxies, cookies, and session management. It supports
        various request options through request.meta:
        此方法处理配置和执行HTTP请求的详细信息，包括SSL设置、代理、Cookie和会话管理。
        它通过request.meta支持各种请求选项：

        - verify_ssl: Whether to verify SSL certificates
                     是否验证SSL证书
        - download_timeout: Timeout for the request in seconds
                          请求超时时间（秒）
        - dont_redirect: Whether to disable following redirects
                        是否禁用跟随重定向
        - TLS_CIPHERS: Custom SSL cipher suite to use
                      要使用的自定义SSL密码套件
        - ssl_protocol: SSL protocol version to use
                       要使用的SSL协议版本
        - proxy: Proxy URL to use for the request
                用于请求的代理URL

        Args:
            request: The request to download.
                    要下载的请求。
                    This includes the URL, method, headers, body, cookies, and
                    meta information for configuring the request.
                    这包括URL、方法、标头、正文、Cookie和用于配置请求的元信息。

        Returns:
            HtmlResponse: The response from the server.
                         来自服务器的响应。
                         This includes the status code, headers, body, cookies,
                         and encoding of the response.
                         这包括响应的状态码、标头、正文、Cookie和编码。
        """
        # Prepare request parameters
        # 准备请求参数
        kwargs = {
            'verify_ssl': request.meta.get('verify_ssl', self.verify_ssl),
            'timeout': request.meta.get('download_timeout', 180),
            'cookies': dict(request.cookies),
            'data': request.body or None,
            'allow_redirects': self.settings.getbool('REDIRECT_ENABLED', True) if request.meta.get(
                'dont_redirect') is None else request.meta.get('dont_redirect'),
            'max_redirects': self.settings.getint('REDIRECT_MAX_TIMES', 20),
        }

        # Set headers from request or default settings
        # 从请求或默认设置设置标头
        headers = request.headers or self.settings.get('DEFAULT_REQUEST_HEADERS')
        kwargs['headers'] = headers

        # Configure SSL context if needed
        # 如果需要，配置SSL上下文
        ssl_ciphers: str = request.meta.get('TLS_CIPHERS')
        ssl_protocol = request.meta.get('ssl_protocol', self.ssl_protocol)
        if ssl_ciphers or ssl_protocol:
            if ssl_protocol:
                context = ssl.SSLContext(protocol=ssl_protocol)
            else:
                context = ssl.create_default_context()

            ssl_ciphers and context.set_ciphers(ssl_ciphers)
            kwargs['ssl'] = context
            kwargs['verify_ssl'] = True

        # Configure proxy if specified
        # 如果指定，配置代理
        proxy: str = request.meta.get("proxy")
        if proxy:
            kwargs["proxy"] = proxy
            logger.debug(f"使用代理{proxy}抓取: {request.url}")

        # Perform the request using either a persistent session or a new session
        # 使用持久会话或新会话执行请求
        if self.use_session:
            # Not recommended to use session, The abnormal phenomena will occurs when using tunnel proxy
            # 不建议使用会话，使用隧道代理时会出现异常现象
            session = self.get_session(**self.aiohttp_client_session_args)
            async with session.request(request.method, request.url, **kwargs) as response:
                content: bytes = await response.read()
        else:
            # Create a new session for each request (recommended)
            # 为每个请求创建一个新会话（推荐）
            async with aiohttp.ClientSession(**self.aiohttp_client_session_args) as session:
                async with session.request(request.method, request.url, **kwargs) as response:
                    content: bytes = await response.read()

        # Process cookies from response
        # 处理响应中的Cookie
        r_cookies = response.cookies.output() or None
        if r_cookies:
            r_cookies = {
                cookie[0]: cookie[1] for cookie in re.findall(r'Set-Cookie: (.*?)=(.*?); Domain', r_cookies, re.S)
            }

        # Create and return the response object
        # 创建并返回响应对象
        return HtmlResponse(
            str(response.url),
            status=response.status,
            headers=response.headers,
            body=content,
            cookies=r_cookies,
            encoding=response.charset
        )

    async def close(self):
        """
        Close the download handler and release its resources.
        关闭下载处理程序并释放其资源。

        This method closes the shared session if one exists and waits for
        the underlying SSL connections to close properly. It follows the
        recommended graceful shutdown procedure for aiohttp sessions.
        此方法关闭共享会话（如果存在），并等待底层SSL连接正确关闭。
        它遵循aiohttp会话的推荐优雅关闭程序。

        The 250ms sleep after closing the session is recommended by the aiohttp
        documentation to allow the underlying SSL connections to be properly closed.
        Without this delay, SSL connections might be terminated abruptly, which
        can cause issues with some servers.
        关闭会话后的250毫秒睡眠是aiohttp文档推荐的，以允许底层SSL连接正确关闭。
        没有这个延迟，SSL连接可能会突然终止，这可能会导致某些服务器出现问题。

        See: https://docs.aiohttp.org/en/latest/client_advanced.html#graceful-shutdown
        参见：https://docs.aiohttp.org/en/latest/client_advanced.html#graceful-shutdown
        """
        if self.session is not None:
            # Close the shared session
            # 关闭共享会话
            await self.session.close()

            # Wait 250 ms for the underlying SSL connections to close
            # 等待250毫秒让底层SSL连接关闭
            # https://docs.aiohttp.org/en/latest/client_advanced.html#graceful-shutdown
            await asyncio.sleep(0.250)
