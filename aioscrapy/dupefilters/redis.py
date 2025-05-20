"""
Redis-based Duplicate Filters for AioScrapy
AioScrapy的基于Redis的重复过滤器

This module provides several implementations of duplicate filters that use Redis
for storage. It includes a simple set-based filter, a Bloom filter implementation,
and extended versions of both that support removing fingerprints under certain
conditions.
此模块提供了几种使用Redis进行存储的重复过滤器实现。它包括一个简单的基于集合的过滤器、
一个布隆过滤器实现，以及两者的扩展版本，支持在特定条件下移除指纹。
"""

from typing import Literal

from aioscrapy import Request
from aioscrapy.db import db_manager
from aioscrapy.dupefilters import DupeFilterBase


class RedisRFPDupeFilter(DupeFilterBase):
    """
    Request Fingerprint duplicates filter built with Set of Redis.
    使用Redis集合构建的请求指纹重复过滤器。

    This filter uses a Redis SET to store request fingerprints. It implements
    the DupeFilterBase interface and provides methods for checking if a request
    has been seen before and for clearing the filter.
    此过滤器使用Redis SET来存储请求指纹。它实现了DupeFilterBase接口，
    并提供了检查请求是否已经被看到过以及清除过滤器的方法。
    """

    def __init__(
            self,
            server: "redis.asyncio.Redis",
            key: str,
            debug: bool = False,
            keep_on_close: bool = True,
            info: bool = False,
    ):
        """
        Initialize the Redis-based request fingerprint filter.
        初始化基于Redis的请求指纹过滤器。

        Args:
            server: The Redis server connection.
                   Redis服务器连接。
            key: The Redis key to use for storing fingerprints.
                用于存储指纹的Redis键。
            debug: Whether to log filtered requests.
                  是否记录被过滤的请求。
                  Defaults to False.
                  默认为False。
            keep_on_close: Whether to keep the fingerprints in Redis when the spider closes.
                          爬虫关闭时是否保留Redis中的指纹。
                          Defaults to True.
                          默认为True。
            info: Whether to log duplicate requests at INFO level.
                 是否在INFO级别记录重复的请求。
                 Defaults to False.
                 默认为False。
        """
        # Redis server connection
        # Redis服务器连接
        self.server = server

        # Redis key for storing fingerprints
        # 用于存储指纹的Redis键
        self.key = key

        # Whether to log filtered requests
        # 是否记录被过滤的请求
        self.debug = debug

        # Whether to keep fingerprints when the spider closes
        # 爬虫关闭时是否保留指纹
        self.keep_on_close = keep_on_close

        # Whether to log duplicate requests (will be set to False after first log)
        # 是否记录重复的请求（在第一次记录后将设置为False）
        self.logdupes: bool = True

        # Whether to log duplicate requests at INFO level
        # 是否在INFO级别记录重复的请求
        self.info: bool = info

    @classmethod
    def from_crawler(cls, crawler: "aioscrapy.crawler.Crawler"):
        """
        Create a RedisRFPDupeFilter instance from a crawler.
        从爬虫创建RedisRFPDupeFilter实例。

        This is the factory method used by AioScrapy to create the dupefilter.
        这是AioScrapy用于创建重复过滤器的工厂方法。

        Args:
            crawler: The crawler that will use this dupefilter.
                    将使用此重复过滤器的爬虫。

        Returns:
            RedisRFPDupeFilter: A new RedisRFPDupeFilter instance.
                               一个新的RedisRFPDupeFilter实例。
        """
        # Get Redis connection from database manager
        # 从数据库管理器获取Redis连接
        server = db_manager.redis.queue

        # Get dupefilter key pattern from settings, default to '%(spider)s:dupefilter'
        # 从设置获取重复过滤器键模式，默认为'%(spider)s:dupefilter'
        dupefilter_key = crawler.settings.get("SCHEDULER_DUPEFILTER_KEY", '%(spider)s:dupefilter')

        # Get keep_on_close setting, default to True
        # 获取keep_on_close设置，默认为True
        keep_on_close = crawler.settings.getbool("KEEP_DUPEFILTER_DATA_ON_CLOSE", True)

        # Format the key with the spider name
        # 使用爬虫名称格式化键
        key = dupefilter_key % {'spider': crawler.spider.name}

        # Get debug setting, default to False
        # 获取debug设置，默认为False
        debug = crawler.settings.getbool('DUPEFILTER_DEBUG', False)

        # Get info setting, default to False
        # 获取info设置，默认为False
        info = crawler.settings.getbool('DUPEFILTER_INFO', False)

        # Create and return a new instance
        # 创建并返回一个新实例
        instance = cls(server, key=key, debug=debug, keep_on_close=keep_on_close, info=info)
        return instance

    async def request_seen(self, request: Request) -> bool:
        """
        Check if a request has been seen before.
        检查请求是否已经被请求过。

        This method adds the request's fingerprint to the Redis SET and checks
        if it was already there. If the fingerprint was already in the SET,
        the request is considered a duplicate.
        此方法将请求的指纹添加到Redis SET中，并检查它是否已经存在。
        如果指纹已经在SET中，则认为请求是重复的。

        Args:
            request: The request to check.
                    要检查的请求。

        Returns:
            bool: True if the request has been seen before, False otherwise.
                 如果请求之前已经被看到过，则为True，否则为False。
        """
        # Add the fingerprint to the Redis SET and check if it was already there
        # sadd returns 0 if the member already exists in the set
        # 将指纹添加到Redis SET中，并检查它是否已经存在
        # sadd在成员已经存在于集合中时返回0
        return await self.server.sadd(self.key, request.fingerprint) == 0

    async def close(self, reason: str = ''):
        """
        Close the dupefilter.
        关闭重复过滤器。

        This method is called when the spider is closed. If keep_on_close is False,
        it clears the fingerprints from Redis.
        当爬虫关闭时调用此方法。如果keep_on_close为False，它会从Redis中清除指纹。

        Args:
            reason: The reason why the spider was closed.
                   爬虫被关闭的原因。
        """
        # If keep_on_close is False, clear the fingerprints
        # 如果keep_on_close为False，清除指纹
        if not self.keep_on_close:
            await self.clear()

    async def clear(self):
        """
        Clear all fingerprints from Redis.
        从Redis中清除所有指纹。

        This method deletes the Redis key used to store fingerprints,
        effectively clearing the filter.
        此方法删除用于存储指纹的Redis键，有效地清除过滤器。
        """
        # Delete the Redis key
        # 删除Redis键
        await self.server.delete(self.key)


