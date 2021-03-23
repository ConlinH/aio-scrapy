import logging

from scrapy import Request
from scrapy.utils.misc import load_object
from scrapy.utils.python import to_unicode
from scrapy.utils.reqser import _get_method
from scrapy.utils.reqser import request_to_dict, request_from_dict

from .picklecompat import PickleCompat, JsonPickleCompat

logger = logging.getLogger(__name__)

_to_str = lambda x: x if isinstance(x, str) else str(x)


class Base(object):
    """Per-spider base queue class"""

    def __init__(self, server, spider, key, serializer=None):
        """Initialize per-spider redis queue.

        Parameters
        ----------
        server : StrictRedis
            Redis client instance.
        spider : Spider
            Scrapy spider instance.
        key: str
            Redis key where to put and get messages.
        serializer : object
            Serializer object with ``loads`` and ``dumps`` methods.

        """
        if serializer is None:
            # Backward compatibility.
            # TODO: deprecate pickle.
            serializer = PickleCompat
        if not hasattr(serializer, 'loads'):
            raise TypeError("serializer does not implement 'loads' function: %r"
                            % serializer)
        if not hasattr(serializer, 'dumps'):
            raise TypeError("serializer '%s' does not implement 'dumps' function: %r"
                            % serializer)

        self.server = server
        self.spider = spider
        self.key = key % {'spider': spider.name}
        self.serializer = serializer

    def _encode_request(self, request):
        """Encode a request object"""
        obj = request_to_dict(request, self.spider)
        return self.serializer.dumps(obj)

    def _decode_request(self, encoded_request):
        """Decode an request previously encoded"""
        obj = self.serializer.loads(encoded_request)
        return request_from_dict(obj, self.spider)

    def __len__(self):
        """Return the length of the queue"""
        raise Exception('please use len()')

    async def len(self):
        raise NotImplementedError

    async def push(self, request):
        """Push a request"""
        raise NotImplementedError

    async def pop(self, timeout=0):
        """Pop a request"""
        raise NotImplementedError

    async def clear(self):
        """Clear queue/stack"""
        await self.server.delete(self.key)


class FifoQueue(Base):
    """Per-spider FIFO queue"""

    async def len(self):
        return await self.server.llen(self.key)

    async def push(self, request):
        """Push a request"""
        await self.server.lpush(self.key, self._encode_request(request))

    async def pop(self, timeout=0):
        """Pop a request"""
        if timeout > 0:
            data = await self.server.brpop(self.key, timeout)
            if isinstance(data, tuple):
                data = data[1]
        else:
            data = await self.server.rpop(self.key)
        if data:
            return self._decode_request(data)


class PriorityQueue(Base):
    """Per-spider priority queue abstraction using redis' sorted set"""

    async def len(self):
        return await self.server.zcard(self.key)

    async def push(self, request):
        """Push a request"""
        data = self._encode_request(request)
        score = -request.priority
        # We don't use zadd method as the order of arguments change depending on
        # whether the class is Redis or StrictRedis, and the option of using
        # kwargs only accepts strings, not bytes.
        await self.server.zadd(self.key, score, data)

    async def pop(self, timeout=0):
        """
        Pop a request
        timeout not support in this queue class
        """
        # use atomic range/remove using multi/exec
        pipe = self.server.multi_exec()
        pipe.zrange(self.key, 0, 0)
        pipe.zremrangebyrank(self.key, 0, 0)
        results, count = await pipe.execute()
        if results:
            return self._decode_request(results[0])


class LifoQueue(Base):
    """Per-spider LIFO queue."""

    async def len(self):
        return await self.server.llen(self.key)

    async def push(self, request):
        """Push a request"""
        await self.server.lpush(self.key, self._encode_request(request))

    async def pop(self, timeout=0):
        """Pop a request"""
        if timeout > 0:
            data = await self.server.blpop(self.key, timeout)
            if isinstance(data, tuple):
                data = data[1]
        else:
            data = await self.server.lpop(self.key)

        if data:
            return self._decode_request(data)


class JsonPriorityQueue(PriorityQueue):

    def __init__(self, server, spider, key, serializer=None):
        if serializer is None:
            serializer = JsonPickleCompat

        super().__init__(server, spider, key, serializer)

    def _decode_request(self, encoded_request):
        obj = self.serializer.loads(encoded_request)
        return self._request_from_dict(obj, self.spider)

    @staticmethod
    def _request_from_dict(d, spider=None):
        """对 scrapy.utils.reqser.request_from_dict 方法的重写, 使其能处理formdata的post请求"""
        cb = d.setdefault('callback', 'parse')
        if cb and spider:
            cb = _get_method(spider, cb)
        eb = d.setdefault('errback', None)
        if eb and spider:
            eb = _get_method(spider, eb)

        kwargs = dict(
            url=to_unicode(d['url']),
            callback=cb,
            errback=eb,
            method=d.setdefault('method', 'GET'),
            headers=d.setdefault('headers', None),
            body=d.setdefault('body', None),
            cookies=d.setdefault('cookies', None),
            meta=d.setdefault('meta', None),
            encoding=d.setdefault('_encoding', 'utf-8'),
            priority=d.setdefault('priority', 0),
            dont_filter=d.setdefault('dont_filter', False),
            flags=d.setdefault('flags', None)
        )
        if 'formdata' in d:
            d['_class'] = 'scrapy.FormRequest'
            kwargs['method'] = 'POST'
            kwargs['formdata'] = {key: _to_str(d['formdata'][key]) for key in d['formdata']}

        request_cls = load_object(d['_class']) if '_class' in d else Request

        return request_cls(**kwargs)


# TODO: Deprecate the use of these names.
SpiderQueue = FifoQueue
SpiderStack = LifoQueue
SpiderPriorityQueue = PriorityQueue
SpiderJsonPriorityQueue = JsonPriorityQueue
