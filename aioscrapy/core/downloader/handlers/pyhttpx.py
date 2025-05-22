"""
Download handler implementation using pyhttpx.
使用pyhttpx的下载处理程序实现。

This module provides a download handler that uses pyhttpx to perform HTTP/HTTPS requests.
It supports HTTP/2, proxies, and cookies, and runs synchronous pyhttpx in a thread pool.
此模块提供了一个使用pyhttpx执行HTTP/HTTPS请求的下载处理程序。
它支持HTTP/2、代理和Cookie，并在线程池中运行同步的pyhttpx。
"""

import asyncio

import pyhttpx
from pyhttpx.exception import BaseExpetion as PyHttpxError

from aioscrapy import Request
from aioscrapy.core.downloader.handlers import BaseDownloadHandler
from aioscrapy.exceptions import DownloadError
from aioscrapy.http import HtmlResponse
from aioscrapy.settings import Settings
from aioscrapy.utils.log import logger


class PyhttpxDownloadHandler(BaseDownloadHandler):
    """
    Download handler that uses pyhttpx to perform HTTP/HTTPS requests.
    使用pyhttpx执行HTTP/HTTPS请求的下载处理程序。

    This handler implements the BaseDownloadHandler interface using the pyhttpx
    library, which provides HTTP client features including HTTP/2 support.
    Since pyhttpx is synchronous, this handler runs it in a thread pool.
    此处理程序使用pyhttpx库实现BaseDownloadHandler接口，该库提供包括HTTP/2支持的HTTP客户端功能。
    由于pyhttpx是同步的，此处理程序在线程池中运行它。
    """

    def __init__(self, settings):
        """
        Initialize the PyhttpxDownloadHandler.
        初始化PyhttpxDownloadHandler。

        Args:
            settings: The settings object containing configuration for the handler.
                     包含处理程序配置的设置对象。
        """
        self.settings: Settings = settings

        # Arguments to pass to pyhttpx HttpSession constructor
        # 传递给pyhttpx HttpSession构造函数的参数
        self.pyhttpx_args: dict = self.settings.get('PYHTTPX_ARGS', {})

        # SSL verification setting
        # SSL验证设置
        self.verify_ssl = self.settings.get("VERIFY_SSL", True)

        # Get the current event loop for running pyhttpx in a thread pool
        # 获取当前事件循环，用于在线程池中运行pyhttpx
        self.loop = asyncio.get_running_loop()

    @classmethod
    def from_settings(cls, settings: Settings):
        """
        Create a download handler from settings.
        从设置创建下载处理程序。

        This is a factory method that creates a new PyhttpxDownloadHandler
        instance with the given settings.
        这是一个工厂方法，使用给定的设置创建一个新的PyhttpxDownloadHandler实例。

        Args:
            settings: The settings to use for the handler.
                     用于处理程序的设置。

        Returns:
            PyhttpxDownloadHandler: A new download handler instance.
                                   一个新的下载处理程序实例。
        """
        return cls(settings)

    async def download_request(self, request: Request, _) -> HtmlResponse:
        """
        Download a request using pyhttpx.
        使用pyhttpx下载请求。

        This method implements the BaseDownloadHandler.download_request interface.
        It wraps the actual download logic in _download_request and handles
        pyhttpx-specific exceptions.
        此方法实现了BaseDownloadHandler.download_request接口。
        它将实际的下载逻辑包装在_download_request中，并处理pyhttpx特定的异常。

        Args:
            request: The request to download.
                    要下载的请求。
            _: The spider (not used in this implementation).
               爬虫（在此实现中未使用）。

        Returns:
            HtmlResponse: The response from the server.
                         来自服务器的响应。

        Raises:
            DownloadError: If a PyHttpxError occurs during the download.
                          如果在下载过程中发生PyHttpxError。
        """
        try:
            return await self._download_request(request)
        except PyHttpxError as e:
            # Wrap pyhttpx-specific exceptions in a generic DownloadError
            # 将pyhttpx特定的异常包装在通用的DownloadError中
            raise DownloadError(real_error=e) from e

    async def _download_request(self, request: Request) -> HtmlResponse:
        """
        Internal method to perform the actual download using pyhttpx.
        使用pyhttpx执行实际下载的内部方法。

        This method configures and uses a pyhttpx.HttpSession to perform the request,
        handling SSL settings, proxies, cookies, and other request parameters.
        Since pyhttpx is synchronous, it runs in a thread pool using asyncio.to_thread.
        此方法配置并使用pyhttpx.HttpSession执行请求，处理SSL设置、代理、Cookie和其他请求参数。
        由于pyhttpx是同步的，它使用asyncio.to_thread在线程池中运行。

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
            'verify': self.verify_ssl,
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
            kwargs["proxies"] = {'https': proxy}
            logger.debug(f"use proxy {proxy}: {request.url}")

        # Configure pyhttpx session
        # 配置pyhttpx会话
        session_args = self.pyhttpx_args.copy()
        session_args.setdefault('http2', True)  # Enable HTTP/2 by default
                                               # 默认启用HTTP/2

        if ja3 := request.meta.get("ja3"):
            session_args['ja3'] = ja3

        # Execute the request in a thread pool since pyhttpx is synchronous
        # 由于pyhttpx是同步的，在线程池中执行请求
        with pyhttpx.HttpSession(**session_args) as session:
            # Run the synchronous pyhttpx request in a thread pool
            # 在线程池中运行同步的pyhttpx请求
            response = await asyncio.to_thread(session.request, request.method, request.url, **kwargs)

            # Convert pyhttpx response to HtmlResponse
            # 将pyhttpx响应转换为HtmlResponse
            return HtmlResponse(
                request.url,
                status=response.status_code,
                headers=response.headers,
                body=response.content,
                cookies=dict(response.cookies),
                encoding=response.encoding
            )

    async def close(self):
        """
        Close the download handler and release resources.
        关闭下载处理程序并释放资源。

        This method is called when the spider is closing. In this implementation,
        there are no persistent resources to clean up since pyhttpx.HttpSession
        is created and closed for each request.
        当爬虫关闭时调用此方法。在此实现中，没有需要清理的持久资源，
        因为pyhttpx.HttpSession是为每个请求创建和关闭的。
        """
        pass