class HashMap(object):
    """
    Simple hash map implementation for Bloom filter.
    布隆过滤器的简单哈希映射实现。

    This class implements a simple hash function that can be used by a Bloom filter
    to map values to bit positions in the filter.
    此类实现了一个简单的哈希函数，布隆过滤器可以使用它将值映射到过滤器中的位位置。
    """

    def __init__(self, m: int, seed: int):
        """
        Initialize the hash map.
        初始化哈希映射。

        Args:
            m: The size of the bit array (should be a power of 2).
               位数组的大小（应该是2的幂）。
            seed: The seed value for the hash function.
                 哈希函数的种子值。
        """
        # Size of the bit array
        # 位数组的大小
        self.m = m

        # Seed value for the hash function
        # 哈希函数的种子值
        self.seed = seed

    def hash(self, value: str) -> int:
        """
        Hash a string value to an integer.
        将字符串值哈希为整数。

        This method implements a simple hash function that converts a string
        to an integer hash value within the range of the bit array.
        此方法实现了一个简单的哈希函数，将字符串转换为位数组范围内的整数哈希值。

        Args:
            value: The string value to hash.
                  要哈希的字符串值。

        Returns:
            int: The hash value, which is an integer between 0 and m-1.
                哈希值，是0到m-1之间的整数。
        """
        # Initialize the return value
        # 初始化返回值
        ret = 0

        # Calculate the hash value
        # 计算哈希值
        for i in range(len(value)):
            ret += self.seed * ret + ord(value[i])

        # Ensure the hash value is within the range of the bit array
        # 确保哈希值在位数组的范围内
        return (self.m - 1) & ret


