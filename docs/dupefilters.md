# 请求过滤器 | Request Filters

请求过滤器（也称为重复过滤器或指纹过滤器）是AioScrapy中用于避免多次爬取相同URL的组件。它们通过跟踪请求的指纹来实现这一功能。
Request filters (also known as duplicate filters or fingerprint filters) are components in AioScrapy used to avoid crawling the same URL multiple times. They achieve this by tracking request fingerprints.

## 过滤器架构 | Filter Architecture

AioScrapy的请求过滤器系统基于一个抽象基类`DupeFilterBase`，所有具体的过滤器实现都必须继承自这个基类。过滤器系统支持多种存储后端，包括内存、磁盘和Redis。
AioScrapy's request filter system is based on an abstract base class `DupeFilterBase`, and all concrete filter implementations must inherit from this base class. The filter system supports multiple storage backends, including memory, disk, and Redis.

## 过滤器类型 | Filter Types

AioScrapy提供了多种类型的请求过滤器，每种都有其特点和适用场景：
AioScrapy provides multiple types of request filters, each with its own characteristics and use cases:

##### 磁盘过滤器 | Disk Filters

磁盘过滤器将请求指纹存储在磁盘上，适用于需要持久化的场景。
Disk filters store request fingerprints on disk, suitable for scenarios requiring persistence.

##### DiskRFPDupeFilter

基本的磁盘请求指纹过滤器，将请求指纹存储在磁盘文件中。
Basic disk request fingerprint filter, storing request fingerprints in a disk file.

```python
# 在settings.py中设置 | Set in settings.py

DUPEFILTER_CLASS = 'aioscrapy.dupefilters.disk.DiskRFPDupeFilter'

# 作业目录，用于存储请求指纹文件 | Job directory, used to store request fingerprint files

JOBDIR = './job_dir'
```

### Redis过滤器 | Redis Filters

Redis过滤器将请求指纹存储在Redis数据库中，适用于分布式爬取和需要跨进程共享过滤器的场景。
Redis filters store request fingerprints in a Redis database, suitable for distributed crawling and scenarios requiring cross-process filter sharing.

##### RedisRFPDupeFilter

基本的Redis请求指纹过滤器，使用Redis SET存储请求指纹。
Basic Redis request fingerprint filter, using Redis SET to store request fingerprints.

##### RedisBloomDupeFilter

基于布隆过滤器的Redis请求指纹过滤器，使用Redis位图实现布隆过滤器来存储请求指纹。这种过滤器比简单的基于SET的过滤器更节省空间，但有小概率出现假阳性。
Bloom filter-based Redis request fingerprint filter, using Redis bitmaps to implement a Bloom filter for storing request fingerprints. This filter is more space-efficient than the simple SET-based filter, but has a small probability of false positives.

##### ExRedisRFPDupeFilter

加强版的过滤器添加了在请求失败时从过滤器中移除指纹的功能，这对于重试失败的请求很有用。
Extended filters add the ability to remove fingerprints from the filter when requests fail, which is useful for retrying failed requests.

加强版的Redis SET基于的请求指纹过滤器，具有指纹移除功能。
Extended Redis SET-based request fingerprint filter with fingerprint removal capability.

##### ExRedisBloomDupeFilter

加强版的基于布隆过滤器的Redis请求指纹过滤器，具有临时SET存储和指纹移除功能。
Extended Bloom filter-based Redis request fingerprint filter with temporary SET storage and fingerprint removal capability.


```python

# Redis连接设置 | Redis connection settings
REDIS_ARGS = {
    'queue': {
        'url': 'redis://localhost:6379/0',
    }
}

# 在settings.py中设置 | Set in settings.py

# RedisRFPDupeFilter
DUPEFILTER_CLASS = 'aioscrapy.dupefilters.redis.RedisRFPDupeFilter'
JOBDIR = './job_dir'    # 作业目录，用于存储请求指纹文件 | Job directory, used to store request fingerprint files

# ExRedisRFPDupeFilter
DUPEFILTER_CLASS = 'aioscrapy.dupefilters.redis.ExRedisRFPDupeFilter'

# RedisBloomDupeFilter
DUPEFILTER_CLASS = 'aioscrapy.dupefilters.redis.RedisBloomDupeFilter'
BLOOMFILTER_BIT = 30  # 位数，影响布隆过滤器的大小 | Number of bits, affects the size of the Bloom filter
BLOOMFILTER_HASH_NUMBER = 6  # 哈希函数数量，影响假阳性率 | Number of hash functions, affects the false positive rate

# ExRedisBloomDupeFilter
DUPEFILTER_CLASS = 'aioscrapy.dupefilters.redis.ExRedisBloomDupeFilter'
DUPEFILTER_SET_KEY_TTL = 180    # 临时SET的TTL（秒） | TTL for the temporary SET (seconds)
BLOOMFILTER_BIT = 30  # 位数，影响布隆过滤器的大小 | Number of bits, affects the size of the Bloom filter
BLOOMFILTER_HASH_NUMBER = 6  # 哈希函数数量，影响假阳性率 | Number of hash functions, affects the false positive rate
```


## 自定义过滤器 | Custom Filters

您可以创建自己的请求过滤器，只需继承`DupeFilterBase`类并实现必要的方法：
You can create your own request filter by inheriting from the `DupeFilterBase` class and implementing the necessary methods:

