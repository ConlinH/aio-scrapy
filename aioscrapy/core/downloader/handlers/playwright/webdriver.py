# -*- coding: utf-8 -*-

import os
from typing import Dict, Optional, Tuple, Callable

try:
    from typing import Literal  # python >= 3.8
except ImportError:  # python <3.8
    from typing_extensions import Literal

from urllib.parse import urlparse, urlunparse

from playwright.async_api import Page, BrowserContext, ViewportSize, ProxySettings
from playwright.async_api import Playwright, Browser
from playwright.async_api import async_playwright


class PlaywrightDriver:
    def __init__(
            self,
            *,
            driver_type: Literal["chromium", "firefox", "webkit"] = "chromium",
            proxy: Optional[str] = None,
            browser_args: Optional[Dict] = None,
            context_args: Optional[Dict] = None,
            on_event: Optional[Dict] = None,
            on_response: Optional[Callable] = None,
            window_size: Optional[Tuple[int, int]] = None,
            timout: int = 30 * 1000,
            user_agent: str = None,
            **kwargs
    ):

        self.driver_type = driver_type
        self.proxy = proxy and self.format_context_proxy(proxy)
        self.viewport = window_size and ViewportSize(width=window_size[0], height=window_size[1])
        self.browser_args = browser_args or {}
        self.context_args = context_args or {}
        self.on_event = on_event
        self.on_response = on_response
        self.user_agent = user_agent

        self.driver: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.url = None

    async def setup(self):
        browser_args = self.browser_args.copy()
        context_args = self.context_args.copy()
        if browser_args.get('args') is None:
            browser_args.update({'args': ["--no-sandbox"]})

        if context_args.get("storage_state") is not None:
            storage_state_path = context_args.get("storage_state")
            os.makedirs(os.path.dirname(storage_state_path), exist_ok=True)

        if self.proxy:
            browser_args.update({'proxy': self.proxy})
            context_args.update({'proxy': self.proxy})
        if self.viewport:
            context_args.update({"viewport": self.viewport})
            context_args.update({"screen": self.viewport})
        if self.user_agent:
            context_args.update({'user_agent': self.user_agent})

        self.driver = await async_playwright().start()
        self.browser = await getattr(self.driver, self.driver_type).launch(**browser_args)
        self.context = await self.browser.new_context(**context_args)
        self.page = await self.context.new_page()

        for event, callback in self.on_event.items():
            self.page.on(event, callback)
        self.on_response and self.page.on("response", self.on_response)

    @staticmethod
    def format_context_proxy(proxy) -> ProxySettings:
        parsed_url = urlparse(proxy)
        return ProxySettings(
            server=urlunparse(parsed_url._replace(netloc=parsed_url.netloc.split('@')[-1])),
            username=parsed_url.username,
            password=parsed_url.password,
        )

    async def quit(self):
        await self.page.close()
        try:
            await self.context.close()
        except:
            pass
        finally:
            await self.browser.close()
            await self.driver.stop()

    async def get_cookies(self):
        return {
            cookie["name"]: cookie["value"]
            for cookie in await self.page.context.cookies()
        }

    async def set_cookies(self, cookies: dict):
        await self.page.context.add_cookies([
            {"name": key, "value": value, "url": self.url or self.page.url} for key, value in cookies.items()
        ])
