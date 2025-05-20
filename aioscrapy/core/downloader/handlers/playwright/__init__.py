"""
Download handler implementation using Playwright.
使用Playwright的下载处理程序实现。

This module provides a download handler that uses Playwright to perform browser-based HTTP requests.
It supports full browser automation, JavaScript execution, and event handling.
此模块提供了一个使用Playwright执行基于浏览器的HTTP请求的下载处理程序。
它支持完整的浏览器自动化、JavaScript执行和事件处理。
"""

from functools import wraps

try:
    from playwright._impl._errors import Error
except ImportError:
    from playwright._impl._api_types import Error

from playwright.async_api._generated import Response as EventResponse

from aioscrapy import Request, Spider
from aioscrapy.core.downloader.handlers import BaseDownloadHandler
from aioscrapy.core.downloader.handlers.playwright.driverpool import WebDriverPool
from aioscrapy.core.downloader.handlers.playwright.webdriver import PlaywrightDriver
from aioscrapy.exceptions import DownloadError
from aioscrapy.http import PlaywrightResponse
from aioscrapy.settings import Settings
from aioscrapy.utils.tools import call_helper


class PlaywrightHandler(BaseDownloadHandler):
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
        playwright_client_args = settings.getdict('PLAYWRIGHT_CLIENT_ARGS')

        # Set the default page load event to wait for
        # 设置要等待的默认页面加载事件
        self.wait_until = playwright_client_args.get('wait_until', 'domcontentloaded')

        # Configure the pool size for browser instances
        # 配置浏览器实例的池大小
        pool_size = playwright_client_args.pop('pool_size', settings.getint("CONCURRENT_REQUESTS", 1))

        # Initialize the WebDriver pool
        # 初始化WebDriver池
        self._webdriver_pool = WebDriverPool(pool_size=pool_size, driver_cls=PlaywrightDriver, **playwright_client_args)

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

    async def download_request(self, request: Request, spider: Spider) -> PlaywrightResponse:
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

    async def _download_request(self, request: Request, spider) -> PlaywrightResponse:
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
                    cache_response[cache_key] = PlaywrightResponse(
                        url=cache_ret.url,
                        request=request,
                        intercept_request=dict(
                            url=cache_ret.request.url,
                            headers=cache_ret.request.headers,
                            data=cache_ret.request.post_data,
                        ),
                        headers=cache_ret.headers,
                        body=await cache_ret.body(),
                        status=cache_ret.status,
                    )

            # Create and return the final response
            # 创建并返回最终响应
            return PlaywrightResponse(
                url=driver.page.url,
                status=200,
                text=await driver.page.content(),
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
