# 代理系统 | Proxy System

AioScrapy提供了一个灵活的代理系统，允许您在爬取过程中使用HTTP代理。这对于避免IP封锁、提高爬取成功率和分散请求负载非常有用。
AioScrapy provides a flexible proxy system that allows you to use HTTP proxies during crawling. This is useful for avoiding IP blocks, improving crawling success rates, and distributing request loads.

## 代理系统架构 | Proxy System Architecture

AioScrapy的代理系统基于以下组件：
AioScrapy's proxy system is based on the following components:

1. **AbsProxy**：代理处理程序的抽象基类，定义了所有代理处理程序必须实现的接口
2. **RedisProxy**：基于Redis的代理处理程序实现，从Redis有序集合中获取代理
3. **自定义代理处理程序**：您可以创建自己的代理处理程序，实现特定的代理逻辑

1. **AbsProxy**: Abstract base class for proxy handlers, defining the interface that all proxy handlers must implement
2. **RedisProxy**: Redis-based proxy handler implementation, fetching proxies from a Redis sorted set
3. **Custom Proxy Handlers**: You can create your own proxy handlers to implement specific proxy logic

## 使用代理 | Using Proxies

AioScrapy提供了多种使用代理的方式：
AioScrapy provides multiple ways to use proxies:

### 方法1：直接在请求中设置代理 | Method 1: Set Proxy Directly in Request

这种方法适用于隧道代理或固定代理，您可以在请求中间件中直接设置代理：
This method is suitable for tunnel proxies or fixed proxies, where you can set the proxy directly in the request middleware:

```python
from aioscrapy import Request, Spider, logger

class DemoProxySpider(Spider):
    name = 'demo_proxy'
    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        "CLOSE_SPIDER_ON_IDLE": True,
    }
    
    start_urls = ['https://quotes.toscrape.com']
    
    @staticmethod
    async def process_request(request, spider):
        """请求中间件 | Request middleware"""
        # 添加代理，适用于隧道代理 | Add proxy, suitable for tunnel proxies
        request.meta['proxy'] = 'http://127.0.0.1:7890'
    
    async def parse(self, response):
        for quote in response.css('div.quote'):
            yield {
                'author': quote.xpath('span/small/text()').get(),
                'text': quote.css('span.text::text').get(),
            }
        
        next_page = response.css('li.next a::attr("href")').get()
        if next_page is not None:
            yield Request(f"https://quotes.toscrape.com{next_page}", callback=self.parse)
```

### 方法2：使用Redis代理池 | Method 2: Use Redis Proxy Pool

这种方法适用于使用Redis代理池的情况，您可以配置AioScrapy使用RedisProxy处理程序：
This method is suitable when using a Redis proxy pool, where you can configure AioScrapy to use the RedisProxy handler:

```python
from aioscrapy import Request, Spider, logger

class DemoRedisProxySpider(Spider):
    name = 'demo_redis_proxy'
    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        "CLOSE_SPIDER_ON_IDLE": True,
        
        # 代理配置 | Proxy configuration
        "USE_PROXY": True,  # 是否开启代理 | Whether to enable proxy
        "PROXY_HANDLER": 'aioscrapy.proxy.redis.RedisProxy',  # 代理处理程序类 | Proxy handler class
        "PROXY_QUEUE_ALIAS": 'proxy',  # Redis连接别名 | Redis connection alias
        "PROXY_KEY": 'proxies:universal',  # 代理的Redis键名 | Redis key for proxies
        "PROXY_MAX_COUNT": 10,  # 最多缓存的代理数量 | Maximum number of cached proxies
        "PROXY_MIN_COUNT": 1,  # 最少缓存的代理数量 | Minimum number of cached proxies
        
        # Redis连接设置 | Redis connection settings
        "REDIS_ARGS": {
            'proxy': {
                'url': 'redis://username:password@localhost:6379/2',
                'max_connections': 2,
                'timeout': None,
                'retry_on_timeout': True,
                'health_check_interval': 30,
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
            yield Request(f"https://quotes.toscrape.com{next_page}", callback=self.parse)
```

### 方法3：实现自定义代理处理程序 | Method 3: Implement Custom Proxy Handler

您可以创建自己的代理处理程序，实现特定的代理逻辑：
You can create your own proxy handler to implement specific proxy logic:

