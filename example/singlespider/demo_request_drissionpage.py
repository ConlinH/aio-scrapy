import time
from typing import Any

from watchdog.watchmedo import argument

from aioscrapy import Request, logger, Spider
from aioscrapy.core.downloader.handlers.webdriver import DrissionPageDriver
from aioscrapy.http import WebDriverResponse


class DemoPlaywrightSpider(Spider):
    name = 'DemoPlaywrightSpider'

    custom_settings = dict(
        USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        # DOWNLOAD_DELAY=3,
        # RANDOMIZE_DOWNLOAD_DELAY=True,
        CONCURRENT_REQUESTS=2,
        LOG_LEVEL='INFO',
        CLOSE_SPIDER_ON_IDLE=True,
        # DOWNLOAD_HANDLERS={
        #     'http': 'aioscrapy.core.downloader.handlers.webdriver.drissionpage.DrissionPageHandler',
        #     'https': 'aioscrapy.core.downloader.handlers.webdriver.drissionpage.DrissionPageHandler',
        # },
        DOWNLOAD_HANDLERS_TYPE="dp",
        DP_CLIENT_ARGS=dict(
            use_pool=True,  # use_pool=True时 使用完driver后不销毁 重复使用 提供效率
            max_uses=None,  # 在use_pool=True时生效，如果driver达到指定使用次数，则销毁，重新启动一个driver（处理有些driver使用次数变多则变卡的情况）
            headless=False,
            arguments=['--no-sandbox', ('--window-size', '1024,800')]
        )

    )

    start_urls = [
        'https://hanyu.baidu.com/zici/s?wd=黄&query=黄',
    ]

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

    async def parse(self, response: WebDriverResponse):
        yield {
            'pingyin': response.xpath('//div[@class="pinyin-text"]/text()').get(),
            'action_ret': response.get_response('action_ret'),
        }

    def process_action(self, driver: DrissionPageDriver, request: Request) -> Any:
        """
        该方法在异步线程中执行，不要使用异步函数
        """
        img_bytes = driver.page.get_screenshot(as_bytes='jpeg')
        print(img_bytes)

        time.sleep(2)   # 等待js渲染

        # TODO: 点击 选择元素等操作

        # 如果有需要传递回 parse函数的内容，则按如下返回，结果将在self.parse的response.cache_response中，
        return 'action_ret', 'process_action result'

    async def process_item(self, item):
        logger.info(item)


if __name__ == '__main__':
    DemoPlaywrightSpider.start()
