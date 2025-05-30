
from aioscrapy import Request, logger, Spider
from aioscrapy.http import Response


class DemoPyhttpxSpider(Spider):
    name = 'DemoPyhttpxSpider'

    custom_settings = dict(
        USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        # DOWNLOAD_DELAY=3,
        # RANDOMIZE_DOWNLOAD_DELAY=True,
        CONCURRENT_REQUESTS=1,
        LOG_LEVEL='INFO',
        CLOSE_SPIDER_ON_IDLE=True,
        # DOWNLOAD_HANDLERS={
        #     'http': 'aioscrapy.core.downloader.handlers.pyhttpx.PyhttpxDownloadHandler',
        #     'https': 'aioscrapy.core.downloader.handlers.pyhttpx.PyhttpxDownloadHandler',
        # },
        DOWNLOAD_HANDLERS_TYPE="pyhttpx",
        PYHTTPX_ARGS={}      # 传递给pyhttpx.HttpSession构造函数的参数
    )

    start_urls = ['https://tls.peet.ws/api/all']

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

    async def parse(self, response: Response):
        print(response.text)

    async def process_item(self, item):
        logger.info(item)


if __name__ == '__main__':
    DemoPyhttpxSpider.start()
