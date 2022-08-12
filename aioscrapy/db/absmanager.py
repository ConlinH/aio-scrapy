from abc import ABCMeta, abstractmethod

import aioscrapy


class AbsDBPoolManager(object, metaclass=ABCMeta):

    @property
    @abstractmethod
    def _clients(self) -> dict:
        return {}

    @abstractmethod
    async def create(self, alias: str, params: dict):
        """Create pool of connection"""

    @abstractmethod
    def get_pool(self, alias: str):
        """Get pool named `alias`"""

    @abstractmethod
    async def close_all(self):
        """Close all pool"""

    @abstractmethod
    async def close(self, alias: str):
        """Close pool named `alias`"""

    @abstractmethod
    async def from_dict(self, db_args: dict):
        """Create pool with dict"""

    @abstractmethod
    async def from_settings(self, settings: aioscrapy.Settings):
        """Create pool with settings"""

    async def from_crawler(self, crawler: "aioscrapy.Crawler"):
        return await self.from_settings(crawler.settings)

    def __call__(self, alias: str):
        return self.get_pool(alias)

    def __getitem__(self, alias: str):
        return self.get_pool(alias)

    def __getattr__(self, alias: str):
        return self.get_pool(alias)
