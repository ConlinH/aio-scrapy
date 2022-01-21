
class IManager:

    async def create(self, *args, **kwargs):
        raise NotImplementedError

    def get_pool(self, alias: str):
        raise NotImplementedError

    async def close_all(self, *args, **kwargs):
        raise NotImplementedError

    async def close(self, *args, **kwargs):
        raise NotImplementedError

    async def from_settings(self, settings: "scrapy.settings.Setting"):
        raise NotImplementedError

    async def from_crawler(self, crawler):
        return await self.from_settings(crawler.settings)
