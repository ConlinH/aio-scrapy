from abc import ABCMeta, abstractmethod
from typing import Optional, Any, List

import aioscrapy
from aioscrapy.serializer import AbsSerializer
from aioscrapy.utils.reqser import request_from_dict


class AbsQueue(metaclass=ABCMeta):
    """Per-spider base queue class"""

    def __init__(
            self,
            container: Any,
            spider: Optional[aioscrapy.Spider] = None,
            key: Optional[str] = None,
            serializer: Optional[AbsSerializer] = None
    ) -> None:
        """Initialize per-spider queue"""
        self.container = container
        self.spider = spider
        self.key = key
        self.serializer = serializer

    @property
    @abstractmethod
    def inc_key(self) -> str:
        """stats inc_value"""

    @classmethod
    @abstractmethod
    async def from_spider(cls, spider: aioscrapy.Spider) -> "AbsQueue":
        """get queue instance from spider"""

    def _encode_request(self, request: aioscrapy.Request) -> Any:
        """Encode a request object"""
        obj = request.to_dict(spider=self.spider)
        return self.serializer.dumps(obj)

    def _decode_request(self, encoded_request: Any) -> aioscrapy.Request:
        """Decode an request previously encoded"""
        obj = self.serializer.loads(encoded_request)
        return request_from_dict(obj, spider=self.spider)

    def __len__(self) -> None:
        """Return the length of the queue"""
        raise Exception('please use len()')

    @abstractmethod
    async def len(self) -> int:
        """Return the length of the queue"""

    @abstractmethod
    async def push(self, request: aioscrapy.Request) -> None:
        """Push a request"""

    @abstractmethod
    async def push_batch(self, requests: List[aioscrapy.Request]) -> None:
        """Push a batch requests"""

    @abstractmethod
    async def pop(self, timeout: int = 0) -> Optional[aioscrapy.Request]:
        """Pop a request"""

    @abstractmethod
    async def clear(self) -> None:
        """Clear queue/stack"""
