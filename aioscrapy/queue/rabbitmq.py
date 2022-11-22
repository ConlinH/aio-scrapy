from typing import Optional, List

import aioscrapy
from aioscrapy.db import db_manager
from aioscrapy.queue import AbsQueue
from aioscrapy.serializer import AbsSerializer
from aioscrapy.utils.misc import load_object


class RabbitMqPriorityQueue(AbsQueue):
    inc_key = 'scheduler/enqueued/rabbitmq'

    @classmethod
    def from_dict(cls, data: dict) -> "RabbitMqPriorityQueue":
        alias: str = data.get("alias", 'queue')
        server: aioscrapy.db.aiorabbitmq.RabbitmqExecutor = db_manager.rabbitmq.executor(alias)
        spider_name: str = data["spider_name"]
        serializer: str = data.get("serializer", "aioscrapy.serializer.JsonSerializer")
        serializer: AbsSerializer = load_object(serializer)
        return cls(
            server,
            key='%(spider)s:requests' % {'spider': spider_name},
            serializer=serializer
        )

    @classmethod
    async def from_spider(cls, spider: aioscrapy.Spider) -> "RabbitMqPriorityQueue":
        alias: str = spider.settings.get("SCHEDULER_QUEUE_ALIAS", 'queue')
        executor: aioscrapy.db.aiorabbitmq.RabbitmqExecutor = db_manager.rabbitmq.executor(alias)
        queue_key: str = spider.settings.get("SCHEDULER_QUEUE_KEY", '%(spider)s:requests')
        serializer: str = spider.settings.get("SCHEDULER_SERIALIZER", "aioscrapy.serializer.JsonSerializer")
        serializer: AbsSerializer = load_object(serializer)
        return cls(
            executor,
            spider,
            queue_key % {'spider': spider.name},
            serializer=serializer
        )

    async def len(self) -> int:
        return await self.container.get_message_count(self.key)

    async def push(self, request: aioscrapy.Request) -> None:
        data = self._encode_request(request)
        score = request.priority
        await self.container.publish(
            routing_key=self.key,
            body=data if isinstance(data, bytes) else data.encode(),
            priority=score
        )

    async def push_batch(self, requests: List[aioscrapy.Request]) -> None:
        # TODO: 实现rabbitmq的批量存储
        for request in requests:
            await self.push(request)

    async def pop(self, count: int = 1) -> Optional[aioscrapy.Request]:
        result = await self.container.get_message(self.key)
        if result:
            yield self._decode_request(result)

    async def clear(self) -> None:
        await self.container.clean_message_queue(self.key)


SpiderPriorityQueue = RabbitMqPriorityQueue
