"""
Download handler implementation using Playwright.
使用Playwright的下载处理程序实现。

This module provides a download handler that uses Playwright to perform browser-based HTTP requests.
It supports full browser automation, JavaScript execution, and event handling.
此模块提供了一个使用Playwright执行基于浏览器的HTTP请求的下载处理程序。
它支持完整的浏览器自动化、JavaScript执行和事件处理。
"""
import os
from functools import wraps
from typing import Dict, Optional, Tuple, Literal
from urllib.parse import urlparse, urlunparse


try:
    from playwright._impl._errors import Error
except ImportError:
    from playwright._impl._api_types import Error

from playwright.async_api._generated import Response as EventResponse
from playwright.async_api import Page, BrowserContext, ViewportSize, ProxySettings
from playwright.async_api import Playwright, Browser
from playwright.async_api import async_playwright

from aioscrapy import Request, Spider
from aioscrapy.core.downloader.handlers import BaseDownloadHandler
from aioscrapy.exceptions import DownloadError
from aioscrapy.http import WebDriverResponse
from aioscrapy.settings import Settings
from aioscrapy.utils.tools import call_helper
from .driverpool import WebDriverPool, WebDriverBase


class PlaywrightDriver(WebDriverBase):
    """
    A wrapper around Playwright's browser automation API.
    对Playwright浏览器自动化API的包装。

    This class provides a simplified interface for working with Playwright browsers,
    handling initialization, proxy configuration, and browser lifecycle management.
    此类提供了一个简化的接口来使用Playwright浏览器，处理初始化、代理配置和浏览器生命周期管理。
    """

    def __init__(
            self,
            *,
            driver_type: Literal["chromium", "firefox", "webkit"] = "chromium",
            proxy: Optional[str] = None,
            browser_args: Optional[Dict] = None,
            context_args: Optional[Dict] = None,
            window_size: Optional[Tuple[int, int]] = None,
            user_agent: str = None,
            max_uses: Optional[int] = None,
            **kwargs  # Additional arguments (not used directly)
                     # 其他参数（不直接使用）
    ):
        """
        Initialize the PlaywrightDriver.
        初始化PlaywrightDriver。

        Args:
            driver_type: The type of browser to use ("chromium", "firefox", or "webkit").
                        要使用的浏览器类型（"chromium"、"firefox"或"webkit"）。
            proxy: Optional proxy URL to use for browser connections.
                  用于浏览器连接的可选代理URL。
            browser_args: Optional arguments to pass to browser.launch().
                         传递给browser.launch()的可选参数。
            context_args: Optional arguments to pass to browser.new_context().
                         传递给browser.new_context()的可选参数。
            window_size: Optional tuple of (width, height) for the browser window size.
                        浏览器窗口大小的可选元组(width, height)。
            user_agent: Optional user agent string to use.
                       要使用的可选用户代理字符串。
            max_uses: Optional count of uses after which the browser should be recycled.
                      浏览器应该被回收的使用次数的可选计数。
            **kwargs: Additional arguments (not used directly).
                     其他参数（不直接使用）。
        """
        # Browser configuration
        # 浏览器配置
        self.driver_type = driver_type  # Type of browser to use
                                       # 要使用的浏览器类型
        self.proxy = proxy and self.format_context_proxy(proxy)  # Formatted proxy settings
                                                                # 格式化的代理设置
        self.viewport = window_size and ViewportSize(width=window_size[0], height=window_size[1])  # Browser viewport size
                                                                                                  # 浏览器视口大小
        self.browser_args = browser_args or {}  # Arguments for browser.launch()
                                               # browser.launch()的参数
        self.context_args = context_args or {}  # Arguments for browser.new_context()
                                               # browser.new_context()的参数
        self.user_agent = user_agent  # User agent string
                                     # 用户代理字符串

        # Playwright components (initialized in setup())
        # Playwright组件（在setup()中初始化）
        self.driver: Optional[Playwright] = None  # Playwright instance
                                                 # Playwright实例
        self.browser: Optional[Browser] = None  # Browser instance
                                               # 浏览器实例
        self.context: Optional[BrowserContext] = None  # Browser context
                                                      # 浏览器上下文
        self.page: Optional[Page] = None  # Browser page
                                         # 浏览器页面
        self.url = None  # Current URL (used for cookie management)
                        # 当前URL（用于Cookie管理）
        self.max_uses = max_uses  # Counter for browser recycling
                                  # 浏览器回收计数器

    async def setup(self):
        """
        Initialize the Playwright browser and page.
        初始化Playwright浏览器和页面。

        This method starts Playwright, launches the browser, creates a browser context,
        and opens a new page. It applies all configuration options such as proxy settings,
        viewport size, and user agent.
        此方法启动Playwright，启动浏览器，创建浏览器上下文，并打开新页面。
        它应用所有配置选项，如代理设置、视口大小和用户代理。

        Returns:
            None
        """
        # Create copies of argument dictionaries to avoid modifying the originals
        # 创建参数字典的副本，以避免修改原始字典
        browser_args = self.browser_args.copy()
        context_args = self.context_args.copy()

        # Add --no-sandbox argument for Chrome if not specified
        # 如果未指定，为Chrome添加--no-sandbox参数
        if browser_args.get('args') is None:
            browser_args.update({'args': ["--no-sandbox"]})

        # Ensure storage state directory exists if specified
        # 如果指定了存储状态目录，确保它存在
        if context_args.get("storage_state") is not None:
            storage_state_path = context_args.get("storage_state")
            os.makedirs(os.path.dirname(storage_state_path), exist_ok=True)

        # Apply proxy settings if specified
        # 如果指定了代理设置，则应用它们
        if self.proxy:
            browser_args.update({'proxy': self.proxy})
            context_args.update({'proxy': self.proxy})

        # Apply viewport settings if specified
        # 如果指定了视口设置，则应用它们
        if self.viewport:
            context_args.update({"viewport": self.viewport})
            context_args.update({"screen": self.viewport})

        # Apply user agent if specified
        # 如果指定了用户代理，则应用它
        if self.user_agent:
            context_args.update({'user_agent': self.user_agent})

        # Start Playwright and launch browser
        # 启动Playwright和浏览器
        self.driver = await async_playwright().start()
        self.browser: Browser = await getattr(self.driver, self.driver_type).launch(**browser_args)

        # Create browser context and page
        # 创建浏览器上下文和页面
        self.context = await self.browser.new_context(**context_args)
        self.page = await self.context.new_page()

    @staticmethod
    def format_context_proxy(proxy) -> ProxySettings:
        """
        Format a proxy URL into Playwright's ProxySettings object.
        将代理URL格式化为Playwright的ProxySettings对象。

        This method parses a proxy URL (e.g., http://user:pass@host:port) and converts
        it into a ProxySettings object that Playwright can use.
        此方法解析代理URL（例如，http://user:pass@host:port）并将其转换为
        Playwright可以使用的ProxySettings对象。

        Args:
            proxy: The proxy URL string.
                  代理URL字符串。

        Returns:
            ProxySettings: A Playwright ProxySettings object with server, username, and password.
                          包含服务器、用户名和密码的Playwright ProxySettings对象。
        """
        # Parse the proxy URL
        # 解析代理URL
        parsed_url = urlparse(proxy)

        # Create and return a ProxySettings object
        # 创建并返回ProxySettings对象
        return ProxySettings(
            # Remove username:password from the server URL
            # 从服务器URL中移除username:password
            server=urlunparse(parsed_url._replace(netloc=parsed_url.netloc.split('@')[-1])),
            username=parsed_url.username,
            password=parsed_url.password,
        )

    async def quit(self):
        """
        Close the browser and clean up resources.
        关闭浏览器并清理资源。

        This method closes the page, browser context, browser, and stops the
        Playwright instance, releasing all associated resources.
        此方法关闭页面、浏览器上下文、浏览器，并停止Playwright实例，
        释放所有相关资源。

        Returns:
            None
        """
        # Close the page first
        # 首先关闭页面
        await self.page.close()

        try:
            # Try to close the browser context
            # 尝试关闭浏览器上下文
            await self.context.close()
        except:
            # Ignore errors when closing the context
            # 关闭上下文时忽略错误
            pass
        finally:
            # Always close the browser and stop Playwright
            # 始终关闭浏览器并停止Playwright
            await self.browser.close()
            await self.driver.stop()

    async def get_cookies(self):
        """
        Get all cookies from the browser context.
        从浏览器上下文获取所有Cookie。

        This method retrieves all cookies from the current browser context
        and returns them as a dictionary of name-value pairs.
        此方法从当前浏览器上下文检索所有Cookie，并将它们作为名称-值对的字典返回。

        Returns:
            dict: A dictionary of cookie name-value pairs.
                 Cookie名称-值对的字典。
        """
        # Convert the list of cookie objects to a name-value dictionary
        # 将Cookie对象列表转换为名称-值字典
        return {
            cookie["name"]: cookie["value"]
            for cookie in await self.page.context.cookies()
        }

    async def set_cookies(self, cookies: dict):
        """
        Set cookies in the browser context.
        在浏览器上下文中设置Cookie。

        This method adds the provided cookies to the browser context,
        associating them with the current URL.
        此方法将提供的Cookie添加到浏览器上下文中，将它们与当前URL关联。

        Args:
            cookies: A dictionary of cookie name-value pairs to set.
                    要设置的Cookie名称-值对的字典。

        Returns:
            None
        """
        # Convert the dictionary to the format expected by Playwright
        # 将字典转换为Playwright期望的格式
        await self.page.context.add_cookies([
            {
                "name": key,
                "value": value,
                # Use the stored URL or current page URL
                # 使用存储的URL或当前页面URL
                "url": self.url or self.page.url
            }
            for key, value in cookies.items()
        ])


