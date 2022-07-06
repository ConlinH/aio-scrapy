from aioscrapy.utils.misc import load_object
from aioscrapy.utils.tools import call_helper
from typing import Optional


class Scheduler(object):

    def __init__(
            self,
            queue_cls: Optional[str] = None,
            dupefilter_cls: Optional[str] = None,
            persist=True,
            flush_on_start=False,
    ):
        self.persist = persist
        self.flush_on_start = flush_on_start
        self.queue_cls = queue_cls
        self.dupefilter_cls = dupefilter_cls
        self.stats = None
        self.spider = None
        self.queue = None
        self.df = None

    @classmethod
    async def from_settings(cls, settings):
        kwargs = {
            'persist': settings.getbool('SCHEDULER_PERSIST', True),
            'flush_on_start': settings.getbool('SCHEDULER_FLUSH_ON_START', False),
            'queue_cls': settings.get('SCHEDULER_QUEUE_CLASS'),
            'dupefilter_cls': settings.get('DUPEFILTER_CLASS'),
        }
        return cls(**kwargs)

    @classmethod
    async def from_crawler(cls, crawler):
        instance = await cls.from_settings(crawler.settings)
        instance.stats = crawler.stats
        return instance

    async def open(self, spider):
        self.spider = spider

        try:
            self.queue = await call_helper(load_object(self.queue_cls).from_spider, spider)
        except TypeError as e:
            raise ValueError("Failed to instantiate queue class '%s': %s", self.queue_cls, e)
        try:
            if self.dupefilter_cls:
                self.df = await call_helper(load_object(self.dupefilter_cls).from_spider, spider)
        except TypeError as e:
            raise ValueError("Failed to instantiate dupefilter class '%s': %s", self.dupefilter_cls, e)

        if self.flush_on_start:
            await self.flush()

        # notice if there are requests already in the queue to resume the crawl
        count = await call_helper(self.queue.len)
        if count:
            spider.log("Resuming crawl (%d requests scheduled)" % count)

    async def close(self, reason):
        if not self.persist:
            await self.flush()
        self.df and await call_helper(self.df.close, reason)

    async def flush(self):
        self.df and await call_helper(self.df.clear)
        await call_helper(self.queue.clear)

    async def enqueue_request(self, request):
        if not request.dont_filter \
                and request.filter_mode == 'IN_QUEUE' \
                and self.df and await self.df.request_seen(request):
            self.df.log(request, self.spider)
            return False

        await call_helper(self.queue.push, request)
        if self.stats:
            self.stats.inc_value(self.queue.inc_key, spider=self.spider)
        return True

    async def next_request(self, count=1):
        async for request in await call_helper(self.queue.pop, count):
            if request and not request.dont_filter \
                    and request.filter_mode == 'OUT_QUEUE' \
                    and self.df and await self.df.request_seen(request):
                self.df.log(request, self.spider)
                continue

            if request and self.stats:
                self.stats.inc_value(self.queue.inc_key, spider=self.spider)
            yield request

    async def has_pending_requests(self):
        return await call_helper(self.queue.len) > 0
