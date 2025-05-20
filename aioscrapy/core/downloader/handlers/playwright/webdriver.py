# -*- coding: utf-8 -*-
"""
Playwright WebDriver implementation for browser automation.
用于浏览器自动化的Playwright WebDriver实现。

This module provides a wrapper around Playwright's browser automation API,
making it easier to use within the aioscrapy framework. It handles browser
initialization, proxy configuration, and cookie management.
此模块提供了对Playwright浏览器自动化API的包装，使其更容易在aioscrapy框架中使用。
它处理浏览器初始化、代理配置和Cookie管理。
"""

import os
from typing import Dict, Optional, Tuple

try:
    from typing import Literal  # python >= 3.8
except ImportError:  # python <3.8
    from typing_extensions import Literal

from urllib.parse import urlparse, urlunparse

from playwright.async_api import Page, BrowserContext, ViewportSize, ProxySettings
from playwright.async_api import Playwright, Browser
from playwright.async_api import async_playwright


class PlaywrightDriver:
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
            destroy_after_uses_cnt: Optional[int] = None,
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
            destroy_after_uses_cnt: Optional count of uses after which the browser should be recycled.
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
        self.destroy_after_uses_cnt = destroy_after_uses_cnt  # Counter for browser recycling
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
