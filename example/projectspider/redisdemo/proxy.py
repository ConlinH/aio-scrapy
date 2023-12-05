from aioscrapy.proxy.redis import AbsProxy
from aioscrapy import logger


# TODO: 根据实际情况重写AbsProxy部分方法
class MyProxy(AbsProxy):
    def __init__(
            self,
            settings,
    ):
        super().__init__(settings)

    @classmethod
    async def from_crawler(cls, crawler) -> AbsProxy:
        settings = crawler.settings
        return cls(
            settings
        )

    async def get(self) -> str:
        # TODO: 实现ip逻辑
        logger.warning("未实现ip代理逻辑")
        return 'http://127.0.0.1:7890'
