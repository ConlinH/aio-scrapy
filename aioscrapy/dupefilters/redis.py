import logging

from aioscrapy import Spider, Request
from aioscrapy.db import db_manager
from aioscrapy.dupefilters import DupeFilterBase

logger = logging.getLogger(__name__)


class RedisRFPDupeFilter(DupeFilterBase):
    """Request Fingerprint duplicates filter built with Set of Redis"""

    logger = logger

    def __init__(
            self,
            server: "redis.asyncio.Redis",
            key: str,
            debug: bool = False,
            keep_on_close: bool = True
    ):
        self.server = server
        self.key = key
        self.debug = debug
        self.keep_on_close = keep_on_close
        self.logdupes: bool = True

    @classmethod
    def from_crawler(cls, crawler: "aioscrapy.crawler.Crawler"):
        server = db_manager.redis.queue
        dupefilter_key = crawler.settings.get("SCHEDULER_DUPEFILTER_KEY", '%(spider)s:dupefilter')
        keep_on_close = crawler.settings.getbool("KEEP_DUPEFILTER_DATA_ON_CLOSE", True)
        key = dupefilter_key % {'spider': crawler.spider.name}
        debug = crawler.settings.getbool('DUPEFILTER_DEBUG', False)
        instance = cls(server, key=key, debug=debug, keep_on_close=keep_on_close)
        return instance

    async def request_seen(self, request: Request):
        return await self.server.sadd(self.key, request.fingerprint) == 0

    async def close(self, reason=''):
        if not self.keep_on_close:
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
        spider.crawler.stats.inc_value('dupefilter/filtered', spider=spider)


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
        async with self.server.pipeline(transaction=True) as pipe:
            for f in self.maps:
                offset = f.hash(value)
                pipe.getbit(self.key, offset)
            result = await pipe.execute()
        return any(result)

    async def insert(self, value):
        """
        add value to bloom
        :param value:
        :return:
        """
        async with self.server.pipeline(transaction=True) as pipe:
            for f in self.maps:
                offset = f.hash(value)
                pipe.setbit(self.key, offset, 1)
            await pipe.execute()


class RedisBloomDupeFilter(RedisRFPDupeFilter):
    """Bloom filter built with the bitis bitmap of redis"""

    def __init__(self, server, key, debug, bit, hash_number, keep_on_close):
        super().__init__(server, key, debug, keep_on_close)
        self.bit = bit
        self.hash_number = hash_number
        self.bf = BloomFilter(server, self.key, bit, hash_number)

    @classmethod
    async def from_crawler(cls, crawler: "aioscrapy.crawler.Crawler"):
        server = db_manager.redis.queue
        dupefilter_key = crawler.settings.get("SCHEDULER_DUPEFILTER_KEY", '%(spider)s:bloomfilter')
        keep_on_close = crawler.settings.getbool("KEEP_DUPEFILTER_DATA_ON_CLOSE", True)
        key = dupefilter_key % {'spider': crawler.spider.name}
        debug = crawler.settings.getbool('DUPEFILTER_DEBUG', False)
        bit = crawler.settings.getint('BLOOMFILTER_BIT', 30)
        hash_number = crawler.settings.getint('BLOOMFILTER_HASH_NUMBER', 6)
        return cls(server, key=key, debug=debug, bit=bit, hash_number=hash_number, keep_on_close=keep_on_close)

    async def request_seen(self, request: Request) -> bool:
        fp = await self.bf.exists(request.fingerprint)
        if fp:
            return True
        await self.bf.insert(request.fingerprint)
        return False


RFPDupeFilter = RedisRFPDupeFilter
BloomDupeFilter = RedisBloomDupeFilter