class BloomFilter(object):
    """
    Bloom filter implementation using Redis bitsets.
    使用Redis位集实现的布隆过滤器。

    A Bloom filter is a space-efficient probabilistic data structure that is used
    to test whether an element is a member of a set. False positives are possible,
    but false negatives are not.
    布隆过滤器是一种空间效率高的概率数据结构，用于测试元素是否是集合的成员。
    可能出现假阳性，但不会出现假阴性。
    """

    def __init__(self, server: "redis.asyncio.Redis", key: str, bit: int = 30, hash_number: int = 6):
        """
        Initialize the Bloom filter.
        初始化布隆过滤器。

        Args:
            server: The Redis server connection.
                   Redis服务器连接。
            key: The Redis key to use for the Bloom filter.
                用于布隆过滤器的Redis键。
            bit: The power of 2 to use for the bit array size (m = 2^bit).
                用于位数组大小的2的幂（m = 2^bit）。
                Defaults to 30, which gives a bit array of size 2^30 = 1,073,741,824 bits = 128MB.
                默认为30，这给出了大小为2^30 = 1,073,741,824位 = 128MB的位数组。
            hash_number: The number of hash functions to use.
                        要使用的哈希函数的数量。
                        Defaults to 6.
                        默认为6。
        """
        # Calculate the bit array size (m = 2^bit)
        # 计算位数组大小（m = 2^bit）
        # default to 1 << 30 = 1,073,741,824 = 2^30 = 128MB
        # max filter capacity is approximately 2^30/hash_number = 178,956,970 fingerprints
        # 默认为1 << 30 = 1,073,741,824 = 2^30 = 128MB
        # 最大过滤器容量约为2^30/hash_number = 178,956,970个指纹
        self.m = 1 << bit

        # Generate seeds for the hash functions
        # 生成哈希函数的种子
        self.seeds = range(hash_number)

        # Redis server connection
        # Redis服务器连接
        self.server = server

        # Redis key for the Bloom filter
        # 布隆过滤器的Redis键
        self.key = key

        # Create hash maps for each seed
        # 为每个种子创建哈希映射
        self.maps = [HashMap(self.m, seed) for seed in self.seeds]

    async def exists(self, value: str) -> bool:
        """
        Check if a value might exist in the Bloom filter.
        检查值是否可能存在于布隆过滤器中。

        This method checks if a value might be in the set represented by the Bloom filter.
        If it returns False, the value is definitely not in the set. If it returns True,
        the value might be in the set (false positives are possible).
        此方法检查值是否可能在布隆过滤器表示的集合中。
        如果返回False，则该值肯定不在集合中。如果返回True，
        则该值可能在集合中（可能出现假阳性）。

        Args:
            value: The value to check.
                  要检查的值。

        Returns:
            bool: True if the value might exist in the set, False if it definitely does not.
                 如果值可能存在于集合中，则为True；如果它肯定不存在，则为False。
        """
        # Empty values are never in the set
        # 空值永远不在集合中
        if not value:
            return False

        # Use a Redis pipeline to get all the bits in one round-trip
        # 使用Redis管道在一次往返中获取所有位
        async with self.server.pipeline(transaction=True) as pipe:
            # For each hash function, get the bit at the hashed position
            # 对于每个哈希函数，获取哈希位置的位
            for f in self.maps:
                offset = f.hash(value)
                pipe.getbit(self.key, offset)

            # Execute the pipeline and get the results
            # 执行管道并获取结果
            result = await pipe.execute()

        # If all bits are set, the value might be in the set
        # 如果所有位都已设置，则该值可能在集合中
        return all(result)

    async def insert(self, value: str) -> None:
        """
        Insert a value into the Bloom filter.
        将值插入布隆过滤器。

        This method sets the bits in the Bloom filter corresponding to the value,
        so that future calls to exists() for this value will return True.
        此方法设置布隆过滤器中与值对应的位，
        以便将来对此值调用exists()将返回True。

        Args:
            value: The value to insert.
                  要插入的值。
        """
        # Use a Redis pipeline to set all the bits in one round-trip
        # 使用Redis管道在一次往返中设置所有位
        async with self.server.pipeline(transaction=True) as pipe:
            # For each hash function, set the bit at the hashed position
            # 对于每个哈希函数，设置哈希位置的位
            for f in self.maps:
                offset = f.hash(value)
                pipe.setbit(self.key, offset, 1)

            # Execute the pipeline
            # 执行管道
            await pipe.execute()


