# 配置参考 | Settings Reference

AioScrapy提供了丰富的配置选项，允许您自定义爬虫的行为。本文档提供了所有可用设置的详细说明。
AioScrapy provides a rich set of configuration options that allow you to customize the behavior of your spiders. This document provides detailed descriptions of all available settings.

## 配置方式 | Configuration Methods

在AioScrapy中，有多种方式可以配置设置：
In AioScrapy, there are multiple ways to configure settings:

1. **项目设置文件**：在项目的`settings.py`文件中定义
2. **爬虫自定义设置**：在爬虫类的`custom_settings`属性中定义
3. **命令行参数**：使用`-s`参数在命令行中设置
4. **环境变量**：使用`AIOSCRAPY_`前缀的环境变量

1. **Project Settings File**: Defined in the project's `settings.py` file
2. **Spider Custom Settings**: Defined in the `custom_settings` attribute of the spider class
3. **Command Line Arguments**: Set using the `-s` parameter on the command line
4. **Environment Variables**: Using environment variables with the `AIOSCRAPY_` prefix

## 设置优先级 | Settings Priority

当同一设置在多个地方定义时，AioScrapy按照以下优先级使用它们（从高到低）：
When the same setting is defined in multiple places, AioScrapy uses them according to the following priority (from highest to lowest):

### 基本设置 | Basic Settings

| 设置 | Setting | 类型 | Type | 默认值 | Default | 描述 | Description |
|---------------|------------|-----------------|-------------------|
| `DOWNLOAD_TIMEOUT` | float | `180` | 下载超时时间（秒） | The download timeout (in seconds) |
| `DOWNLOAD_HANDLERS_TYPE` | string | `'aiohttp'` | 使用的下载处理程序类型 | The type of download handler to use |
| `DOWNLOAD_HANDLERS` | dict |  | URL方案到下载处理程序的映射 | Mapping of URL schemes to download handlers |
| `DOWNLOADER_MIDDLEWARES` | dict | `{}` | 启用的下载器中间件及其顺序 | Enabled downloader middlewares and their order |
| `SPIDER_MIDDLEWARES` | dict | `{}` | 启用的爬虫中间件及其顺序 | Enabled spider middlewares and their order |
| `ITEM_PIPELINES` | dict | `{}` | 启用的项目管道及其顺序 | Enabled item pipelines and their order |
| `EXTENSIONS` | dict | `{}` | 启用的扩展及其顺序 | Enabled extensions and their order |
| `USER_AGENT` | string | `'aioscrapy/VERSION'` | 默认的用户代理字符串 | Default user agent string |

### 并发设置 | Concurrent Requests Settings

| 设置 | Setting | 类型 | Type | 默认值 | Default | 描述 | Description |
|---------------|------------|-----------------|-------------------|
| `CONCURRENT_REQUESTS_PER_DOMAIN` | integer | `8` | 对同一域名的最大并发请求数 | The maximum number of concurrent requests to the same domain |
| `CONCURRENT_REQUESTS` | integer | `16` | 允许的并发请求数 | The maximum number of concurrent requests |
| `DOWNLOAD_DELAY` | float | `0` | 下载同一网站的连续页面之间的延迟（秒） | The delay between downloading consecutive pages from the same website (in seconds) |
| `RANDOMIZE_DOWNLOAD_DELAY` | boolean | `True` | 是否随机化下载延迟 | Whether to randomize the download delay |

### 调度器设置 | Scheduler Settings

| 设置 | Setting | 类型 | Type | 默认值 | Default | 描述 | Description |
|---------------|------------|-----------------|-------------------|
| `DUPEFILTER_CLASS` | string | `'aioscrapy.dupefilters.desk.RFPDupeFilter'` | 用于过滤重复请求的类 | Class used to filter duplicate requests |
| `SCHEDULER_QUEUE_CLASS` | string | `'aioscrapy.queue.memory.SpiderPriorityQueue'` | 用于存储请求的队列类 | Queue class used to store requests |
| `SCHEDULER_SERIALIZER` | string | `'aioscrapy.serializer.JsonSerializer'` | 用于序列化请求的序列化器 | Serializer used to serialize requests |

### 重试设置 | Retry Settings

| 设置 | Setting | 类型 | Type | 默认值 | Default | 描述 | Description |
|---------------|------------|-----------------|-------------------|
| `RETRY_ENABLED` | boolean | `True` | 是否启用重试中间件 | Whether to enable the retry middleware |
| `RETRY_TIMES` | integer | `2` | 最大重试次数 | Maximum number of retries |
| `RETRY_HTTP_CODES` | list | `[500, 502, 503, 504, 522, 524, 408, 429]` | 触发重试的HTTP状态码 | HTTP status codes that trigger retries |
| `RETRY_PRIORITY_ADJUST` | integer | `-1` | 重试请求的优先级调整 | Priority adjustment for retried requests |

### 爬虫关闭设置 | Spider Close Settings

| 设置 | Setting | 类型 | Type | 默认值 | Default | 描述 | Description |
|---------------|------------|-----------------|-------------------|
| `CLOSE_SPIDER_ON_IDLE` | boolean | `True` | 当爬虫空闲时是否关闭爬虫 | Whether to close the spider when it's idle |
| `CLOSESPIDER_TIMEOUT` | integer | `0` | 爬虫运行的秒数，超过后关闭爬虫（0表示不限制） | Number of seconds after which the spider will be closed (0 means no limit) |
| `CLOSESPIDER_ITEMCOUNT` | integer | `0` | 收集的项目数量，超过后关闭爬虫（0表示不限制） | Number of items scraped after which the spider will be closed (0 means no limit) |
| `CLOSESPIDER_PAGECOUNT` | integer | `0` | 爬取的页面数量，超过后关闭爬虫（0表示不限制） | Number of pages crawled after which the spider will be closed (0 means no limit) |
| `CLOSESPIDER_ERRORCOUNT` | integer | `0` | 发生的错误数量，超过后关闭爬虫（0表示不限制） | Number of errors after which the spider will be closed (0 means no limit) |

