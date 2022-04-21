import logging
import time

from scrapy.dupefilters import BaseDupeFilter
from scrapy.utils.request import request_fingerprint

from aioscrapy.db import get_pool


logger = logging.getLogger(__name__)


class RFPDupeFilter(BaseDupeFilter):
    """ 使用redis集合构建的过滤器"""

    logger = logger

    def __init__(self, server, key, debug=False):
        self.server = server
        self.key = key
        self.debug = debug
        self.logdupes = True

    @classmethod
    async def from_spider(cls, spider):
        settings = spider.settings
        server = await get_pool('redis')
        dupefilter_key = settings.get("SCHEDULER_DUPEFILTER_KEY",  '%(spider)s:bloomfilter')
        key = dupefilter_key % {'spider': spider.name}
        debug = settings.getbool('DUPEFILTER_DEBUG', False)
        instance = cls(server, key=key, debug=debug)
        return instance

    @classmethod
    async def from_settings(cls, settings):
        server = await get_pool('redis')
        key = settings['DUPEFILTER_KEY'] % {'timestamp': int(time.time())}
        debug = settings.getbool('DUPEFILTER_DEBUG')
        return cls(server, key=key, debug=debug)

    @classmethod
    async def from_crawler(cls, crawler):
        return await cls.from_settings(crawler.settings)

    async def request_seen(self, request):
        fp = self.request_fingerprint(request)
        return await self.server.sadd(self.key, fp) == 0

    def request_fingerprint(self, request):
        return request_fingerprint(request)

    async def close(self, reason=''):
        await self.clear()

    async def clear(self):
        await self.server.delete(self.key)

    def log(self, request, spider):
        if self.debug:
            msg = "Filtered duplicate request: %(request)s"
            self.logger.debug(msg, {'request': request}, extra={'spider': spider})
        elif self.logdupes:
            msg = ("Filtered duplicate request %(request)s"
                   " - no more duplicates will be shown"
                   " (see DUPEFILTER_DEBUG to show all duplicates)")
            self.logger.debug(msg, {'request': request}, extra={'spider': spider})
            self.logdupes = False


class HashMap(object):
    def __init__(self, m, seed):
        self.m = m
        self.seed = seed

    def hash(self, value):
        """
        Hash Algorithm
        :param value: Value
        :return: Hash Value
        """
        ret = 0
        for i in range(len(value)):
            ret += self.seed * ret + ord(value[i])
        return (self.m - 1) & ret


class BloomFilter(object):
    def __init__(self, server, key, bit=30, hash_number=6):
        """
        Initialize BloomFilter
        :param server: Redis Server
        :param key: BloomFilter Key
        :param bit: m = 2 ^ bit
        :param hash_number: the number of hash function
        """
        # default to 1 << 30 = 10,7374,1824 = 2^30 = 128MB, max filter 2^30/hash_number = 1,7895,6970 fingerprints
        self.m = 1 << bit
        self.seeds = range(hash_number)
        self.server = server
        self.key = key
        self.maps = [HashMap(self.m, seed) for seed in self.seeds]

    async def exists(self, value):
        if not value:
            return False
        exist = True
        for map_ in self.maps:
            offset = map_.hash(value)
            exist = exist & await self.server.getbit(self.key, offset)
            if not exist:
                return False
        return exist

    async def insert(self, value):
        """
        add value to bloom
        :param value:
        :return:
        """
        for f in self.maps:
            offset = f.hash(value)
            await self.server.setbit(self.key, offset, 1)


class BloomDupeFilter(RFPDupeFilter):
    """ 使用redis的位图构建的布隆过滤器 """

    def __init__(self, server, key, debug, bit, hash_number):
        super().__init__(server, key, debug)
        self.bit = bit
        self.hash_number = hash_number
        self.bf = BloomFilter(server, self.key, bit, hash_number)

    @classmethod
    async def from_settings(cls, settings):
        server = await get_pool('redis')

        key = settings.get('DUPEFILTER_KEY', 'dupefilter:%(timestamp)s') % {'timestamp': int(time.time())}
        debug = settings.getbool('DUPEFILTER_DEBUG')
        bit = settings.getint('BLOOMFILTER_BIT', 30)
        hash_number = settings.getint('BLOOMFILTER_HASH_NUMBER', 6)
        return cls(server, key=key, debug=debug, bit=bit, hash_number=hash_number)

    @classmethod
    async def from_spider(cls, spider):
        settings = spider.settings
        server = await get_pool('redis')
        dupefilter_key = settings.get("SCHEDULER_DUPEFILTER_KEY",  '%(spider)s:bloomfilter')
        key = dupefilter_key % {'spider': spider.name}
        debug = settings.getbool('DUPEFILTER_DEBUG', False)
        bit = settings.getint('BLOOMFILTER_BIT', 30)
        hash_number = settings.getint('BLOOMFILTER_HASH_NUMBER', 6)
        return cls(server, key=key, debug=debug, bit=bit, hash_number=hash_number)

    async def request_seen(self, request):
        fp = self.request_fingerprint(request)
        if await self.bf.exists(fp):
            return True
        await self.bf.insert(fp)
        return False

    def log(self, request, spider):
        super().log(request, spider)
        spider.crawler.stats.inc_value('bloomfilter/filtered', spider=spider)