class RedisBloomDupeFilter(RedisRFPDupeFilter):
    """
    Bloom filter-based duplicate filter built with Redis bitmaps.
    使用Redis位图构建的基于布隆过滤器的重复过滤器。

    This filter uses a Bloom filter implemented with Redis bitmaps to store
    request fingerprints. It is more space-efficient than the simple SET-based
    filter, but has a small probability of false positives.
    此过滤器使用使用Redis位图实现的布隆过滤器来存储请求指纹。
    它比简单的基于SET的过滤器更节省空间，但有小概率出现假阳性。
    """

    def __init__(self, server: "redis.asyncio.Redis", key: str, debug: bool, bit: int,
                 hash_number: int, keep_on_close: bool, info: bool):
        """
        Initialize the Bloom filter-based duplicate filter.
        初始化基于布隆过滤器的重复过滤器。

        Args:
            server: The Redis server connection.
                   Redis服务器连接。
            key: The Redis key to use for the Bloom filter.
                用于布隆过滤器的Redis键。
            debug: Whether to log filtered requests.
                  是否记录被过滤的请求。
            bit: The power of 2 to use for the bit array size (m = 2^bit).
                用于位数组大小的2的幂（m = 2^bit）。
            hash_number: The number of hash functions to use.
                        要使用的哈希函数的数量。
            keep_on_close: Whether to keep the fingerprints in Redis when the spider closes.
                          爬虫关闭时是否保留Redis中的指纹。
            info: Whether to log duplicate requests at INFO level.
                 是否在INFO级别记录重复的请求。
        """
        # Initialize the parent class
        # 初始化父类
        super().__init__(server, key, debug, keep_on_close, info)

        # Store Bloom filter parameters
        # 存储布隆过滤器参数
        self.bit = bit
        self.hash_number = hash_number

        # Create the Bloom filter
        # 创建布隆过滤器
        self.bf = BloomFilter(server, self.key, bit, hash_number)

    @classmethod
    async def from_crawler(cls, crawler: "aioscrapy.crawler.Crawler"):
        """
        Create a RedisBloomDupeFilter instance from a crawler.
        从爬虫创建RedisBloomDupeFilter实例。

        This is the factory method used by AioScrapy to create the dupefilter.
        这是AioScrapy用于创建重复过滤器的工厂方法。

        Args:
            crawler: The crawler that will use this dupefilter.
                    将使用此重复过滤器的爬虫。

        Returns:
            RedisBloomDupeFilter: A new RedisBloomDupeFilter instance.
                                 一个新的RedisBloomDupeFilter实例。
        """
        # Get Redis connection from database manager
        # 从数据库管理器获取Redis连接
        server = db_manager.redis.queue

        # Get dupefilter key pattern from settings, default to '%(spider)s:bloomfilter'
        # 从设置获取重复过滤器键模式，默认为'%(spider)s:bloomfilter'
        dupefilter_key = crawler.settings.get("SCHEDULER_DUPEFILTER_KEY", '%(spider)s:bloomfilter')

        # Get keep_on_close setting, default to True
        # 获取keep_on_close设置，默认为True
        keep_on_close = crawler.settings.getbool("KEEP_DUPEFILTER_DATA_ON_CLOSE", True)

        # Format the key with the spider name
        # 使用爬虫名称格式化键
        key = dupefilter_key % {'spider': crawler.spider.name}

        # Get debug setting, default to False
        # 获取debug设置，默认为False
        debug = crawler.settings.getbool('DUPEFILTER_DEBUG', False)

        # Get info setting, default to False
        # 获取info设置，默认为False
        info = crawler.settings.getbool('DUPEFILTER_INFO', False)

        # Get Bloom filter parameters from settings
        # 从设置获取布隆过滤器参数
        bit = crawler.settings.getint('BLOOMFILTER_BIT', 30)
        hash_number = crawler.settings.getint('BLOOMFILTER_HASH_NUMBER', 6)

        # Create and return a new instance
        # 创建并返回一个新实例
        return cls(server, key=key, debug=debug, bit=bit, hash_number=hash_number,
                   keep_on_close=keep_on_close, info=info)

    async def request_seen(self, request: Request) -> bool:
        """
        Check if a request has been seen before.
        检查请求是否已经被看到过。

        This method checks if the request's fingerprint exists in the Bloom filter.
        If it does, the request is considered a duplicate. If not, the fingerprint
        is added to the Bloom filter.
        此方法检查请求的指纹是否存在于布隆过滤器中。
        如果存在，则认为请求是重复的。如果不存在，则将指纹添加到布隆过滤器中。

        Args:
            request: The request to check.
                    要检查的请求。

        Returns:
            bool: True if the request has been seen before, False otherwise.
                 如果请求之前已经被看到过，则为True，否则为False。
        """
        # Check if the fingerprint exists in the Bloom filter
        # 检查指纹是否存在于布隆过滤器中
        fp = await self.bf.exists(request.fingerprint)

        # If the fingerprint exists, the request is a duplicate
        # 如果指纹存在，则请求是重复的
        if fp:
            return True

        # If not, add the fingerprint to the Bloom filter
        # 如果不存在，则将指纹添加到布隆过滤器中
        await self.bf.insert(request.fingerprint)

        # The request has not been seen before
        # 请求之前未被看到过
        return False