```python
from aioscrapy.dupefilters import DupeFilterBase
from aioscrapy import Request, Spider

class MyCustomDupeFilter(DupeFilterBase):

    # 初始化过滤器 | Initialize the filter
    def __init__(self, debug=False, info=False):
        self.fingerprints = set()
        self.debug = debug
        self.info = info
        self.logdupes = True

    # 从爬虫创建过滤器 | Create a filter from a crawler
    @classmethod
    def from_crawler(cls, crawler):
        debug = crawler.settings.getbool('DUPEFILTER_DEBUG', False)
        info = crawler.settings.getbool('DUPEFILTER_INFO', False)
        return cls(debug, info)

    # 检查请求是否已经被看到过 | Check if the request has been seen before
    async def request_seen(self, request: Request) -> bool:
        if request.fingerprint in self.fingerprints:
            return True
        self.fingerprints.add(request.fingerprint)
        return False

    # 关闭过滤器 | Close the filter
    async def close(self, reason=''):
        self.fingerprints.clear()

    # 处理请求完成状态 | Handle request completion status
    async def done(self, request, done_type):
        # 如果请求失败，从过滤器中移除指纹 | If the request fails, remove the fingerprint from the filter
        if done_type == "request_err" or done_type == "parse_err":
            self.fingerprints.discard(request.fingerprint)
```

然后在设置中注册您的过滤器：
Then register your filter in the settings:

```python
# 在settings.py中设置 | Set in settings.py
DUPEFILTER_CLASS = 'myproject.dupefilters.MyCustomDupeFilter'
```

## 过滤器配置 | Filter Configuration
### 基本配置 | Basic Configuration

```python
# 过滤器类 | Filter class
DUPEFILTER_CLASS = 'aioscrapy.dupefilters.disk.DiskRFPDupeFilter'

# 是否记录被过滤的请求（DEBUG级别） | Whether to log filtered requests (DEBUG level)
DUPEFILTER_DEBUG = False

# 是否记录重复请求（INFO级别） | Whether to log duplicate requests (INFO level)
DUPEFILTER_INFO = False

# 作业目录，用于磁盘过滤器 | Job directory, used for disk filters
JOBDIR = './job_dir'
```

## 过滤器使用示例 | Filter Usage Examples
### 基本使用 | Basic Usage

```python
from aioscrapy import Spider, Request

class MySpider(Spider):
    name = 'myspider'
    start_urls = ['https://example.com']
    
    custom_settings = {
        'DUPEFILTER_CLASS': 'aioscrapy.dupefilters.disk.DiskRFPDupeFilter',
        'JOBDIR': './job_dir',
    }
    
    # 处理响应 | Process the response
    async def parse(self, response):
        yield {'url': response.url, 'title': response.css('title::text').get()}
        
        # 添加新请求，过滤器会自动过滤重复的URL | Add new requests, the filter will automatically filter duplicate URLs
        for href in response.css('a::attr(href)'):
            yield Request(response.urljoin(href), callback=self.parse)

if __name__ == '__main__':
    MySpider.start()
```

### 使用Redis布隆过滤器进行分布式爬取 | Using Redis Bloom Filter for Distributed Crawling

```python
from aioscrapy import Spider, Request

class DistributedSpider(Spider):
    name = 'distributed'
    start_urls = ['https://example.com']
    
    custom_settings = {
        'DUPEFILTER_CLASS': 'aioscrapy.dupefilters.redis.RedisBloomDupeFilter',
        'BLOOMFILTER_BIT': 30,
        'BLOOMFILTER_HASH_NUMBER': 6,
        'REDIS_ARGS': {
            'queue': {
                'url': 'redis://localhost:6379/0',
            }
        },
    }
    
    # 处理响应 | Process the response
    async def parse(self, response):
        yield {'url': response.url, 'title': response.css('title::text').get()}
        
        # 添加新请求，过滤器会自动过滤重复的URL | Add new requests, the filter will automatically filter duplicate URLs
        for href in response.css('a::attr(href)'):
            yield Request(response.urljoin(href), callback=self.parse)


if __name__ == '__main__':
    DistributedSpider.start()
```

### 使用扩展过滤器重试失败的请求 | Using Extended Filter to Retry Failed Requests

```python
from aioscrapy import Spider, Request

class RetrySpider(Spider):
    name = 'retry'
    start_urls = ['https://example.com']
    
    custom_settings = {
        'DUPEFILTER_CLASS': 'aioscrapy.dupefilters.redis.ExRedisBloomDupeFilter',
        'BLOOMFILTER_BIT': 30,
        'BLOOMFILTER_HASH_NUMBER': 6,
        'DUPEFILTER_SET_KEY_TTL': 180,
        'REDIS_ARGS': {
            'queue': {
                'url': 'redis://localhost:6379/0',
            }
        },
    }
    
    # 处理响应 | Process the response
    async def parse(self, response):
        yield {'url': response.url, 'title': response.css('title::text').get()}
        
        # 添加新请求，如果请求失败，过滤器会自动移除指纹，允许重试 | Add new requests, if the request fails, the filter will automatically remove the fingerprint, allowing retry
        for href in response.css('a::attr(href)'):
            yield Request(response.urljoin(href), callback=self.parse)

if __name__ == '__main__':
    RetrySpider.start()
```
