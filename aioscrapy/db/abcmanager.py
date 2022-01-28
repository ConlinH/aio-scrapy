from abc import ABCMeta, abstractmethod


class ABCManager(object, metaclass=ABCMeta):

    @abstractmethod
    async def create(self, alias: str, params: dict):
        """创建连接池"""

    @abstractmethod
    def get_pool(self, alias: str):
        """获取指定连接池"""

    @abstractmethod
    async def close_all(self):
        """关闭所有连接池"""

    @abstractmethod
    async def close(self, alias: str):
        """关闭指定连接池"""

    @abstractmethod
    async def from_settings(self, settings: "scrapy.settings.Setting"):
        """更具setting实例化连接池管理类"""

    async def from_crawler(self, crawler):
        return await self.from_settings(crawler.settings)
