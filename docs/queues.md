# 队列 | Queues

队列是AioScrapy中用于存储和管理请求的组件。它们负责存储待处理的请求，并按照一定的顺序提供给下载器。</br>
Queues are components in AioScrapy used to store and manage requests. They are responsible for storing pending requests and providing them to the downloader in a certain order.

## 队列架构 | Queue Architecture

AioScrapy的队列系统基于一个抽象基类`AbsQueue`，所有具体的队列实现都必须继承自这个基类。队列系统支持多种存储后端，包括内存、磁盘和Redis。</br>
AioScrapy's queue system is based on an abstract base class `AbsQueue`, and all concrete queue implementations must inherit from this base class. The queue system supports multiple storage backends, including memory, disk, and Redis.

## 队列类型 | Queue Types

AioScrapy提供了多种类型的队列，每种都有其特点和适用场景：</br>
AioScrapy provides multiple types of queues, each with its own characteristics and use cases:

### 内存队列 | Memory Queues

内存队列将请求存储在内存中，适用于单机爬取和小规模爬取任务。</br>
Memory queues store requests in memory, suitable for single-machine crawling and small-scale crawling tasks.

###### SpiderQueue

基本的内存队列，按照先进先出（FIFO）的顺序处理请求。</br>
Basic memory queue, processing requests in first-in-first-out (FIFO) order.

###### SpiderStack

后进先出（LIFO）内存队列，最后添加的请求会先被处理。这种队列适用于深度优先爬取。</br>
Last-in-first-out (LIFO) memory queue, where the most recently added requests are processed first. This type of queue is suitable for depth-first crawling.

###### PriorityQueue

优先级内存队列，根据请求的优先级处理请求。优先级高的请求会先被处理。</br>
Priority memory queue, processing requests based on their priority. Requests with higher priority will be processed first.

```python
# 在settings.py中设置 | Set in settings.py
SCHEDULER_QUEUE_CLASS = 'aioscrapy.queue.memory.SpiderPriorityQueue'
# SCHEDULER_QUEUE_CLASS = 'aioscrapy.queue.memory.LifoMemoryQueue'
# SCHEDULER_QUEUE_CLASS = 'aioscrapy.queue.memory.SpiderStack'
```

### Redis队列 | Redis Queues

Redis队列将请求存储在Redis数据库中，适用于分布式爬取和需要跨进程共享队列的场景。</br>
Redis queues store requests in a Redis database, suitable for distributed crawling and scenarios requiring cross-process queue sharing.

###### SpiderQueue

基本的Redis队列，按照先进先出（FIFO）的顺序处理请求。</br>
Basic Redis queue, processing requests in first-in-first-out (FIFO) order.

###### SpiderStack

后进先出（LIFO）Redis队列，最后添加的请求会先被处理。</br>
Last-in-first-out (LIFO) Redis queue, where the most recently added requests are processed first.

###### SpiderPriorityQueue

优先级Redis队列，根据请求的优先级处理请求。</br>
Priority Redis queue, processing requests based on their priority.

```python

# Redis连接设置 | Redis connection settings
REDIS_ARGS = {
    'queue': {
        'url': 'redis://localhost:6379/0',
    }
}

# 在settings.py中设置 | Set in settings.py
SCHEDULER_QUEUE_CLASS = 'aioscrapy.queue.redis.SpiderPriorityQueue'
# SCHEDULER_QUEUE_CLASS = 'aioscrapy.queue.redis.SpiderQueue'
# SCHEDULER_QUEUE_CLASS = 'aioscrapy.queue.redis.SpiderStack'
```

### RabbitMQ队列 | RabbitMQ Queues

RabbitMQ队列将请求存储在RabbitMQ消息队列中，适用于分布式爬取和需要可靠消息传递的场景。RabbitMQ提供了强大的消息路由、持久化和负载均衡功能。</br>
RabbitMQ queues store requests in a RabbitMQ message queue, suitable for distributed crawling and scenarios requiring reliable message delivery. RabbitMQ provides powerful message routing, persistence, and load balancing capabilities.

##### RabbitMqPriorityQueue

基于RabbitMQ的优先级队列，根据请求的优先级处理请求。</br>
RabbitMQ-based priority queue, processing requests based on their priority.

```python

# RabbitMQ连接设置 | RabbitMQ connection settings
RABBITMQ_ARGS = {
    'queue': {
        'url': 'amqp://guest:guest@localhost:5672/',
        'connection_max_size': 2,  # 最大连接数 | Maximum connections
        'channel_max_size': 10,    # 最大通道数 | Maximum channels
    }
}

# 在settings.py中设置 | Set in settings.py
SCHEDULER_QUEUE_CLASS = 'aioscrapy.queue.rabbitmq.RabbitMqPriorityQueue'
```

## 自定义队列 | Custom Queues

您可以创建自己的队列，只需继承`AbsQueue`类并实现必要的方法：</br>
You can create your own queue by inheriting from the `AbsQueue` class and implementing the necessary methods:

