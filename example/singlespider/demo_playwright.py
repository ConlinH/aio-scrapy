import logging

from aioscrapy import Request
from aioscrapy.spiders import Spider
from aioscrapy.http import PlaywrightResponse
from aioscrapy.core.downloader.handlers.playwright import PlaywrightDriver

logger = logging.getLogger(__name__)


class DemoPlaywrightSpider(Spider):
    name = 'DemoPlaywrightSpider'

    custom_settings = dict(
        USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        # DOWNLOAD_DELAY=3,
        # RANDOMIZE_DOWNLOAD_DELAY=True,
        CONCURRENT_REQUESTS=1,
        LOG_LEVEL='INFO',
        CLOSE_SPIDER_ON_IDLE=True,
        DOWNLOAD_HANDLERS={
            'http': 'aioscrapy.core.downloader.handlers.playwright.PlaywrightHandler',
            'https': 'aioscrapy.core.downloader.handlers.playwright.PlaywrightHandler',
        },
        PLAYWRIGHT_CLIENT_ARGS=dict(
            driver_type="chromium",  # chromium、firefox、webkit
            wait_until="networkidle",  # 等待页面加载完成的事件,可选值："commit", "domcontentloaded", "load", "networkidle"
            window_size=(1024, 800),
            # url_regexes=["xxxx"],
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
        # res = response.get_response("xxxx")
        # print(res.text[:100])

        img_bytes = response.get_response('action_result')
        yield {
            'pingyin': response.xpath('//div[@id="pinyin"]/span/b/text()').get(),
            'fan': response.xpath('//*[@id="traditional"]/span/text()').get(),
            'img': img_bytes,
        }

        new_character = response.xpath('//a[@class="img-link"]/@href').getall()
        for character in new_character:
            new_url = 'https://hanyu.baidu.com/zici' + character
            yield Request(new_url, callback=self.parse, dont_filter=True)

    async def process_action(self, driver: PlaywrightDriver):
        """ Do some operations after function page.goto """
        img_bytes = await driver.page.screenshot(type="jpeg", quality=50)
        return img_bytes

    async def process_item(self, item):
        print(item)


if __name__ == '__main__':
    DemoPlaywrightSpider.start()
