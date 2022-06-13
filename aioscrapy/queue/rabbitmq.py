from aioscrapy.db import db_manager
from aioscrapy.queue import AbsQueue
from aioscrapy.serializer import AbsSerializer
from aioscrapy.utils.misc import load_object


class RabbitMqPriorityQueue(AbsQueue):
    inc_key = 'scheduler/enqueued/rabbitmq'

    @classmethod
    def from_dict(cls, data: dict) -> "AbsQueue":
        alias = data.get("alias", 'queue')
        server = db_manager.rabbitmq.executor(alias)
        spider_name = data["spider_name"]
        serializer = data.get("serializer", "aioscrapy.serializer.JsonSerializer")
        serializer: AbsSerializer = load_object(serializer)
        return cls(
            server,
            key='%(spider)s:requests' % {'spider': spider_name},
            serializer=serializer
        )

    @classmethod
    async def from_spider(cls, spider) -> "RabbitMqPriorityQueue":
        settings = spider.settings
        alias = settings.get("SCHEDULER_QUEUE_ALIAS", 'queue')
        executor = db_manager.rabbitmq.executor(alias)
        queue_key = settings.get("SCHEDULER_QUEUE_KEY", '%(spider)s:requests')
        serializer = settings.get("SCHEDULER_SERIALIZER", "aioscrapy.serializer.JsonSerializer")
        serializer: AbsSerializer = load_object(serializer)
        return cls(
            executor,
            spider,
            queue_key % {'spider': spider.name},
            serializer=serializer
        )

    async def len(self) -> int:
        return await self.container.get_message_count(self.key)

    async def push(self, request):
        data = self._encode_request(request)
        score = request.priority
        await self.container.publish(
            routing_key=self.key,
            body=data if isinstance(data, bytes) else data.encode(),
            priority=score
        )

    async def pop(self, timeout=0):
        result = await self.container.get_message(self.key)
        if result:
            return self._decode_request(result)

    async def clear(self):
        return await self.container.clean_message_queue(self.key)


SpiderPriorityQueue = RabbitMqPriorityQueue
