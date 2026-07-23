from typing import List, Sequence
from uuid import uuid4

import aioscrapy

from aioscrapy.db import db_manager
from aioscrapy.queue import AbsQueue, QueueDelivery
from aioscrapy.serializer import AbsSerializer
from aioscrapy.utils.misc import load_object


class RabbitMqPriorityQueue(AbsQueue):
    inc_key = 'scheduler/enqueued/rabbitmq'

    @classmethod
    def from_dict(cls, data: dict) -> "RabbitMqPriorityQueue":
        alias = data.get('alias', 'queue')
        serializer: AbsSerializer = load_object(
            data.get('serializer', 'aioscrapy.serializer.JsonSerializer')
        )
        return cls(
            db_manager.rabbitmq.executor(alias),
            key=data.get('key', '%(spider)s:requests') % {'spider': data['spider_name']},
            serializer=serializer,
        )

    @classmethod
    async def from_spider(cls, spider: aioscrapy.Spider) -> "RabbitMqPriorityQueue":
        alias = spider.settings.get('SCHEDULER_QUEUE_ALIAS', 'queue')
        queue_key = spider.settings.get('SCHEDULER_QUEUE_KEY', '%(spider)s:requests')
        serializer: AbsSerializer = load_object(
            spider.settings.get('SCHEDULER_SERIALIZER', 'aioscrapy.serializer.JsonSerializer')
        )
        return cls(
            db_manager.rabbitmq.executor(alias),
            spider,
            queue_key % {'spider': spider.name},
            serializer=serializer,
        )

    async def len(self) -> int:
        return await self.container.get_ready_message_count(self.key)

    async def push(self, request: aioscrapy.Request) -> None:
        task_id = uuid4().hex
        data = self._encode_request(request)
        await self.container.publish(
            routing_key=self.key,
            body=data if isinstance(data, bytes) else data.encode(),
            priority=request.priority,
            message_id=task_id,
            delivery_mode=2,
        )

    async def push_batch(self, requests: List[aioscrapy.Request]) -> None:
        for request in requests:
            await self.push(request)

    async def reserve(self, count: int = 1, visibility_timeout: float = 600) -> List[QueueDelivery]:
        deliveries = []
        for _ in range(max(0, count)):
            message = await self.container.reserve_message(self.key)
            if message is None:
                break
            task_id = message.message_id or uuid4().hex
            token = str(message.delivery_tag)
            deliveries.append(QueueDelivery(
                request=await self._decode_request(message.body),
                task_id=task_id,
                token=token,
                receipt=message,
                redelivered=bool(message.redelivered),
            ))
        return deliveries

    async def ack_batch(self, deliveries: Sequence[QueueDelivery]) -> List[bool]:
        results = []
        for delivery in deliveries:
            if delivery.receipt.processed:
                results.append(True)
            else:
                await delivery.receipt.ack()
                results.append(True)
        return results

    async def nack_batch(self, deliveries: Sequence[QueueDelivery]) -> List[bool]:
        results = []
        for delivery in deliveries:
            if delivery.receipt.processed:
                results.append(True)
            else:
                await delivery.receipt.nack(requeue=True)
                results.append(True)
        return results

    async def clear(self) -> None:
        await self.container.clean_message_queue(self.key)


SpiderPriorityQueue = RabbitMqPriorityQueue
