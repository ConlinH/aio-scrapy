from abc import ABCMeta, abstractmethod
from typing import Optional, Any, List

import aioscrapy
from aioscrapy.serializer import AbsSerializer
from aioscrapy.utils.reqser import request_from_dict


class AbsQueue(metaclass=ABCMeta):
    """
    Per-spider base queue class.
    每个爬虫的基础队列类。

    This abstract class defines the interface for request queues used by spiders.
    It provides methods for pushing, popping, and managing requests in a queue.
    此抽象类定义了爬虫使用的请求队列的接口。
    它提供了推送、弹出和管理队列中请求的方法。
    """

    def __init__(
            self,
            container: Any,
            spider: Optional[aioscrapy.Spider] = None,
            key: Optional[str] = None,
            serializer: Optional[AbsSerializer] = None
    ) -> None:
        """
        Initialize per-spider queue.
        初始化每个爬虫的队列。

        Args:
            container: The underlying data structure to store the queue.
                      存储队列的底层数据结构。
            spider: The spider instance that will use this queue.
                   将使用此队列的爬虫实例。
            key: Optional key to identify this queue.
                可选的键，用于标识此队列。
            serializer: Optional serializer for encoding/decoding requests.
                       可选的序列化器，用于编码/解码请求。
        """
        self.container = container  # The underlying data structure
                                   # 底层数据结构
        self.spider = spider  # Associated spider
                             # 关联的爬虫
        self.key = key  # Queue identifier
                        # 队列标识符
        self.serializer = serializer  # For serializing requests
                                     # 用于序列化请求

    @property
    @abstractmethod
    def inc_key(self) -> str:
        """
        Get the key used for incrementing stats.
        获取用于增加统计信息的键。

        This property should return a string key that will be used with
        the stats collector's inc_value method to track queue operations.
        此属性应返回一个字符串键，该键将与统计收集器的inc_value方法一起使用，
        以跟踪队列操作。

        Returns:
            str: The stats key for this queue.
                此队列的统计键。
        """

    @classmethod
    @abstractmethod
    async def from_spider(cls, spider: aioscrapy.Spider) -> "AbsQueue":
        """
        Create a queue instance for a spider.
        为爬虫创建队列实例。

        This factory method creates a new queue instance configured
        for the given spider.
        此工厂方法创建一个为给定爬虫配置的新队列实例。

        Args:
            spider: The spider that will use the queue.
                   将使用队列的爬虫。

        Returns:
            AbsQueue: A new queue instance.
                     一个新的队列实例。
        """

    def _encode_request(self, request: aioscrapy.Request) -> Any:
        """
        Encode a request object for storage.
        编码请求对象以进行存储。

        This method converts a Request object to a serialized form that can
        be stored in the queue's container.
        此方法将Request对象转换为可以存储在队列容器中的序列化形式。

        Args:
            request: The Request object to encode.
                    要编码的Request对象。

        Returns:
            Any: The serialized form of the request.
                请求的序列化形式。
        """
        obj = request.to_dict(spider=self.spider)
        return self.serializer.dumps(obj)

    async def _decode_request(self, encoded_request: Any) -> aioscrapy.Request:
        """
        Decode a previously encoded request.
        解码先前编码的请求。

        This method converts a serialized request back into a Request object.
        此方法将序列化的请求转换回Request对象。

        Args:
            encoded_request: The serialized request to decode.
                           要解码的序列化请求。

        Returns:
            Request: The reconstructed Request object.
                    重建的Request对象。
        """
        obj = self.serializer.loads(encoded_request)
        return await request_from_dict(obj, spider=self.spider)

    def __len__(self) -> None:
        """
        Return the length of the queue (synchronous version).
        返回队列的长度（同步版本）。

        This method is overridden to prevent synchronous access to the queue length.
        Use the async len() method instead.
        此方法被重写以防止同步访问队列长度。
        请改用异步len()方法。

        Raises:
            Exception: Always raises an exception to remind users to use the async len() method.
                      始终引发异常，以提醒用户使用异步len()方法。
        """
        raise Exception('please use len()')

    @abstractmethod
    async def len(self) -> int:
        """
        Return the length of the queue (asynchronous version).
        返回队列的长度（异步版本）。

        This method should return the number of requests currently in the queue.
        此方法应返回当前队列中的请求数量。

        Returns:
            int: The number of requests in the queue.
                队列中的请求数量。
        """

    @abstractmethod
    async def push(self, request: aioscrapy.Request) -> None:
        """
        Push a request to the queue.
        将请求推送到队列。

        This method adds a single request to the queue.
        此方法将单个请求添加到队列中。

        Args:
            request: The request to add to the queue.
                    要添加到队列的请求。
        """

    @abstractmethod
    async def push_batch(self, requests: List[aioscrapy.Request]) -> None:
        """
        Push multiple requests to the queue.
        将多个请求推送到队列。

        This method adds multiple requests to the queue at once,
        which may be more efficient than calling push() multiple times.
        此方法一次将多个请求添加到队列中，
        这可能比多次调用push()更有效率。

        Args:
            requests: A list of requests to add to the queue.
                     要添加到队列的请求列表。
        """

    @abstractmethod
    async def pop(self, timeout: int = 0) -> Optional[aioscrapy.Request]:
        """
        Pop a request from the queue.
        从队列中弹出请求。

        This method removes and returns a request from the queue.
        If the queue is empty, it may wait up to timeout seconds
        before returning None.
        此方法从队列中移除并返回一个请求。
        如果队列为空，它可能会等待最多timeout秒，
        然后返回None。

        Args:
            timeout: Maximum time to wait for a request, in seconds.
                    等待请求的最长时间，以秒为单位。

        Returns:
            Optional[Request]: The next request from the queue, or None if
                              the queue is empty or the timeout expires.
                              队列中的下一个请求，如果队列为空或超时，则为None。
        """

    @abstractmethod
    async def clear(self) -> None:
        """
        Clear all requests from the queue.
        清除队列中的所有请求。

        This method removes all pending requests from the queue,
        effectively resetting it to an empty state.
        此方法从队列中删除所有待处理的请求，
        有效地将其重置为空状态。
        """
