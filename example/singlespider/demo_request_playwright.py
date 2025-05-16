import random
from typing import Any

from playwright.async_api._generated import Response as EventResponse
from playwright.async_api._generated import Request as EventRequest

from aioscrapy import Request, logger, Spider
from aioscrapy.core.downloader.handlers.playwright import PlaywrightDriver
from aioscrapy.http import PlaywrightResponse


class DemoPlaywrightSpider(Spider):
    name = 'DemoPlaywrightSpider'

    custom_settings = dict(
        USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        # DOWNLOAD_DELAY=3,
        # RANDOMIZE_DOWNLOAD_DELAY=True,
        CONCURRENT_REQUESTS=1,
        LOG_LEVEL='INFO',
        CLOSE_SPIDER_ON_IDLE=True,
        # DOWNLOAD_HANDLERS={
        #     'http': 'aioscrapy.core.downloader.handlers.playwright.PlaywrightHandler',
        #     'https': 'aioscrapy.core.downloader.handlers.playwright.PlaywrightHandler',
        # },
        DOWNLOAD_HANDLERS_TYPE="playwright",
        PLAYWRIGHT_CLIENT_ARGS=dict(
            use_pool=True,  # use_pool=True时 使用完driver后不销毁 重复使用 提供效率
            destroy_after_uses_cnt=None,  # 在use_pool=True时生效，如果driver达到指定使用次数，则销毁，重新启动一个driver（处理有些driver使用次数变多则变卡的情况）
            driver_type="chromium",  # chromium、firefox、webkit
            wait_until="networkidle",  # 等待页面加载完成的事件,可选值："commit", "domcontentloaded", "load", "networkidle"
            window_size=(1024, 800),
            # proxy='http://user:pwd@127.0.0.1:7890',
            browser_args=dict(
                executable_path=None, channel=None, args=None, ignore_default_args=None, handle_sigint=None,
                handle_sigterm=None, handle_sighup=None, timeout=None, env=None, headless=False, devtools=None,
                downloads_path=None, slow_mo=None, traces_dir=None, chromium_sandbox=None,
                firefox_user_prefs=None,
            ),
            context_args=dict(
                no_viewport=None, ignore_https_errors=None, java_script_enabled=None,
                bypass_csp=None, user_agent=None, locale=None, timezone_id=None, geolocation=None, permissions=None,
                extra_http_headers=None, offline=None, http_credentials=None, device_scale_factor=None,
                is_mobile=None, has_touch=None, color_scheme=None, reduced_motion=None, forced_colors=None,
                accept_downloads=None, default_browser_type=None, record_har_path=None,
                record_har_omit_content=None, record_video_dir=None, record_video_size=None, storage_state=None,
                base_url=None, strict_selectors=None, service_workers=None, record_har_url_filter=None,
                record_har_mode=None, record_har_content=None,
            ),
        )

    )

    start_urls = ['https://hanyu.baidu.com/zici/s?wd=黄&query=黄']
    # start_urls = ["https://mall.jd.com/view_search-507915-3733265-99-1-24-1.html"]

    @staticmethod
    async def process_request(request, spider):
        """ request middleware """
        pass

    @staticmethod
    async def process_response(request, response, spider):
        """ response middleware """
        return response

    @staticmethod
    async def process_exception(request, exception, spider):
        """ exception middleware """
        pass

    async def parse(self, response: PlaywrightResponse):
        # # res = response.get_response("xxxx")
        # # print(res.text[:100])
        # print(response.cache_response)
        # res: PlaywrightResponse = response.get_response('getModuleHtml_response')
        # print(res.text)

        img_bytes = response.get_response('action_result')
        yield {
            'pingyin': response.xpath('//div[@id="pinyin"]/span/b/text()').get(),
            'fan': response.xpath('//*[@id="traditional"]/span/text()').get(),
            'img_bytes': img_bytes,
        }

        new_character = response.xpath('//a[@class="img-link"]/@href').getall()
        for character in new_character:
            new_url = 'https://hanyu.baidu.com/zici' + character
            yield Request(new_url, callback=self.parse, dont_filter=True)

    async def on_event_request(self, result: EventRequest) -> Any:
        """
        具体使用参考playwright的page.on('request', lambda req: print(req))
        """
        # print(result)

    async def on_event_response(self, result: EventResponse) -> Any:
        """
        具体使用参考playwright的page.on('response', lambda res: print(res))
        """

        # 如果事件中有需要传递回 parse函数的内容，则按如下返回，结果将在self.parse的response.cache_response中,

        if 'getModuleHtml' in result.url:
            return 'getModuleHtml_response', result

        if 'xxx1' in result.url:
            return 'xxx_response', await result.text()

        if 'xxx2' in result.url:
            return 'xxx2', {'data': 'aaa'}

    async def process_action(self, driver: PlaywrightDriver, request: Request) -> Any:
        """ Do some operations after function page.goto """
        # img_bytes = await driver.page.screenshot(type="jpeg", quality=50)

        # TODO: 点击 选择元素等操作

        # 如果有需要传递回 parse函数的内容，则按如下返回，结果将在self.parse的response.cache_response中，
        # return 'img_bytes', img_bytes

    async def process_item(self, item):
        logger.info(item)


if __name__ == '__main__':
    DemoPlaywrightSpider.start()