### 爬虫设置 | Spider Settings

| 设置 | Setting | 类型 | Type | 默认值 | Default | 描述 | Description |
|---------------|------------|-----------------|-------------------|
| `DEPTH_LIMIT` | integer | `0` | 爬取的最大深度（0表示不限制） | The maximum depth to crawl (0 means no limit) |
| `DEPTH_PRIORITY` | integer | `0` | 深度优先级调整 | Depth priority adjustment |

### 日志设置 | Logging Settings

| 设置 | Setting | 类型 | Type | 默认值 | Default | 描述 | Description |
|---------------|------------|-----------------|-------------------|
| `LOG_ENABLED` | boolean | `True` | 是否启用日志 | Whether to enable logging |
| `LOG_LEVEL` | string | `'DEBUG'` | 日志级别 | Logging level |
| `LOG_FILE` | string | `None` | 日志文件路径 | Log file path |
| `LOG_STDOUT` | boolean | `False` | 是否将日志输出到标准输出 | Whether to log to standard output |
| `LOG_ENCODING` | string | `'utf-8'` | 日志文件编码 | Log file encoding |
| `LOG_FORMAT` | string |  | 日志格式 | Log format |

### 数据库设置 | Database Settings
| 设置 | Setting | 类型 | Type | 默认值 | Default | 描述 | Description |
|---------------|------------|-----------------|-------------------|
| `REDIS_ARGS` | dict | `{}` | Redis连接参数 | Redis connection parameters |
| `MONGO_ARGS` | dict | `{}` | MongoDB连接参数 | MongoDB connection parameters |
| `MYSQL_ARGS` | dict | `{}` | MySQL连接参数 | MySQL connection parameters |
| `PG_ARGS` | dict | `{}` | PostgreSQL连接参数 | PostgreSQL connection parameters |

## 示例 | Examples
### 基本设置示例 | Basic Settings Example

```python
# settings.py
# 基本设置 | Basic settings

BOT_NAME = 'myproject'
SPIDER_MODULES = ['myproject.spiders']
NEWSPIDER_MODULE = 'myproject.spiders'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

# 并发和限制 | Concurrency and limits

CONCURRENT_REQUESTS = 32
CONCURRENT_REQUESTS_PER_DOMAIN = 16
DOWNLOAD_DELAY = 0.5
RANDOMIZE_DOWNLOAD_DELAY = True
DEPTH_LIMIT = 3  # 限制爬取深度为3 | Limit crawling depth to 3

# 下载处理程序 | Download handlers

DOWNLOAD_HANDLERS_TYPE = "httpx"

# 调度器设置 | Scheduler settings

DUPEFILTER_CLASS = 'aioscrapy.dupefilters.redis.RedisBloomDupeFilter'  # 使用Redis布隆过滤器 | Use Redis bloom filter
SCHEDULER_QUEUE_CLASS = 'aioscrapy.queue.redis.SpiderPriorityQueue'  # 使用Redis优先级队列 | Use Redis priority queue
SCHEDULER_SERIALIZER = 'aioscrapy.serializer.JsonSerializer'  # 使用JSON序列化器 | Use JSON serializer

# 重试设置 | Retry settings

RETRY_ENABLED = True
RETRY_TIMES = 3  # 最多重试3次 | Maximum 3 retries
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429]  # 触发重试的HTTP状态码 | HTTP status codes that trigger retries
RETRY_PRIORITY_ADJUST = -1  # 重试请求的优先级降低 | Lower priority for retried requests

# 爬虫关闭设置 | Spider close settings

CLOSESPIDER_TIMEOUT = 3600  # 爬虫最多运行1小时 | Spider runs for maximum 1 hour
CLOSESPIDER_ITEMCOUNT = 10000  # 收集10000个项目后关闭 | Close after collecting 10000 items
CLOSESPIDER_PAGECOUNT = 0  # 不限制页面数量 | No limit on page count
CLOSESPIDER_ERRORCOUNT = 50  # 发生50个错误后关闭 | Close after 50 errors

# 中间件 | Middlewares

DOWNLOADER_MIDDLEWARES = {
    'myproject.middlewares.MyDownloaderMiddleware': 543,
}

SPIDER_MIDDLEWARES = {
    'myproject.middlewares.MySpiderMiddleware': 543,
}

# 管道 | Pipelines

ITEM_PIPELINES = {
    'myproject.pipelines.MyPipeline': 300,
}

# 日志设置 | Logging settings

LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/aioscrapy.log'
```

### 数据库设置示例 | Database Settings Example

```python
# MongoDB设置 | MongoDB settings

MONGO_ARGS = {
    'default': {
        'host': 'localhost',
        'port': 27017,
        'username': 'user',
        'password': 'password',
        'database': 'aioscrapy'
    }
}

# MySQL设置 | MySQL settings

MYSQL_ARGS = {
    'default': {
        'host': 'localhost',
        'port': 3306,
        'user': 'user',
        'password': 'password',
        'database': 'aioscrapy',
        'charset': 'utf8mb4'
    }
}

# Redis设置 | Redis settings

REDIS_ARGS = {
    'default': {
        'host': 'localhost',
        'port': 6379,
        'password': None,
        'db': 0
    }
}
```
