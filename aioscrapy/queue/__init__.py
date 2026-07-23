from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Optional, Sequence

import aioscrapy

from aioscrapy.serializer import AbsSerializer
from aioscrapy.utils.reqser import request_from_dict


@dataclass
class QueueDelivery:
    """A request reserved from a queue until it is acknowledged."""

    request: aioscrapy.Request
    task_id: str
    token: str
    receipt: Any = None
    redelivered: bool = False
    score: float = 0


class AbsQueue(metaclass=ABCMeta):
    """Base interface for per-spider request queues."""

    @property
    def requires_periodic_poll(self) -> bool:
        return True

    def __init__(
            self,
            container: Any,
            spider: Optional[aioscrapy.Spider] = None,
            key: Optional[str] = None,
            serializer: Optional[AbsSerializer] = None,
    ) -> None:
        self.container = container
        self.spider = spider
        self.key = key
        self.serializer = serializer

    @property
    @abstractmethod
    def inc_key(self) -> str:
        """Return the stats key used for queue operations."""

    @classmethod
    @abstractmethod
    async def from_spider(cls, spider: aioscrapy.Spider) -> "AbsQueue":
        """Create a queue configured for a spider."""

    def _encode_request(self, request: aioscrapy.Request) -> Any:
        return self.serializer.dumps(request.to_dict(spider=self.spider))

    async def _decode_request(self, encoded_request: Any) -> aioscrapy.Request:
        obj = self.serializer.loads(encoded_request)
        return await request_from_dict(obj, spider=self.spider)

    def __len__(self) -> None:
        raise Exception('please use len()')

    @abstractmethod
    async def len(self) -> int:
        """Return ready plus reserved request count."""

    @abstractmethod
    async def push(self, request: aioscrapy.Request) -> None:
        """Push one request."""

    @abstractmethod
    async def push_batch(self, requests: List[aioscrapy.Request]) -> None:
        """Push multiple requests in one logical operation."""

    @abstractmethod
    async def reserve(self, count: int = 1, visibility_timeout: float = 600) -> List[QueueDelivery]:
        """Reserve requests without deleting their durable payload."""

    async def pop(self, count: int = 1):
        """Compatibility helper retaining the old destructive-pop behavior."""
        deliveries = await self.reserve(count)
        if deliveries:
            await self.ack_batch(deliveries)
        for delivery in deliveries:
            yield delivery.request

    @abstractmethod
    async def ack_batch(self, deliveries: Sequence[QueueDelivery]) -> List[bool]:
        """Acknowledge completed deliveries."""

    async def ack(self, delivery: QueueDelivery) -> bool:
        result = await self.ack_batch([delivery])
        return bool(result and result[0])

    @abstractmethod
    async def nack_batch(self, deliveries: Sequence[QueueDelivery]) -> List[bool]:
        """Return unfinished deliveries to the queue."""

    async def nack(self, delivery: QueueDelivery) -> bool:
        result = await self.nack_batch([delivery])
        return bool(result and result[0])

    async def close(self) -> None:
        """Release queue-specific resources."""

    @abstractmethod
    async def clear(self) -> None:
        """Delete ready, reserved, and payload data."""
