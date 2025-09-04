"""
Download handler implementation using Playwright.
使用Playwright的下载处理程序实现。

This module provides a download handler that uses Playwright to perform browser-based HTTP requests.
It supports full browser automation, JavaScript execution, and event handling.
此模块提供了一个使用Playwright执行基于浏览器的HTTP请求的下载处理程序。
它支持完整的浏览器自动化、JavaScript执行和事件处理。
"""
from functools import wraps
from typing import Optional, Literal

from sbcdp import AsyncChrome, NetHttp

from aioscrapy import Request, Spider
from aioscrapy.core.downloader.handlers import BaseDownloadHandler
from aioscrapy.exceptions import DownloadError
from aioscrapy.http import WebDriverResponse
from aioscrapy.settings import Settings
from aioscrapy.utils.tools import call_helper
from .driverpool import WebDriverPool, WebDriverBase


class SbcdpDriver(WebDriverBase):
    """
    A wrapper around sbcdp's browser automation API.
    对sbcdp浏览器自动化API的包装。

    This class provides a simplified interface for working with sbcdp browsers,
    handling initialization, proxy configuration, and browser lifecycle management.
    此类提供了一个简化的接口来使用sbcdp浏览器，处理初始化、代理配置和浏览器生命周期管理。
    """

    def __init__(
            self,
            *,
            driver_type: Literal["google-chrome", "edge"] = "google-chrome",
            proxy: Optional[str] = None,
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
        self.proxy = proxy # Formatted proxy settings
                            # 代理设置
        self.user_agent = user_agent  # User agent string
                                     # 用户代理字符串

        # sbcdp components (initialized in setup())
        # sbcdp组件（在setup()中初始化）
        self.browser: Optional[AsyncChrome] = None  # sbcdp instance
                                                 # sbcdp实例
        self.url = None  # Current URL (used for cookie management)
                        # 当前URL（用于Cookie管理）
        self.max_uses = max_uses  # Counter for browser recycling
                                  # 浏览器回收计数器

        self.had_set_event_http = False
        self.cache_response = None

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
        # Start Playwright and launch browser
        # 启动Playwright和浏览器
        self.browser = AsyncChrome(url=self.url, user_agent=self.user_agent, proxy=self.proxy)
        await self.browser.start()


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
        self.cache_response = None
        await self.browser.stop()

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
            cookie.name: cookie.value
            for cookie in await self.browser.get_all_cookies()
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
        # Convert the dictionary to the format expected by sbcdp
        # 将字典转换为sbcdp期望的格式
        u = self.url or await self.browser.get_origin()
        await self.browser.set_all_cookies([
            {
                "name": key,
                "value": value,
                # Use the stored URL or current page URL
                # 使用存储的URL或当前页面URL
                "url": u
            }
            for key, value in cookies.items()
        ])


class SbcdpDownloadHandler(BaseDownloadHandler):
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
        sbcdp_client_args = settings.getdict('SBCDP_ARGS')

        # Configure the pool size for browser instances
        # 配置浏览器实例的池大小
        pool_size = sbcdp_client_args.pop('pool_size', settings.getint("CONCURRENT_REQUESTS", 1))

        # Initialize the WebDriver pool
        # 初始化WebDriver池
        self._webdriver_pool = WebDriverPool(SbcdpDriver, pool_size=pool_size,  **sbcdp_client_args)

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
        # except Error as e:
        #     # Wrap Playwright-specific exceptions in a generic DownloadError
        #     # 将Playwright特定的异常包装在通用的DownloadError中
        #     raise DownloadError(real_error=e) from e
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

        # Configure browser options
        # 配置浏览器选项
        kwargs = dict()
        if proxy:
            kwargs['proxy'] = proxy
        if user_agent:
            kwargs['user_agent'] = user_agent

        # Get a browser instance from the pool
        # 从池中获取浏览器实例
        driver: SbcdpDriver = await self._webdriver_pool.get(**kwargs)

        # Dictionary to store responses from event listeners
        # 存储来自事件监听器的响应的字典
        driver.cache_response = {}

        # Wrapper for event handlers to capture their return values
        # 包装事件处理程序以捕获其返回值
        # 为了获取监听事件中的响应结果
        def on_event_wrap_handler(func):
            @wraps(func)
            async def inner(*a, **kw):
                ret = await func(*a, **kw)
                if ret:
                    driver.cache_response[ret[0]] = ret[1]

            return inner

        # Set up event listeners from spider methods
        # 从爬虫方法设置事件监听器
        if (not driver.had_set_event_http) and (monitor_cb:=getattr(spider, "on_event_http", None)):
            intercept_cb = getattr(spider, "on_event_http_intercept", None)
            driver.browser.http_monitor(
                monitor_cb=on_event_wrap_handler(monitor_cb),
                intercept_cb=intercept_cb,
                delay_response_body=True
            )
            driver.had_set_event_http = True

        try:
            # Set cookies if provided
            # 如果提供了Cookie，则设置Cookie
            if cookies:
                driver.url = url
                await driver.set_cookies(cookies)

            # Navigate to the URL
            # 导航到URL
            await driver.browser.get(url, timeout=timeout)

            # Execute custom actions if defined in the spider
            # 如果在爬虫中定义了自定义操作，则执行
            if process_action_fn := getattr(spider, 'process_action', None):
                action_result = await call_helper(process_action_fn, driver, request)
                if action_result:
                    driver.cache_response[action_result[0]] = action_result[1]

            # Process any event responses
            # 处理任何事件响应
            for cache_key in list(driver.cache_response.keys()):
                if isinstance(driver.cache_response[cache_key], NetHttp):
                    cache_ret = driver.cache_response[cache_key]
                    # Convert sbcdp response to WebDriverResponse
                    # 将sbcdp响应转换为WebDriverResponse
                    driver.cache_response[cache_key] = WebDriverResponse(
                        url=cache_ret.url,
                        request=request,
                        intercept_request=dict(
                            url=cache_ret.request.url,
                            headers=cache_ret.request.headers,
                            data=cache_ret.request.post_data,
                        ),
                        headers=cache_ret.headers,
                        body=(await cache_ret.get_response_body()).encode(),
                        status=200,
                    )

            # Create and return the final response
            # 创建并返回最终响应
            return WebDriverResponse(
                url=await driver.browser.get_current_url(),
                status=200,
                text=await driver.browser.get_page_source(),
                cookies=await driver.get_cookies(),
                cache_response=driver.cache_response,
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
