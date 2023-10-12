from functools import wraps

from playwright.async_api._generated import Response as EventResponse

from aioscrapy import Request
from aioscrapy.core.downloader.handlers import BaseDownloadHandler
from aioscrapy.core.downloader.handlers.playwright.driverpool import WebDriverPool
from aioscrapy.core.downloader.handlers.playwright.webdriver import PlaywrightDriver
from aioscrapy.http import PlaywrightResponse
from aioscrapy.settings import Settings
from aioscrapy.utils.tools import call_helper


class PlaywrightHandler(BaseDownloadHandler):
    def __init__(self, settings: Settings):
        self.settings = settings
        playwright_client_args = settings.getdict('PLAYWRIGHT_CLIENT_ARGS')
        self.wait_until = playwright_client_args.get('wait_until', 'domcontentloaded')
        self.url_regexes = playwright_client_args.pop('url_regexes', [])
        pool_size = playwright_client_args.pop('pool_size', settings.getint("CONCURRENT_REQUESTS", 1))
        self._webdriver_pool = WebDriverPool(pool_size=pool_size, driver_cls=PlaywrightDriver, **playwright_client_args)

    @classmethod
    def from_settings(cls, settings: Settings):
        return cls(settings)

    async def download_request(self, request: Request, spider) -> PlaywrightResponse:
        cookies = dict(request.cookies)
        timeout = request.meta.get('download_timeout', 30) * 1000
        user_agent = request.headers.get("User-Agent")
        proxy: str = request.meta.get("proxy")
        url = request.url

        cache_response = {}

        # 为了获取监听事件中的响应结果
        def on_event_wrap_handler(func):
            @wraps(func)
            async def inner(response):
                ret = await func(response)
                if ret:
                    cache_response[ret[0]] = ret[1]

            return inner

        kwargs = dict()
        if proxy:
            kwargs['proxy'] = proxy
        if user_agent:
            kwargs['user_agent'] = user_agent

        driver: PlaywrightDriver = await self._webdriver_pool.get(**kwargs)

        # 移除所有的事件监听事件后 重新添加
        driver.page._events = dict()
        for name in dir(spider):
            if not name.startswith('on_event_'):
                continue
            driver.page.on(name.replace('on_event_', ''), on_event_wrap_handler(getattr(spider, name)))

        try:
            if cookies:
                driver.url = url
                await driver.set_cookies(cookies)
            await driver.page.goto(url, wait_until=request.meta.get('wait_until', self.wait_until), timeout=timeout)

            if process_action_fn := getattr(spider, 'process_action', None):
                action_result = await call_helper(process_action_fn, driver)
                if action_result:
                    cache_response[action_result[0]] = action_result[1]

            for cache_key in list(cache_response.keys()):
                if isinstance(cache_response[cache_key], EventResponse):
                    cache_ret = cache_response[cache_key]
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
            await self._webdriver_pool.remove(driver)
            raise e

    async def close(self):
        await self._webdriver_pool.close()
