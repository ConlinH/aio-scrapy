import logging

from aioscrapy import Request
from aioscrapy.core.downloader.handlers import BaseDownloadHandler
from aioscrapy.http import PlaywrightResponse
from aioscrapy.settings import Settings
from .driverpool import WebDriverPool
from .webdriver import PlaywrightDriver

logger = logging.getLogger(__name__)


class PlaywrightHandler(BaseDownloadHandler):
    def __init__(self, settings: Settings):
        self.settings = settings
        playwright_client_args = settings.getdict('PLAYWRIGHT_CLIENT_ARGS')
        self.url_regexes = playwright_client_args.pop('url_regexes', [])
        pool_size = playwright_client_args.pop('pool_size', settings.getint("CONCURRENT_REQUESTS", 1))
        self._webdriver_pool = WebDriverPool(pool_size=pool_size, driver_cls=PlaywrightDriver, **playwright_client_args)

    @classmethod
    def from_settings(cls, settings: Settings):
        return cls(settings)

    async def download_request(self, request: Request, spider) -> PlaywrightResponse:
        cookies = dict(request.cookies)
        timeout = request.meta.get('download_timeout', 5) * 1000
        user_agent = (request.headers or self.settings.get('DEFAULT_REQUEST_HEADERS')).get("User-agent")
        proxy: str = request.meta.get("proxy")
        url = request.url

        driver: PlaywrightDriver = await self._webdriver_pool.get(
            user_agent=user_agent,
            proxy=proxy,
            timeout=timeout,
            on_event={
                name.replace('on_event', ''): getattr(spider, name) for name in dir(spider) if name.startswith('on_event')
            },
        )
        try:
            if cookies:
                driver.url = url
                await driver.set_cookies(cookies)
            await driver.page.goto(url, wait_until=request.meta.get('wait_until', "networkidle"))
            cache_response = {}
            for url_regex in self.url_regexes:
                async with driver.page.expect_response(url_regex, timeout=int(timeout/len(self.url_regexes))) as result:
                    res = await result.value
                    cache_response[url_regex] = PlaywrightResponse(
                        url=res.url,
                        request=request,
                        intercept_request=dict(
                            url=res.request.url,
                            headers=res.request.headers,
                            data=res.request.post_data,
                        ),
                        headers=res.headers,
                        body=await res.body(),
                        status=res.status,
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