class ExRedisBloomDupeFilter(RedisBloomDupeFilter):
    """
    Extended Bloom filter-based duplicate filter with temporary SET storage.
    具有临时SET存储的扩展基于布隆过滤器的重复过滤器。

    This filter extends the RedisBloomDupeFilter by adding a temporary SET to store
    fingerprints of requests that are currently being processed. This allows for
    removing fingerprints from the filter if the request fails, which can be useful
    for retrying failed requests.
    此过滤器通过添加一个临时SET来扩展RedisBloomDupeFilter，用于存储当前正在处理的
    请求的指纹。这允许在请求失败时从过滤器中删除指纹，这对于重试失败的请求很有用。
    """

    def __init__(self, server: "redis.asyncio.Redis", key: str, key_set: str, ttl: int,
                 debug: bool, bit: int, hash_number: int, keep_on_close: bool, info: bool):
        """
        Initialize the extended Bloom filter-based duplicate filter.
        初始化扩展的基于布隆过滤器的重复过滤器。

        Args:
            server: The Redis server connection.
                   Redis服务器连接。
            key: The Redis key to use for the Bloom filter.
                用于布隆过滤器的Redis键。
            key_set: The Redis key to use for the temporary SET.
                    用于临时SET的Redis键。
            ttl: The time-to-live in seconds for the temporary SET.
                临时SET的生存时间（秒）。
            debug: Whether to log filtered requests.
                  是否记录被过滤的请求。
            bit: The power of 2 to use for the bit array size (m = 2^bit).
                用于位数组大小的2的幂（m = 2^bit）。
            hash_number: The number of hash functions to use.
                        要使用的哈希函数的数量。
            keep_on_close: Whether to keep the fingerprints in Redis when the spider closes.
                          爬虫关闭时是否保留Redis中的指纹。
            info: Whether to log duplicate requests at INFO level.
                 是否在INFO级别记录重复的请求。
        """
        # Initialize the parent class
        # 初始化父类
        super().__init__(server, key, debug, bit, hash_number, keep_on_close, info)

        # Redis key for the temporary SET
        # 临时SET的Redis键
        self.key_set = key_set

        # Time-to-live for the temporary SET
        # 临时SET的生存时间
        self.ttl = ttl

    @classmethod
    async def from_crawler(cls, crawler: "aioscrapy.crawler.Crawler"):
        """
        Create an ExRedisBloomDupeFilter instance from a crawler.
        从爬虫创建ExRedisBloomDupeFilter实例。

        This is the factory method used by AioScrapy to create the dupefilter.
        这是AioScrapy用于创建重复过滤器的工厂方法。

        Args:
            crawler: The crawler that will use this dupefilter.
                    将使用此重复过滤器的爬虫。

        Returns:
            ExRedisBloomDupeFilter: A new ExRedisBloomDupeFilter instance.
                                   一个新的ExRedisBloomDupeFilter实例。
        """
        # Get Redis connection from database manager
        # 从数据库管理器获取Redis连接
        server = db_manager.redis.queue

        # Get dupefilter key pattern from settings, default to '%(spider)s:bloomfilter'
        # 从设置获取重复过滤器键模式，默认为'%(spider)s:bloomfilter'
        dupefilter_key = crawler.settings.get("SCHEDULER_DUPEFILTER_KEY", '%(spider)s:bloomfilter')

        # Get keep_on_close setting, default to True
        # 获取keep_on_close设置，默认为True
        keep_on_close = crawler.settings.getbool("KEEP_DUPEFILTER_DATA_ON_CLOSE", True)

        # Format the key with the spider name
        # 使用爬虫名称格式化键
        key = dupefilter_key % {'spider': crawler.spider.name}

        # Get debug setting, default to False
        # 获取debug设置，默认为False
        debug = crawler.settings.getbool('DUPEFILTER_DEBUG', False)

        # Get info setting, default to False
        # 获取info设置，默认为False
        info = crawler.settings.getbool('DUPEFILTER_INFO', False)

        # Get Bloom filter parameters from settings
        # 从设置获取布隆过滤器参数
        bit = crawler.settings.getint('BLOOMFILTER_BIT', 30)
        hash_number = crawler.settings.getint('BLOOMFILTER_HASH_NUMBER', 6)

        # Get TTL for the temporary SET, default to 180 seconds
        # 获取临时SET的TTL，默认为180秒
        ttl = crawler.settings.getint('DUPEFILTER_SET_KEY_TTL', 180)

        # Create and return a new instance
        # 创建并返回一个新实例
        return cls(server, key=key, key_set=key + "_set", ttl=ttl, debug=debug, bit=bit,
                   hash_number=hash_number, keep_on_close=keep_on_close, info=info)

    async def request_seen(self, request: Request) -> bool:
        """
        Check if a request has been seen before.
        检查请求是否已经被看到过。

        This method first checks if the request's fingerprint exists in the Bloom filter.
        If it does, the request is considered a duplicate. If not, the fingerprint is
        added to the temporary SET with a TTL, but not yet to the Bloom filter.
        此方法首先检查请求的指纹是否存在于布隆过滤器中。
        如果存在，则认为请求是重复的。如果不存在，则将指纹添加到具有TTL的临时SET中，
        但尚未添加到布隆过滤器中。

        Args:
            request: The request to check.
                    要检查的请求。

        Returns:
            bool: True if the request has been seen before, False otherwise.
                 如果请求之前已经被看到过，则为True，否则为False。
        """
        # Check if the fingerprint exists in the Bloom filter
        # 检查指纹是否存在于布隆过滤器中
        fp = await self.bf.exists(request.fingerprint)

        # If the fingerprint exists in the Bloom filter, the request is a duplicate
        # 如果指纹存在于布隆过滤器中，则请求是重复的
        if fp:
            return True

        # If not, add the fingerprint to the temporary SET with a TTL
        # 如果不存在，则将指纹添加到具有TTL的临时SET中
        async with self.server.pipeline() as pipe:
            pipe.sadd(self.key_set, request.fingerprint)
            pipe.expire(self.key_set, self.ttl)
            ret, _ = await pipe.execute()

        # Return True if the fingerprint was already in the temporary SET (ret == 0)
        # 如果指纹已经在临时SET中，则返回True（ret == 0）
        return ret == 0

    async def done(
            self,
            request: Request,
            done_type: Literal["request_ok", "request_err", "parse_ok", "parse_err"]
    ) -> None:
        """
        Handle the completion of a request.
        处理请求的完成。

        This method is called when a request has been processed. It handles the
        fingerprint differently based on the done_type:
        - For "request_ok" or "request_err", it removes the fingerprint from the temporary SET.
        - For "parse_ok", it adds the fingerprint to the Bloom filter.
        当请求已处理时调用此方法。它根据done_type不同地处理指纹：
        - 对于"request_ok"或"request_err"，它从临时SET中删除指纹。
        - 对于"parse_ok"，它将指纹添加到布隆过滤器中。

        Args:
            request: The request that has been processed.
                    已处理的请求。
            done_type: The status of the request processing.
                      请求处理的状态。
                      Can be one of: "request_ok", "request_err", "parse_ok", "parse_err".
                      可以是以下之一："request_ok"、"request_err"、"parse_ok"、"parse_err"。
        """
        # If the request was successful or failed at the request level,
        # remove the fingerprint from the temporary SET
        # 如果请求成功或在请求级别失败，则从临时SET中删除指纹
        if done_type == "request_ok" or done_type == "request_err":
            await self.server.srem(self.key_set, request.fingerprint)

        # If the request was successfully parsed, add the fingerprint to the Bloom filter
        # 如果请求成功解析，则将指纹添加到布隆过滤器中
        elif done_type == "parse_ok":
            await self.bf.insert(request.fingerprint)

    async def close(self, reason: str = ''):
        """
        Close the dupefilter.
        关闭重复过滤器。

        This method is called when the spider is closed. If keep_on_close is False,
        it clears the Bloom filter. It also deletes the temporary SET.
        当爬虫关闭时调用此方法。如果keep_on_close为False，它会清除布隆过滤器。
        它还会删除临时SET。

        Args:
            reason: The reason why the spider was closed.
                   爬虫被关闭的原因。
        """
        # If keep_on_close is False, clear the Bloom filter
        # 如果keep_on_close为False，清除布隆过滤器
        if not self.keep_on_close:
            await self.clear()

        # Delete the temporary SET
        # 删除临时SET
        await self.server.delete(self.key_set)