class PlaywrightDownloadHandler(BaseDownloadHandler):
    """
    Download handler that uses Playwright to perform browser-based HTTP requests.
    使用Playwright执行基于浏览器的HTTP请求的下载处理程序。

    This handler implements the BaseDownloadHandler interface using Playwright,
    which provides a high-level API to control browsers. It supports full browser
    automation, JavaScript execution, and event handling.
    此处理程序使用Playwright实现BaseDownloadHandler接口，Playwright提供了控制浏览器的
    高级API。它支持完整的浏览器自动化、JavaScript执行和事件处理。
    """

    def __init__(self, settings: Settings):
        """
        Initialize the PlaywrightHandler.
        初始化PlaywrightHandler。

        Args:
            settings: The settings object containing configuration for the handler.
                     包含处理程序配置的设置对象。
        """
        self.settings = settings

        # Get Playwright client arguments from settings
        # 从设置中获取Playwright客户端参数
        playwright_client_args = settings.getdict('PLAYWRIGHT_ARGS')

        # Set the default page load event to wait for
        # 设置要等待的默认页面加载事件
        self.wait_until = playwright_client_args.get('wait_until', 'domcontentloaded')

        # Configure the pool size for browser instances
        # 配置浏览器实例的池大小
        pool_size = playwright_client_args.pop('pool_size', settings.getint("CONCURRENT_REQUESTS", 1))

        # Initialize the WebDriver pool
        # 初始化WebDriver池
        self._webdriver_pool = WebDriverPool(PlaywrightDriver, pool_size=pool_size,  **playwright_client_args)

    @classmethod
    def from_settings(cls, settings: Settings):
        """
        Create a download handler from settings.
        从设置创建下载处理程序。

        This is a factory method that creates a new PlaywrightHandler
        instance with the given settings.
        这是一个工厂方法，使用给定的设置创建一个新的PlaywrightHandler实例。

        Args:
            settings: The settings to use for the handler.
                     用于处理程序的设置。

        Returns:
            PlaywrightHandler: A new download handler instance.
                              一个新的下载处理程序实例。
        """
        return cls(settings)

    async def download_request(self, request: Request, spider: Spider) -> WebDriverResponse:
        """
        Download a request using Playwright.
        使用Playwright下载请求。

        This method implements the BaseDownloadHandler.download_request interface.
        It wraps the actual download logic in _download_request and handles
        Playwright-specific exceptions.
        此方法实现了BaseDownloadHandler.download_request接口。
        它将实际的下载逻辑包装在_download_request中，并处理Playwright特定的异常。

        Args:
            request: The request to download.
                    要下载的请求。
            spider: The spider that initiated the request.
                   发起请求的爬虫。

        Returns:
            PlaywrightResponse: The response from the browser.
                               来自浏览器的响应。

        Raises:
            DownloadError: If a Playwright error or any other exception occurs during the download.
                          如果在下载过程中发生Playwright错误或任何其他异常。
        """
        try:
            return await self._download_request(request, spider)
        except Error as e:
            # Wrap Playwright-specific exceptions in a generic DownloadError
            # 将Playwright特定的异常包装在通用的DownloadError中
            raise DownloadError(real_error=e) from e
        except Exception as e:
            # Wrap any other exceptions in a generic DownloadError
            # 将任何其他异常包装在通用的DownloadError中
            raise DownloadError(real_error=e) from e

    async def _download_request(self, request: Request, spider) -> WebDriverResponse:
        """
        Internal method to perform the actual download using Playwright.
        使用Playwright执行实际下载的内部方法。

        This method configures and uses a Playwright browser to perform the request,
        handling cookies, user agent, proxies, and event listeners. It also supports
        custom browser actions defined in the spider.
        此方法配置并使用Playwright浏览器执行请求，处理Cookie、用户代理、代理和事件监听器。
        它还支持在爬虫中定义的自定义浏览器操作。

        Args:
            request: The request to download.
                    要下载的请求。
            spider: The spider that initiated the request.
                   发起请求的爬虫。

        Returns:
            PlaywrightResponse: The response from the browser.
                               来自浏览器的响应。

        Raises:
            Exception: If any error occurs during the browser automation.
                      如果在浏览器自动化过程中发生任何错误。
        """
        # Extract request parameters
        # 提取请求参数
        cookies = dict(request.cookies)
        timeout = request.meta.get('download_timeout', 30) * 1000  # Convert to milliseconds
        # 转换为毫秒
        user_agent = request.headers.get("User-Agent")
        proxy: str = request.meta.get("proxy")
        url = request.url

        # Dictionary to store responses from event listeners
        # 存储来自事件监听器的响应的字典
        cache_response = {}

        # Wrapper for event handlers to capture their return values
        # 包装事件处理程序以捕获其返回值
        # 为了获取监听事件中的响应结果
        def on_event_wrap_handler(func):
            @wraps(func)
            async def inner(response):
                ret = await func(response)
                if ret:
                    cache_response[ret[0]] = ret[1]

            return inner

        # Configure browser options
        # 配置浏览器选项
        kwargs = dict()
        if proxy:
            kwargs['proxy'] = proxy
        if user_agent:
            kwargs['user_agent'] = user_agent

        # Get a browser instance from the pool
        # 从池中获取浏览器实例
        driver: PlaywrightDriver = await self._webdriver_pool.get(**kwargs)

        # Set up event listeners from spider methods
        # 从爬虫方法设置事件监听器
        driver.page._events = dict()
        for name in dir(spider):
            if not name.startswith('on_event_'):
                continue
            driver.page.on(name.replace('on_event_', ''), on_event_wrap_handler(getattr(spider, name)))

        try:
            # Set cookies if provided
            # 如果提供了Cookie，则设置Cookie
            if cookies:
                driver.url = url
                await driver.set_cookies(cookies)

            # Navigate to the URL
            # 导航到URL
            await driver.page.goto(url, wait_until=request.meta.get('wait_until', self.wait_until), timeout=timeout)

            # Execute custom actions if defined in the spider
            # 如果在爬虫中定义了自定义操作，则执行
            if process_action_fn := getattr(spider, 'process_action', None):
                action_result = await call_helper(process_action_fn, driver, request)
                if action_result:
                    cache_response[action_result[0]] = action_result[1]

            # Process any event responses
            # 处理任何事件响应
            for cache_key in list(cache_response.keys()):
                if isinstance(cache_response[cache_key], EventResponse):
                    cache_ret = cache_response[cache_key]
                    # Convert Playwright response to PlaywrightResponse
                    # 将Playwright响应转换为PlaywrightResponse
                    cache_response[cache_key] = WebDriverResponse(url=cache_ret.url, request=request,
                        intercept_request=dict(url=cache_ret.request.url, headers=cache_ret.request.headers,
                            data=cache_ret.request.post_data, ), headers=cache_ret.headers, body=await cache_ret.body(),
                        status=cache_ret.status, )

            # Create and return the final response
            # 创建并返回最终响应
            return WebDriverResponse(url=driver.page.url, status=200, text=await driver.page.content(),
                cookies=await driver.get_cookies(), cache_response=cache_response, driver=driver,
                driver_pool=self._webdriver_pool)
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
