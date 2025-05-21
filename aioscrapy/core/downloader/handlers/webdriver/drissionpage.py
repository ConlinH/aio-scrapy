"""
Download handler implementation using DrissionPage.
使用DrissionPage的下载处理程序实现。

This module provides a download handler that uses DrissionPage to perform browser-based HTTP requests.
It supports full browser automation, JavaScript execution, and event handling.
此模块提供了一个使用DrissionPage执行基于浏览器的HTTP请求的下载处理程序。
它支持完整的浏览器自动化、JavaScript执行和事件处理。
"""

import asyncio
from typing import Dict, Optional, Tuple, Any
from urllib.parse import urlparse

from DrissionPage.errors import BaseError
from DrissionPage import ChromiumPage, ChromiumOptions

from aioscrapy import Request, Spider
from aioscrapy.core.downloader.handlers import BaseDownloadHandler
from aioscrapy.exceptions import DownloadError, NotSupported
from aioscrapy.http import WebDriverResponse
from aioscrapy.settings import Settings
from .driverpool import WebDriverPool, WebDriverBase


class DrissionPageDriver(WebDriverBase):
    """
    A wrapper around DrissionPage's browser automation API.
    对DrissionPage浏览器自动化API的包装。

    This class provides a simplified interface for working with DrissionPage browsers,
    handling initialization, proxy configuration, and browser lifecycle management.
    此类提供了一个简化的接口来使用DrissionPage浏览器，处理初始化、代理配置和浏览器生命周期管理。
    """
    _port = 0

    @classmethod
    def port(cls):
        """
        Generate a unique port number for browser instances.
        为浏览器实例生成唯一的端口号。

        This method increments a class-level counter to ensure each browser instance
        gets a unique debugging port, which prevents port conflicts when running
        multiple browser instances simultaneously.
        此方法递增类级别计数器，以确保每个浏览器实例获得唯一的调试端口，
        这可以防止同时运行多个浏览器实例时发生端口冲突。

        Returns:
            int: A unique port number.
                一个唯一的端口号。
        """
        cls._port += 1
        return cls._port

    def __init__(
            self,
            *,
            proxy: Optional[str] = None,
            user_agent: str = None,
            headless: bool = False,
            arguments=None,
            max_uses: Optional[int] = None,
            **kwargs  # Additional arguments (not used directly)
                     # 其他参数（不直接使用）
    ):
        """
        Initialize the DrissionPageDriver.
        初始化DrissionPageDriver。

        Args:
            proxy: Optional proxy URL to use for browser connections.
                  用于浏览器连接的可选代理URL。
            user_agent: Optional user agent string to use.
                        要使用的可选用户代理字符串。
            headless: Whether to run the browser in headless mode (without GUI).
                     是否在无头模式下运行浏览器（无GUI）。
            arguments: Additional command-line arguments to pass to the browser.
                      传递给浏览器的其他命令行参数。
            max_uses: Optional count of uses after which the browser should be recycled.
                      浏览器应该被回收的使用次数的可选计数。
            **kwargs: Additional arguments passed to the parent class or for future extensions.
                     传递给父类的其他参数或用于未来扩展。
                     These arguments are intentionally not used directly in this implementation
                     but are included for compatibility with the WebDriverBase interface.
                     这些参数在此实现中有意不直接使用，但包含它们是为了与WebDriverBase接口兼容。
        """
        # Browser configuration
        # 浏览器配置
        self.proxy = proxy  # Proxy URL 代理URL
        self.max_uses = max_uses  # Counter for browser recycling 浏览器回收计数器
        self.user_agent = user_agent  # User agent string 用户代理字符串
        self.headless = headless
        self.arguments = arguments  # Apply additional browser arguments 浏览器启动参数

        # DrissionPage components (initialized in setup())
        # DrissionPage组件（在setup()中初始化）
        self.page: Optional[ChromiumPage] = None  # Browser page 浏览器页面
        self.url = None  # Current URL (used for cookie management) 当前URL（用于Cookie管理）

    async def setup(self):
        """
        Initialize the DrissionPage browser and page.
        初始化DrissionPage浏览器和页面。

        This method creates a ChromiumOptions instance with the specified configuration,
        then initializes a ChromiumPage with these options. It applies all configuration
        options such as proxy settings, window size, and user agent.
        此方法创建具有指定配置的ChromiumOptions实例，然后使用这些选项初始化ChromiumPage。
        它应用所有配置选项，如代理设置、窗口大小和用户代理。

        Returns:
            None
        """
        # Run the browser initialization in a separate thread to avoid blocking the event loop
        # 在单独的线程中运行浏览器初始化，以避免阻塞事件循环
        await asyncio.to_thread(self._setup_sync)

    def _setup_sync(self):
        """
        Synchronous implementation of browser setup.
        浏览器设置的同步实现。

        This method is called by setup() in a separate thread to perform the actual
        browser initialization without blocking the event loop.
        此方法由setup()在单独的线程中调用，以执行实际的浏览器初始化，而不会阻塞事件循环。

        Returns:
            None
        """
        # Create ChromiumOptions with the specified configuration
        # 使用指定的配置创建ChromiumOptions
        co = ChromiumOptions()

        co.set_local_port(9221+self.port())

        # Apply additional browser arguments
        # 应用其他浏览器参数
        if self.arguments:
            for arg in self.arguments:
                if isinstance(arg, str):
                    co.set_argument(arg)
                elif isinstance(arg, (list, tuple)):
                    co.set_argument(*arg)
                else:
                    raise BaseError(f"arguments error: {arg}")

        co.headless(self.headless)

        # Apply proxy settings if specified
        # 如果指定了代理设置，则应用它们
        if self.proxy:
            proxy_url = urlparse(self.proxy)
            proxy_server = f"{proxy_url.scheme}://{proxy_url.netloc}"
            co.set_proxy(proxy_server)

        # Apply user agent if specified
        # 如果指定了用户代理，则应用它
        if self.user_agent:
            co.set_user_agent(self.user_agent)

        # Create the ChromiumPage with the configured options
        # 使用配置的选项创建ChromiumPage
        self.page = ChromiumPage(co)

    async def quit(self):
        """
        Close the browser and clean up resources.
        关闭浏览器并清理资源。

        This method closes the browser and releases all associated resources.
        此方法关闭浏览器并释放所有相关资源。

        Returns:
            None
        """
        # Run the browser cleanup in a separate thread to avoid blocking the event loop
        # 在单独的线程中运行浏览器清理，以避免阻塞事件循环
        if self.page:
            await asyncio.to_thread(self._quit_sync)

    def _quit_sync(self):
        """
        Synchronous implementation of browser cleanup.
        浏览器清理的同步实现。

        This method is called by quit() in a separate thread to perform the actual
        browser cleanup without blocking the event loop.
        此方法由quit()在单独的线程中调用，以执行实际的浏览器清理，而不会阻塞事件循环。

        Returns:
            None
        """
        if self.page:
            self.page.quit()

    async def get_cookies(self) -> Dict[str, str]:
        """
        Get all cookies from the browser.
        从浏览器获取所有Cookie。

        This method retrieves all cookies from the current browser session
        and returns them as a dictionary of name-value pairs.
        此方法从当前浏览器会话检索所有Cookie，并将它们作为名称-值对的字典返回。

        Returns:
            dict: A dictionary of cookie name-value pairs.
                 Cookie名称-值对的字典。
        """
        # Run the cookie retrieval in a separate thread to avoid blocking the event loop
        # 在单独的线程中运行Cookie检索，以避免阻塞事件循环
        cookies = await asyncio.to_thread(self._get_cookies_sync)
        return cookies

    def _get_cookies_sync(self) -> Dict[str, str]:
        """
        Synchronous implementation of cookie retrieval.
        Cookie检索的同步实现。

        This method is called by get_cookies() in a separate thread to perform the actual
        cookie retrieval without blocking the event loop.
        此方法由get_cookies()在单独的线程中调用，以执行实际的Cookie检索，而不会阻塞事件循环。

        Returns:
            dict: A dictionary of cookie name-value pairs.
                 Cookie名称-值对的字典。
        """
        # Convert the list of cookie objects to a name-value dictionary
        # 将Cookie对象列表转换为名称-值字典
        cookies = {}
        if self.page:
            for cookie in self.page.cookies(all_domains=True):
                cookies[cookie.get('name')] = cookie.get('value')
        return cookies

    async def set_cookies(self, cookies: Dict[str, str]):
        """
        Set cookies in the browser.
        在浏览器中设置Cookie。

        This method adds the provided cookies to the browser,
        associating them with the current URL.
        此方法将提供的Cookie添加到浏览器中，将它们与当前URL关联。

        Args:
            cookies: A dictionary of cookie name-value pairs to set.
                    要设置的Cookie名称-值对的字典。

        Returns:
            None
        """
        # Run the cookie setting in a separate thread to avoid blocking the event loop
        # 在单独的线程中运行Cookie设置，以避免阻塞事件循环
        await asyncio.to_thread(self._set_cookies_sync, cookies)

    def _set_cookies_sync(self, cookies: Dict[str, str]):
        """
        Synchronous implementation of cookie setting.
        Cookie设置的同步实现。

        This method is called by set_cookies() in a separate thread to perform the actual
        cookie setting without blocking the event loop.
        此方法由set_cookies()在单独的线程中调用，以执行实际的Cookie设置，而不会阻塞事件循环。

        Args:
            cookies: A dictionary of cookie name-value pairs to set.
                    要设置的Cookie名称-值对的字典。

        Returns:
            None
        """
        if self.page:
            self.page.set.cookies(cookies)


