from scrapy.settings import Settings
from scrapy.settings import BaseSettings
from aioscrapy.settings import aio_settings


class AioSettings(Settings):
    
    def __init__(self, values=None, priority='project'):
        super().__init__()
        self.setmodule(aio_settings, 'default')

        for name, val in self.items():
            if isinstance(val, dict):
                self.set(name, BaseSettings(val, 'default'), 'default')
        self.update(values, priority)

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
