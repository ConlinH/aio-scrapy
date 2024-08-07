from typing import Literal

from aioscrapy import Request
from aioscrapy.db import db_manager
from aioscrapy.dupefilters import DupeFilterBase


class RedisRFPDupeFilter(DupeFilterBase):
    """Request Fingerprint duplicates filter built with Set of Redis"""

    def __init__(
            self,
            server: "redis.asyncio.Redis",
            key: str,
            debug: bool = False,
            keep_on_close: bool = True,
            info: bool = False,
    ):
        self.server = server
        self.key = key
        self.debug = debug
        self.keep_on_close = keep_on_close
        self.logdupes: bool = True
        self.info: bool = info

    @classmethod
    def from_crawler(cls, crawler: "aioscrapy.crawler.Crawler"):
        server = db_manager.redis.queue
        dupefilter_key = crawler.settings.get("SCHEDULER_DUPEFILTER_KEY", '%(spider)s:dupefilter')
        keep_on_close = crawler.settings.getbool("KEEP_DUPEFILTER_DATA_ON_CLOSE", True)
        key = dupefilter_key % {'spider': crawler.spider.name}
        debug = crawler.settings.getbool('DUPEFILTER_DEBUG', False)
        info = crawler.settings.getbool('DUPEFILTER_INFO', False)
        instance = cls(server, key=key, debug=debug, keep_on_close=keep_on_close, info=info)
        return instance

    async def request_seen(self, request: Request):
        return await self.server.sadd(self.key, request.fingerprint) == 0

    async def close(self, reason=''):
        if not self.keep_on_close:
            await self.clear()

    async def clear(self):
        await self.server.delete(self.key)


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
        return all(result)

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

    def __init__(self, server, key, debug, bit, hash_number, keep_on_close, info):
        super().__init__(server, key, debug, keep_on_close, info)
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
        info = crawler.settings.getbool('DUPEFILTER_INFO', False)
        bit = crawler.settings.getint('BLOOMFILTER_BIT', 30)
        hash_number = crawler.settings.getint('BLOOMFILTER_HASH_NUMBER', 6)
        return cls(server, key=key, debug=debug, bit=bit, hash_number=hash_number, keep_on_close=keep_on_close, info=info)

    async def request_seen(self, request: Request) -> bool:
        fp = await self.bf.exists(request.fingerprint)
        if fp:
            return True
        await self.bf.insert(request.fingerprint)
        return False


class ExRedisBloomDupeFilter(RedisBloomDupeFilter):

    def __init__(self, server, key, key_set, ttl, debug, bit, hash_number, keep_on_close, info):
        super().__init__(server, key, debug, bit, hash_number, keep_on_close, info)
        self.key_set = key_set
        self.ttl = ttl

    @classmethod
    async def from_crawler(cls, crawler: "aioscrapy.crawler.Crawler"):
        server = db_manager.redis.queue
        dupefilter_key = crawler.settings.get("SCHEDULER_DUPEFILTER_KEY", '%(spider)s:bloomfilter')
        keep_on_close = crawler.settings.getbool("KEEP_DUPEFILTER_DATA_ON_CLOSE", True)
        key = dupefilter_key % {'spider': crawler.spider.name}
        debug = crawler.settings.getbool('DUPEFILTER_DEBUG', False)
        info = crawler.settings.getbool('DUPEFILTER_INFO', False)
        bit = crawler.settings.getint('BLOOMFILTER_BIT', 30)
        hash_number = crawler.settings.getint('BLOOMFILTER_HASH_NUMBER', 6)
        ttl = crawler.settings.getint('DUPEFILTER_SET_KEY_TTL', 180)
        return cls(server, key=key, key_set=key + "_set", ttl=ttl, debug=debug, bit=bit, hash_number=hash_number,
                   keep_on_close=keep_on_close, info=info)

    async def request_seen(self, request: Request) -> bool:
        fp = await self.bf.exists(request.fingerprint)
        if fp:
            return True
        async with self.server.pipeline() as pipe:
            pipe.sadd(self.key_set, request.fingerprint)
            pipe.expire(self.key_set, self.ttl)
            ret, _ = await pipe.execute()
        return ret == 0

    async def done(
            self,
            request: Request,
            done_type: Literal["request_ok", "request_err", "parse_ok", "parse_err"]
    ):
        if done_type == "request_ok" or done_type == "request_err":
            await self.server.srem(self.key_set, request.fingerprint)
        elif done_type == "parse_ok":
            await self.bf.insert(request.fingerprint)

    async def close(self, reason=''):
        if not self.keep_on_close:
            await self.clear()
        await self.server.delete(self.key_set)


class ExRedisRFPDupeFilter(RedisRFPDupeFilter):

    async def done(
            self,
            request: Request,
            done_type: Literal["request_ok", "request_err", "parse_ok", "parse_err"]
    ):
        # 当请求失败或解析失败的时候 从Redis的Set中移除指纹
        if done_type == "request_err" or done_type == "parse_err":
            await self.server.srem(self.key, request.fingerprint)


RFPDupeFilter = RedisRFPDupeFilter
ExRFPDupeFilter = ExRedisRFPDupeFilter
BloomDupeFilter = RedisBloomDupeFilter
ExBloomDupeFilter = ExRedisBloomDupeFilter
BloomSetDupeFilter = ExRedisBloomDupeFilter