class DrissionPageHandler(BaseDownloadHandler):
    """
    Download handler that uses DrissionPage to perform browser-based HTTP requests.
    使用DrissionPage执行基于浏览器的HTTP请求的下载处理程序。

    This handler implements the BaseDownloadHandler interface using DrissionPage,
    which provides a high-level API to control browsers. It supports full browser
    automation, JavaScript execution, and event handling.
    此处理程序使用DrissionPage实现BaseDownloadHandler接口，DrissionPage提供了控制浏览器的
    高级API。它支持完整的浏览器自动化、JavaScript执行和事件处理。
    """

    def __init__(self, settings: Settings):
        """
        Initialize the DrissionPageHandler.
        初始化DrissionPageHandler。

        Args:
            settings: The settings object containing configuration for the handler.
                     包含处理程序配置的设置对象。
        """
        self.settings = settings

        # Get DrissionPage client arguments from settings
        # 从设置中获取DrissionPage客户端参数
        client_args = settings.getdict('DP_CLIENT_ARGS', {})

        # Configure the pool size for browser instances
        # 配置浏览器实例的池大小
        pool_size = client_args.pop('pool_size', settings.getint("CONCURRENT_REQUESTS", 1))

        # Initialize the WebDriver pool
        # 初始化WebDriver池
        self._webdriver_pool = WebDriverPool(DrissionPageDriver, pool_size=pool_size, **client_args)

    @classmethod
    def from_settings(cls, settings: Settings):
        """
        Create a download handler from settings.
        从设置创建下载处理程序。

        This is a factory method that creates a new DrissionPageHandler
        instance with the given settings.
        这是一个工厂方法，使用给定的设置创建一个新的DrissionPageHandler实例。

        Args:
            settings: The settings to use for the handler.
                     用于处理程序的设置。

        Returns:
            DrissionPageHandler: A new download handler instance.
                               一个新的下载处理程序实例。
        """
        return cls(settings)

    async def download_request(self, request: Request, spider: Spider) -> WebDriverResponse:
        """
        Download a request using DrissionPage.
        使用DrissionPage下载请求。

        This method implements the BaseDownloadHandler.download_request interface.
        It wraps the actual download logic in _download_request and handles
        DrissionPage-specific exceptions.
        此方法实现了BaseDownloadHandler.download_request接口。
        它将实际的下载逻辑包装在_download_request中，并处理DrissionPage特定的异常。

        Args:
            request: The request to download.
                    要下载的请求。
            spider: The spider that initiated the request.
                   发起请求的爬虫。

        Returns:
            WebDriverResponse: The response from the browser with DrissionPage driver attached.
                              附加了DrissionPage驱动程序的浏览器响应。
                              This response contains the page content, cookies, and a reference
                              to the browser instance for further interaction.
                              此响应包含页面内容、Cookie和对浏览器实例的引用，以便进一步交互。

        Raises:
            DownloadError: If a DrissionPage error or any other exception occurs during the download.
                          如果在下载过程中发生DrissionPage错误或任何其他异常。
        """
        try:
            return await self._download_request(request, spider)
        except BaseError as e:
            # Wrap DrissionPage-specific exceptions in a generic DownloadError
            # 将DrissionPage特定的异常包装在通用的DownloadError中
            raise DownloadError(real_error=e) from e

    async def _download_request(self, request: Request, spider) -> WebDriverResponse:
        """
        Internal method to perform the actual download using DrissionPage.
        使用DrissionPage执行实际下载的内部方法。

        This method configures and uses a DrissionPage browser to perform the request,
        handling cookies, user agent, proxies, and event listeners. It also supports
        custom browser actions defined in the spider.
        此方法配置并使用DrissionPage浏览器执行请求，处理Cookie、用户代理、代理和事件监听器。
        它还支持在爬虫中定义的自定义浏览器操作。

        Args:
            request: The request to download.
                    要下载的请求。
            spider: The spider that initiated the request.
                   发起请求的爬虫。
                   This can be used to access spider-specific settings and methods,
                   particularly the process_action method if defined.
                   这可用于访问爬虫特定的设置和方法，特别是process_action方法（如果已定义）。

        Returns:
            WebDriverResponse: The response from the browser with DrissionPage driver attached.
                              附加了DrissionPage驱动程序的浏览器响应。
                              This response contains the page content, cookies, and a reference
                              to the browser instance for further interaction.
                              此响应包含页面内容、Cookie和对浏览器实例的引用，以便进一步交互。

        Raises:
            NotSupported: If the spider's process_action method is defined as an async function.
                         如果爬虫的process_action方法被定义为异步函数。
            Exception: If any other error occurs during the browser automation.
                      如果在浏览器自动化过程中发生任何其他错误。
        """
        # Extract request parameters
        # 提取请求参数
        cookies = dict(request.cookies)
        timeout = request.meta.get('download_timeout', 30)  # In seconds
                                                           # 以秒为单位
        user_agent = request.headers.get("User-Agent")
        proxy: str = request.meta.get("proxy")
        url = request.url

        # Dictionary to store custom data
        # 存储自定义数据的字典
        cache_response = {}

        # Configure browser options
        # 配置浏览器选项
        kwargs = dict()
        if proxy:
            kwargs['proxy'] = proxy
        if user_agent:
            kwargs['user_agent'] = user_agent

        # Get a browser instance from the pool
        # 从池中获取浏览器实例
        driver: DrissionPageDriver = await self._webdriver_pool.get(**kwargs)

        try:
            # Set cookies if provided
            # 如果提供了Cookie，则设置Cookie
            if cookies:
                driver.url = url
                await driver.set_cookies(cookies)

            driver.page.listen.start('gitee.com/explore')
            # Navigate to the URL
            # 导航到URL
            await asyncio.to_thread(driver.page.get, url, timeout=timeout)

            # Execute custom actions if defined in the spider
            # 如果在爬虫中定义了自定义操作，则执行
            if process_action_fn := getattr(spider, 'process_action', None):
                if asyncio.iscoroutinefunction(process_action_fn):
                    raise NotSupported(f'process_action can not use async')

                action_result = await asyncio.to_thread(process_action_fn, driver, request)
                if action_result:
                    cache_response[action_result[0]] = action_result[1]

            def get_html(d):
                """
                Get the HTML content of the current page.
                获取当前页面的HTML内容。

                This is a helper function to get the HTML content from the driver
                in a way that can be run in a separate thread.
                这是一个辅助函数，用于以可以在单独线程中运行的方式从驱动程序获取HTML内容。

                Args:
                    d: The DrissionPageDriver instance.
                       DrissionPageDriver实例。

                Returns:
                    str: The HTML content of the current page.
                        当前页面的HTML内容。
                """
                return d.page.html

            # Create and return the final response
            # 创建并返回最终响应
            return WebDriverResponse(
                url=driver.page.url,
                status=200,
                text=await asyncio.to_thread(get_html, driver),
                cookies=await driver.get_cookies(),
                cache_response=cache_response,
                driver=driver,
                driver_pool=self._webdriver_pool
            )
        except Exception as e:
            # Remove the driver from the pool on error
            # 出错时从池中移除驱动程序
            await self._webdriver_pool.remove(driver)
            raise e

    async def close(self):
        """
        Close the download handler and release resources.
        关闭下载处理程序并释放资源。

        This method is called when the spider is closing. It closes all browser
        instances in the pool and releases associated resources.
        当爬虫关闭时调用此方法。它关闭池中的所有浏览器实例并释放相关资源。
        """
        # Close all browser instances in the pool
        # 关闭池中的所有浏览器实例
        await self._webdriver_pool.close()