```python
from aioscrapy.queue import AbsQueue
from aioscrapy import Request

class MyCustomQueue(AbsQueue):
    
    # 初始化队列 | Initialize the queue
    def __init__(self, *args, **kwargs):
        self.queue = []

    # 将请求添加到队列 | Add the request to the queue
    async def push(self, request: Request) -> None:
        self.queue.append(request)

    # 从队列中获取一个请求 | Get a request from the queue
    async def pop(self) -> Request:
        if self.queue:
            return self.queue.pop(0)
        return None

    # 清空队列 | Clear the queue
    async def clear(self) -> None:
        self.queue.clear()

    # 获取队列大小 | Get the queue size
    async def qsize(self) -> int:
        return len(self.queue)

    # 从爬虫创建队列 | Create a queue from a spider
    @classmethod
    async def from_spider(cls, spider):
        return cls()
```

然后在设置中注册您的队列：</br>
Then register your queue in the settings:

```python
# 在settings.py中设置 | Set in settings.py

SCHEDULER_QUEUE_CLASS = 'myproject.queues.MyCustomQueue'
```

## 队列配置 | Queue Configuration
### 基本配置 | Basic Configuration

```python
# 队列类 | Queue class
SCHEDULER_QUEUE_CLASS = 'aioscrapy.queue.memory.PriorityQueue'

# 启动时是否清空队列 | Whether to clear the queue on startup
SCHEDULER_FLUSH_ON_START = False

# 队列别名，用于Redis队列 | Queue alias, used for Redis queues
SCHEDULER_QUEUE_ALIAS = 'queue'

# 队列键模板，用于Redis队列 | Queue key template, used for Redis queues
SCHEDULER_QUEUE_KEY = '%(spider)s:requests'

# 序列化器，用于将请求序列化为存储格式 | Serializer, used to serialize requests to storage format
SCHEDULER_SERIALIZER = 'aioscrapy.serializer.JsonSerializer'
# 序列化器，使用PickleSerializer以支持复杂对象 | Serializer, recommend using PickleSerializer to support complex objects
# SCHEDULER_SERIALIZER = 'aioscrapy.serializer.PickleSerializer'
```

## 队列使用示例 | Queue Usage Examples
### 基本使用 | Basic Usage

```python
from aioscrapy import Spider, Request

class MySpider(Spider):
    name = 'myspider'
    start_urls = ['https://example.com']

    custom_settings = {
        'SCHEDULER_QUEUE_CLASS': 'aioscrapy.queue.memory.SpiderPriorityQueue',
    }

    # 处理响应 | Process the response
    async def parse(self, response):
        yield {'url': response.url, 'title': response.css('title::text').get()}

        # 添加新请求到队列 | Add new requests to the queue
        for href in response.css('a::attr(href)'):
            yield Request(response.urljoin(href), callback=self.parse)
```

### 使用Redis队列进行分布式爬取 | Using Redis Queue for Distributed Crawling

```python
from aioscrapy import Spider, Request

class DistributedSpider(Spider):
    name = 'distributed'
    start_urls = ['https://example.com']

    custom_settings = {
        'SCHEDULER_QUEUE_CLASS': 'aioscrapy.queue.redis.SpiderPriorityQueue',
        'REDIS_ARGS': {
            'queue': {
                'url': 'redis://localhost:6379/0',
            }
        },
        'SCHEDULER_FLUSH_ON_START': False,  # 不清空队列，允许多个爬虫实例共享队列
                                           # Don't clear the queue, allowing multiple spider instances to share the queue
    }

    # 处理响应 | Process the response
    async def parse(self, response):
        yield {'url': response.url, 'title': response.css('title::text').get()}

        # 添加新请求到队列 | Add new requests to the queue
        for href in response.css('a::attr(href)'):
            yield Request(response.urljoin(href), callback=self.parse)
```

### 使用RabbitMQ队列进行分布式爬取 | Using RabbitMQ Queue for Distributed Crawling

```python
from aioscrapy import Spider, logger

class RabbitMQSpider(Spider):
    name = 'rabbitmq_spider'
    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        'CONCURRENT_REQUESTS': 2,
        "CLOSE_SPIDER_ON_IDLE": False,

        # 使用RabbitMQ队列 | Use RabbitMQ queue
        'SCHEDULER_QUEUE_CLASS': 'aioscrapy.queue.rabbitmq.SpiderPriorityQueue',

        # 使用PickleSerializer序列化器以支持复杂对象 | Use PickleSerializer to support complex objects
        'SCHEDULER_SERIALIZER': 'aioscrapy.serializer.PickleSerializer',

        # RabbitMQ连接设置 | RabbitMQ connection settings
        'RABBITMQ_ARGS': {
            'queue': {
                'url': "amqp://guest:guest@localhost:5672/",
                'connection_max_size': 2,
                'channel_max_size': 10,
            }
        }
    }

    start_urls = ['https://quotes.toscrape.com']

    async def parse(self, response):
        for quote in response.css('div.quote'):
            yield {
                'author': quote.xpath('span/small/text()').get(),
                'text': quote.css('span.text::text').get(),
            }

        next_page = response.css('li.next a::attr("href")').get()
        if next_page is not None:
            yield response.follow(next_page, self.parse)

    async def process_item(self, item):
        logger.info(item)
```
