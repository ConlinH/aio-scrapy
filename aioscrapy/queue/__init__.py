from abc import ABCMeta, abstractmethod
from typing import Optional

from aioscrapy.utils.reqser import request_to_dict, request_from_dict
from aioscrapy.serializer import AbsSerializer
from aioscrapy.utils.misc import load_object
from aioscrapy.db import db_manager


class AbsQueue(object, metaclass=ABCMeta):
    """Per-spider base queue class"""

    def __init__(
            self, container,
            spider: Optional[str] = None,
            key: Optional[str] = None,
            serializer: Optional[AbsSerializer] = None
    ):
        """Initialize per-spider redis queue.

        Parameters
        ----------
        container : Redis/Queue
            The queue for Request.
        spider : Spider
            aioscrapy spider instance.
        key: str
            Redis key where to put and get messages.
        serializer : object
            Serializer object with ``loads`` and ``dumps`` methods.

        """
        self.container = container
        self.spider = spider
        self.key = key
        self.serializer = serializer

    @property
    @abstractmethod
    def inc_key(self):
        """stats inc_value"""

    @classmethod
    @abstractmethod
    async def from_spider(cls, spider) -> "AbsQueue":
        """get queue instance from spider"""

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

    @abstractmethod
    async def len(self):
        """Return the length of the queue"""

    @abstractmethod
    async def push(self, request):
        """Push a request"""

    @abstractmethod
    async def pop(self, timeout=0):
        """Pop a request"""

    @abstractmethod
    async def clear(self):
        """Clear queue/stack"""