class ExRedisRFPDupeFilter(RedisRFPDupeFilter):
    """
    Extended Redis SET-based duplicate filter with fingerprint removal.
    具有指纹移除功能的扩展Redis SET基于的重复过滤器。

    This filter extends the RedisRFPDupeFilter by adding the ability to remove
    fingerprints from the filter if the request fails, which can be useful for
    retrying failed requests.
    此过滤器通过添加在请求失败时从过滤器中删除指纹的功能来扩展RedisRFPDupeFilter，
    这对于重试失败的请求很有用。
    """

    async def done(
            self,
            request: Request,
            done_type: Literal["request_ok", "request_err", "parse_ok", "parse_err"]
    ) -> None:
        """
        Handle the completion of a request.
        处理请求的完成。

        This method is called when a request has been processed. It removes the
        fingerprint from the Redis SET if the request or parsing failed, allowing
        the request to be retried.
        当请求已处理时调用此方法。如果请求或解析失败，它会从Redis SET中删除指纹，
        允许重试请求。

        Args:
            request: The request that has been processed.
                    已处理的请求。
            done_type: The status of the request processing.
                      请求处理的状态。
                      Can be one of: "request_ok", "request_err", "parse_ok", "parse_err".
                      可以是以下之一："request_ok"、"request_err"、"parse_ok"、"parse_err"。
        """
        # When the request or parsing fails, remove the fingerprint from the Redis SET
        # 当请求失败或解析失败时，从Redis的Set中移除指纹
        if done_type == "request_err" or done_type == "parse_err":
            await self.server.srem(self.key, request.fingerprint)


# Aliases for backward compatibility
# 用于向后兼容的别名
RFPDupeFilter = RedisRFPDupeFilter
ExRFPDupeFilter = ExRedisRFPDupeFilter
BloomDupeFilter = RedisBloomDupeFilter
ExBloomDupeFilter = ExRedisBloomDupeFilter
BloomSetDupeFilter = ExRedisBloomDupeFilter

