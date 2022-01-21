import six

from scrapy.utils.misc import load_object
from aioscrapy.db import get_pool


# TODO: add SCRAPY_JOB support.
class Scheduler(object):

    def __init__(self, server,
                 persist=True,
                 flush_on_start=False,
                 queue_key='%(spider)s:requests',
                 queue_cls='aioscrapy.core.scheduler.queue.PriorityQueue',
                 dupefilter_key='%(spider)s:dupefilter',
                 dupefilter_cls='aioscrapy.core.scheduler.dupefilter.RFPDupeFilter',
                 idle_before_close=0,
                 serializer=None):

        if idle_before_close < 0:
            raise TypeError("idle_before_close cannot be negative")

        self.server = server
        self.persist = persist
        self.flush_on_start = flush_on_start
        self.queue_key = queue_key
        self.queue_cls = queue_cls
        self.dupefilter_cls = dupefilter_cls
        self.dupefilter_key = dupefilter_key
        self.idle_before_close = idle_before_close
        self.serializer = serializer
        self.stats = None

    @classmethod
    async def from_settings(cls, settings):
        kwargs = {
            'persist': settings.getbool('SCHEDULER_PERSIST'),
            'flush_on_start': settings.getbool('SCHEDULER_FLUSH_ON_START'),
            'idle_before_close': settings.getint('SCHEDULER_IDLE_BEFORE_CLOSE'),
        }

        # If these values are missing, it means we want to use the defaults.
        optional = {
            # TODO: Use custom prefixes for this settings to note that are
            # specific to scrapy-redis.
            'queue_key': 'SCHEDULER_QUEUE_KEY',
            'queue_cls': 'SCHEDULER_QUEUE_CLASS',
            'dupefilter_key': 'SCHEDULER_DUPEFILTER_KEY',
            # We use the default setting name to keep compatibility.
            'dupefilter_cls': 'DUPEFILTER_CLASS',
            'serializer': 'SCHEDULER_SERIALIZER',
        }
        for name, setting_name in optional.items():
            val = settings.get(setting_name)
            if val:
                kwargs[name] = val

        # Support serializer as a path to a module.
        if isinstance(kwargs.get('serializer'), six.string_types):
            # kwargs['serializer'] = importlib.import_module(kwargs['serializer'])
            kwargs['serializer'] = load_object(kwargs['serializer'])

        server = await get_pool('redis')
        # Ensure the connection is working.
        await server.ping()

        return cls(server=server, **kwargs)

    @classmethod
    async def from_crawler(cls, crawler):
        instance = await cls.from_settings(crawler.settings)
        # FIXME: for now, stats are only supported from this constructor
        instance.stats = crawler.stats
        return instance

    async def open(self, spider):
        self.spider = spider

        try:
            self.queue = load_object(self.queue_cls)(
                server=self.server,
                spider=spider,
                key=self.queue_key % {'spider': spider.name},
                serializer=self.serializer,
            )
        except TypeError as e:
            raise ValueError("Failed to instantiate queue class '%s': %s",
                             self.queue_cls, e)
        try:
            self.df = await load_object(self.dupefilter_cls).from_spider(spider)
        except TypeError as e:
            raise ValueError("Failed to instantiate dupefilter class '%s': %s",
                             self.dupefilter_cls, e)

        if self.flush_on_start:
            await self.flush()
        # notice if there are requests already in the queue to resume the crawl
        count = await self.queue.len()
        if count:
            spider.log("Resuming crawl (%d requests scheduled)" % count)

    async def close(self, reason):
        if not self.persist:
            await self.flush()

    async def flush(self):
        await self.df.clear()
        await self.queue.clear()

    async def enqueue_request(self, request):
        if not request.dont_filter and await self.df.request_seen(request):
            self.df.log(request, self.spider)
            return False
        if self.stats:
            self.stats.inc_value('scheduler/enqueued/redis', spider=self.spider)
        await self.queue.push(request)
        return True

    async def next_request(self):
        block_pop_timeout = self.idle_before_close
        request = await self.queue.pop(block_pop_timeout)
        if request and self.stats:
            self.stats.inc_value('scheduler/dequeued/redis', spider=self.spider)
        return request

    async def has_pending_requests(self):
        return await self.queue.len() > 0
