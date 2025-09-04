import random
from typing import Any

from aioscrapy import Request, logger, Spider
from aioscrapy.core.downloader.handlers.webdriver import SbcdpDriver
from sbcdp import NetHttp, NetWebsocket
from aioscrapy.http import WebDriverResponse


class DemoSbcdpSpider(Spider):
    name = 'DemoSbcdpSpider'

    custom_settings = dict(
        # DOWNLOAD_DELAY=3,
        # RANDOMIZE_DOWNLOAD_DELAY=True,
        CONCURRENT_REQUESTS=1,
        LOG_LEVEL='INFO',
        CLOSE_SPIDER_ON_IDLE=True,
        # DOWNLOAD_HANDLERS={
        #   'http': 'aioscrapy.core.downloader.handlers.webdriver.sbcdp.SbcdpDownloadHandler',
        #   'https': 'aioscrapy.core.downloader.handlers.webdriver.sbcdp.SbcdpDownloadHandler',
        # },
        DOWNLOAD_HANDLERS_TYPE="sbcdp",
        SBCDP_ARGS=dict(
            use_pool=True,  # use_pool=True时 使用完driver后不销毁 重复使用 提高效率
            max_uses=None,  # 在use_pool=True时生效，如果driver达到指定使用次数，则销毁，重新启动一个driver（处理有些driver使用次数变多则变卡的情况）
            # ... 其它参数为sbcdp的AsyncChrome类参数
        )
    )

    start_urls = [
        'https://hanyu.baidu.com/zici/s?wd=黄&query=黄',
        'https://hanyu.baidu.com/zici/s?wd=王&query=王',
        'https://hanyu.baidu.com/zici/s?wd=李&query=李',
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
            'title': response.get_response('title'),
            'event_ret': response.get_response('info_key'),
        }

    async def on_event_http(self, result: NetHttp) -> Any:
        """
        监听网络请求
        sbcdp的http_monitor_all_tabs方法中的monitor_cb参数
        具体使用参考sbcdp
        """
        # 如果事件中有需要传递回 parse函数的内容，则按如下返回，结果将在self.parse的response.cache_response中,
        if '/dictapp/word/detail_getworddetail' in result.url:
            return 'event_ret', await result.get_response_body()

        if 'xxx2' in result.url:
            return 'xxx2', {'data': 'aaa'}

    async def on_event_http_intercept(self, result: NetHttp) -> Any:
        """
        监听网络请求拦截
        sbcdp的http_monitor_all_tabs方法中的intercept_cb参数
        具体使用参考sbcdp
        """
        # 阻止图片的加载
        if result.resource_type == 'Image':
            return True

    async def process_action(self, driver: SbcdpDriver, request: Request) -> Any:
        """ Do some operations after function page.goto """
        title = await driver.browser.get_title()

        # TODO: 点击 选择元素等操作

        # 如果有需要传递回 parse函数的内容，则按如下返回，结果将在self.parse的response.cache_response中，
        return 'title', title

    async def process_item(self, item):
        logger.info(item)


if __name__ == '__main__':
    DemoSbcdpSpider.start()
