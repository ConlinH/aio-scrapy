from scrapy.settings import Settings
from scrapy.settings import BaseSettings


class AioSettings(Settings):

    def getwithbase(self, name):
        """Get a composition of a dictionary-like setting and its `_BASE`
        counterpart.

        :param name: name of the dictionary-like setting
        :type name: str
        """
        compbs = BaseSettings()
        compbs.update(self[name + '_BASE'])
        compbs.update(self[name])
        compbs.update(self[name + '_USER'])
        return compbs
