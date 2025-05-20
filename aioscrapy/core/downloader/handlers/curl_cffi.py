"""
Download handler implementation using curl_cffi.
使用curl_cffi的下载处理程序实现。

This module provides a download handler that uses curl_cffi to perform HTTP/HTTPS requests.
It supports features like browser impersonation, proxies, and cookies.
此模块提供了一个使用curl_cffi执行HTTP/HTTPS请求的下载处理程序。
它支持浏览器模拟、代理和Cookie等功能。
"""

from curl_cffi.curl import CurlError
from curl_cffi.requests import AsyncSession

from aioscrapy import Request
from aioscrapy.core.downloader.handlers import BaseDownloadHandler
from aioscrapy.exceptions import DownloadError
from aioscrapy.http import HtmlResponse
from aioscrapy.settings import Settings
from aioscrapy.utils.log import logger


class CurlCffiDownloadHandler(BaseDownloadHandler):
    """
    Download handler that uses curl_cffi to perform HTTP/HTTPS requests.
    使用curl_cffi执行HTTP/HTTPS请求的下载处理程序。

    This handler implements the BaseDownloadHandler interface using the curl_cffi
    library, which provides high-performance HTTP requests with browser fingerprinting
    capabilities.
    此处理程序使用curl_cffi库实现BaseDownloadHandler接口，该库提供具有浏览器指纹
    功能的高性能HTTP请求。
    """

    def __init__(self, settings):
        """
        Initialize the CurlCffiDownloadHandler.
        初始化CurlCffiDownloadHandler。

        Args:
            settings: The settings object containing configuration for the handler.
                     包含处理程序配置的设置对象。
        """
        self.settings: Settings = settings

        # Arguments to pass to curl_cffi AsyncSession constructor
        # 传递给curl_cffi AsyncSession构造函数的参数
        self.httpx_client_session_args: dict = self.settings.get('CURL_CFFI_CLIENT_SESSION_ARGS', {})

        # SSL verification setting
        # SSL验证设置
        self.verify_ssl: bool = self.settings.get("VERIFY_SSL", True)

    @classmethod
    def from_settings(cls, settings: Settings):
        """
        Create a download handler from settings.
        从设置创建下载处理程序。

        This is a factory method that creates a new CurlCffiDownloadHandler
        instance with the given settings.
        这是一个工厂方法，使用给定的设置创建一个新的CurlCffiDownloadHandler实例。

        Args:
            settings: The settings to use for the handler.
                     用于处理程序的设置。

        Returns:
            CurlCffiDownloadHandler: A new download handler instance.
                                    一个新的下载处理程序实例。
        """
        return cls(settings)

    async def download_request(self, request: Request, _) -> HtmlResponse:
        """
        Download a request using curl_cffi.
        使用curl_cffi下载请求。

        This method implements the BaseDownloadHandler.download_request interface.
        It wraps the actual download logic in _download_request and handles
        curl_cffi-specific exceptions.
        此方法实现了BaseDownloadHandler.download_request接口。
        它将实际的下载逻辑包装在_download_request中，并处理curl_cffi特定的异常。

        Args:
            request: The request to download.
                    要下载的请求。
            _: The spider (not used in this implementation).
               爬虫（在此实现中未使用）。

        Returns:
            HtmlResponse: The response from the server.
                         来自服务器的响应。

        Raises:
            DownloadError: If a CurlError occurs during the download.
                          如果在下载过程中发生CurlError。
        """
        try:
            return await self._download_request(request)
        except CurlError as e:
            # Wrap curl_cffi-specific exceptions in a generic DownloadError
            # 将curl_cffi特定的异常包装在通用的DownloadError中
            raise DownloadError(real_error=e) from e

    async def _download_request(self, request: Request) -> HtmlResponse:
        """
        Internal method to perform the actual download using curl_cffi.
        使用curl_cffi执行实际下载的内部方法。

        This method configures and uses a curl_cffi.AsyncSession to perform the request,
        handling SSL settings, proxies, cookies, browser impersonation, and other request parameters.
        此方法配置并使用curl_cffi.AsyncSession执行请求，处理SSL设置、代理、Cookie、
        浏览器模拟和其他请求参数。

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
                'dont_redirect') is None else request.meta.get('dont_redirect'),
            'impersonate': request.meta.get('impersonate'),  # Browser fingerprinting feature
                                                            # 浏览器指纹功能
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

        # Configure curl_cffi session
        # 配置curl_cffi会话
        session_args = self.httpx_client_session_args.copy()

        # Perform the request
        # 执行请求
        async with AsyncSession(**session_args) as session:
            response = await session.request(request.method, request.url, **kwargs)

        # Convert curl_cffi response to HtmlResponse
        # 将curl_cffi响应转换为HtmlResponse
        return HtmlResponse(
            str(response.url),
            status=response.status_code,
            headers=response.headers,
            body=response.content,
            cookies={j.name: j.value or '' for j in response.cookies.jar},
            encoding=response.encoding
        )

    async def close(self):
        """
        Close the download handler and release resources.
        关闭下载处理程序并释放资源。

        This method is called when the spider is closing. In this implementation,
        there are no persistent resources to clean up since curl_cffi.AsyncSession
        is created and closed for each request.
        当爬虫关闭时调用此方法。在此实现中，没有需要清理的持久资源，
        因为curl_cffi.AsyncSession是为每个请求创建和关闭的。
        """
        pass