```python
from aioscrapy import Request, Spider, logger
from aioscrapy.proxy import AbsProxy

class MyProxy(AbsProxy):
    """自定义代理处理程序 | Custom proxy handler"""
    
    def __init__(self, settings):
        super().__init__(settings)
    
    @classmethod
    async def from_crawler(cls, crawler) -> "AbsProxy":
        settings = crawler.settings
        return cls(settings)
    
    async def get(self) -> str:
        """获取代理的逻辑 | Logic to get a proxy"""
        # 实现您自己的代理获取逻辑 | Implement your own proxy acquisition logic
        logger.warning("使用自定义代理逻辑 | Using custom proxy logic")
        return 'http://127.0.0.1:7890'

class DemoCustomProxySpider(Spider):
    name = 'demo_custom_proxy'
    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        "CLOSE_SPIDER_ON_IDLE": True,
        
        # 代理配置 | Proxy configuration
        "USE_PROXY": True,  # 是否开启代理 | Whether to enable proxy
        "PROXY_HANDLER": 'myproject.proxies.MyProxy',  # 自定义代理处理程序类 | Custom proxy handler class
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
            yield Request(f"https://quotes.toscrape.com{next_page}", callback=self.parse)
```

## 代理配置参数 | Proxy Configuration Parameters

AioScrapy提供了多个配置参数来控制代理系统的行为：
AioScrapy provides multiple configuration parameters to control the behavior of the proxy system:

| 参数 | Parameter | 类型 | Type | 默认值 | Default | 描述 | Description |
|-----------------|------------|-----------------|-------------------|
| `USE_PROXY` | boolean | `False` | 是否启用代理系统 | Whether to enable the proxy system |
| `PROXY_HANDLER` | string | - | 代理处理程序类的路径 | Path to the proxy handler class |
| `PROXY_MAX_COUNT` | integer | `16` | 最多缓存的代理数量 | Maximum number of cached proxies |
| `PROXY_MIN_COUNT` | integer | `1` | 最少缓存的代理数量 | Minimum number of cached proxies |
| `PROXY_ALLOW_STATUS_CODE` | list | `[404]` | 允许的HTTP状态码，即使使用代理也不会被移除 | Allowed HTTP status codes that won't cause proxy removal |
| `PROXY_QUEUE_ALIAS` | string | `'proxy'` | Redis连接别名（仅适用于RedisProxy） | Redis connection alias (only for RedisProxy) |
| `PROXY_KEY` | string | - | Redis键名（仅适用于RedisProxy） | Redis key (only for RedisProxy) |

## Redis代理池格式 | Redis Proxy Pool Format

当使用RedisProxy时，代理应存储在Redis的有序集合（ZSET）中，格式如下：
When using RedisProxy, proxies should be stored in a Redis sorted set (ZSET) in the following format:

- **键 | Key**: 由`PROXY_KEY`配置参数指定 | Specified by the `PROXY_KEY` configuration parameter
- **成员 | Members**: 代理字符串，格式为`host:port`或`scheme://host:port` | Proxy strings in the format `host:port` or `scheme://host:port`
- **分数 | Scores**: 代理的质量分数，范围从0到100，分数越高表示质量越好 | Quality scores for proxies, ranging from 0 to 100, with higher scores indicating better quality

例如，使用Redis CLI添加代理：
For example, adding proxies using the Redis CLI:

```
ZADD proxies:universal 100 127.0.0.1:8080
ZADD proxies:universal 90 http://example.com:8080
ZADD proxies:universal 80 https://proxy.example.com:3128
```

## 代理验证和管理 | Proxy Validation and Management

AioScrapy的代理系统会自动管理代理的使用和移除：
AioScrapy's proxy system automatically manages the use and removal of proxies:

1. **代理验证**：当请求返回非成功状态码（不在`PROXY_ALLOW_STATUS_CODE`列表中的状态码）或发生异常时，代理会被自动移除
2. **代理轮换**：代理会按顺序使用，确保负载均衡
3. **代理补充**：当缓存中的代理数量低于`PROXY_MIN_COUNT`时，系统会自动从Redis中获取更多代理

1. **Proxy Validation**: When a request returns a non-successful status code (not in the `PROXY_ALLOW_STATUS_CODE` list) or an exception occurs, the proxy is automatically removed
2. **Proxy Rotation**: Proxies are used in sequence to ensure load balancing
3. **Proxy Replenishment**: When the number of proxies in the cache falls below `PROXY_MIN_COUNT`, the system automatically fetches more proxies from Redis

## 最佳实践 | Best Practices

1. **使用代理池**：维护一个代理池，定期更新和验证代理
2. **设置合理的超时**：为使用代理的请求设置合理的超时时间
3. **处理代理失败**：实现重试机制，处理代理失败的情况
4. **监控代理使用**：监控代理的使用情况，及时发现和解决问题

1. **Use a Proxy Pool**: Maintain a pool of proxies, regularly updating and validating them
2. **Set Reasonable Timeouts**: Set reasonable timeout values for requests using proxies
3. **Handle Proxy Failures**: Implement retry mechanisms to handle proxy failures
4. **Monitor Proxy Usage**: Monitor proxy usage to quickly identify and resolve issues
