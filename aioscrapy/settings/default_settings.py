"""
Default settings for aioscrapy.
aioscrapy的默认设置。

This module contains the default values for all settings used by aioscrapy.
It defines configuration for downloaders, middlewares, extensions, and other
components of the crawling system.
此模块包含aioscrapy使用的所有设置的默认值。
它为下载器、中间件、扩展和爬取系统的其他组件定义配置。

For more information about these settings you can read the settings
documentation in docs/topics/settings.rst
有关这些设置的更多信息，您可以阅读docs/topics/settings.rst中的设置文档。

Aioscrapy developers, if you add a setting here remember to:
Aioscrapy开发人员，如果您在此处添加设置，请记住：

* add it in alphabetical order
  按字母顺序添加
* group similar settings without leaving blank lines
  分组类似设置，不留空行
* add its documentation to the available settings documentation
  将其文档添加到可用的设置文档中
  (docs/topics/settings.rst)
"""

import sys
from os.path import join, abspath, dirname

# Auto throttle settings
# 自动限流设置

# Whether to enable the AutoThrottle extension
# 是否启用AutoThrottle扩展
AUTOTHROTTLE_ENABLED = False

# Whether to enable AutoThrottle debugging (displays adjustment decisions)
# 是否启用AutoThrottle调试（显示调整决策）
AUTOTHROTTLE_DEBUG = False

# Maximum delay in seconds for throttled requests
# 限流请求的最大延迟（秒）
AUTOTHROTTLE_MAX_DELAY = 60.0

# Initial delay in seconds for throttled requests
# 限流请求的初始延迟（秒）
AUTOTHROTTLE_START_DELAY = 5.0

# Target average number of concurrent requests per domain
# 每个域的目标平均并发请求数
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

# Default bot name used for the User-Agent header and logging
# 用于User-Agent头和日志记录的默认机器人名称
BOT_NAME = 'aioscrapybot'

# Close spider settings
# 关闭爬虫设置

# Number of seconds after which the spider will be closed
# 爬虫将被关闭的秒数（0表示禁用）
CLOSESPIDER_TIMEOUT = 0

# Number of pages after which the spider will be closed
# 爬虫将被关闭的页面数（0表示禁用）
CLOSESPIDER_PAGECOUNT = 0

# Number of items after which the spider will be closed
# 爬虫将被关闭的项目数（0表示禁用）
CLOSESPIDER_ITEMCOUNT = 0

# Number of errors after which the spider will be closed
# 爬虫将被关闭的错误数（0表示禁用）
CLOSESPIDER_ERRORCOUNT = 0

# Module where custom commands are defined
# 定义自定义命令的模块
COMMANDS_MODULE = ''

# Number of concurrent parsers for processing responses
# 用于处理响应的并发解析器数量
CONCURRENT_PARSER = 1

# Concurrency settings
# 并发设置

# Maximum number of concurrent requests across all domains
# 所有域的最大并发请求数
CONCURRENT_REQUESTS = 16

# Maximum number of concurrent requests per domain
# 每个域的最大并发请求数
CONCURRENT_REQUESTS_PER_DOMAIN = 8

# Maximum number of concurrent requests per IP address (0 means unlimited)
# 每个IP地址的最大并发请求数（0表示无限制）
CONCURRENT_REQUESTS_PER_IP = 0

# Default headers used for all requests
# 用于所有请求的默认头
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en',
}

# Depth settings
# 深度设置

# Maximum depth to crawl (0 means no limit)
# 爬取的最大深度（0表示无限制）
DEPTH_LIMIT = 0

# Whether to log verbose depth stats
# 是否记录详细的深度统计信息
DEPTH_STATS_VERBOSE = False

# Priority adjustment based on depth (-1 means decrease priority with depth)
# 基于深度的优先级调整（-1表示随着深度增加而降低优先级）
DEPTH_PRIORITY = 0

# Download settings
# 下载设置

# Delay in seconds between consecutive requests to the same domain
# 对同一域的连续请求之间的延迟（秒）
DOWNLOAD_DELAY = 0

# Custom download handlers for different schemes (http, https, etc.)
# 不同协议（http、https等）的自定义下载处理程序
DOWNLOAD_HANDLERS = {}

# Base download handlers for http and https
# http和https的基本下载处理程序
DOWNLOAD_HANDLERS_BASE = {
    'http': 'aioscrapy.core.downloader.handlers.aiohttp.AioHttpDownloadHandler',
    'https': 'aioscrapy.core.downloader.handlers.aiohttp.AioHttpDownloadHandler',
}

# Mapping of different HTTP client libraries to their download handlers
# 不同HTTP客户端库到其下载处理程序的映射
DOWNLOAD_HANDLERS_MAP = {
    # aiohttp handlers (default)
    # aiohttp处理程序（默认）
    'aiohttp': DOWNLOAD_HANDLERS_BASE,

    # httpx handlers
    # httpx处理程序
    'httpx': {
        'http': 'aioscrapy.core.downloader.handlers.httpx.HttpxDownloadHandler',
        'https': 'aioscrapy.core.downloader.handlers.httpx.HttpxDownloadHandler',
    },

    # requests handlers
    # requests处理程序
    'requests': {
        'http': 'aioscrapy.core.downloader.handlers.requests.RequestsDownloadHandler',
        'https': 'aioscrapy.core.downloader.handlers.requests.RequestsDownloadHandler',
    },

    # pyhttpx handlers
    # pyhttpx处理程序
    'pyhttpx': {
        'http': 'aioscrapy.core.downloader.handlers.pyhttpx.PyhttpxDownloadHandler',
        'https': 'aioscrapy.core.downloader.handlers.pyhttpx.PyhttpxDownloadHandler',
    },

    # playwright handlers (for JavaScript rendering)
    # playwright处理程序（用于JavaScript渲染）
    'playwright': {
        'http': 'aioscrapy.core.downloader.handlers.webdriver.playwright.PlaywrightHandler',
        'https': 'aioscrapy.core.downloader.handlers.webdriver.playwright.PlaywrightHandler',
    },

    # DrissionPageHandler handlers (for JavaScript rendering)
    # DrissionPageHandler处理程序（用于JavaScript渲染）
    'dp': {
        'http': 'aioscrapy.core.downloader.handlers.webdriver.drissionpage.DrissionPageHandler',
        'https': 'aioscrapy.core.downloader.handlers.webdriver.drissionpage.DrissionPageHandler',
    },

    # curl_cffi handlers
    # curl_cffi处理程序
    'curl_cffi': {
        'http': 'aioscrapy.core.downloader.handlers.curl_cffi.CurlCffiDownloadHandler',
        'https': 'aioscrapy.core.downloader.handlers.curl_cffi.CurlCffiDownloadHandler',
    },
}

# Download timeout in seconds (3 minutes)
# 下载超时时间（秒）（3分钟）
DOWNLOAD_TIMEOUT = 180  # 3mins

# Downloader class to use
# 要使用的下载器类
DOWNLOADER = 'aioscrapy.core.downloader.Downloader'

# Custom downloader middlewares
# 自定义下载器中间件
DOWNLOADER_MIDDLEWARES = {}

# Base downloader middlewares with their priorities
# 基本下载器中间件及其优先级
DOWNLOADER_MIDDLEWARES_BASE = {
    # Engine side middlewares
    # 引擎端中间件
    'aioscrapy.libs.downloader.downloadtimeout.DownloadTimeoutMiddleware': 350,  # Handles download timeouts
    'aioscrapy.libs.downloader.defaultheaders.DefaultHeadersMiddleware': 400,    # Adds default headers
    'aioscrapy.libs.downloader.useragent.UserAgentMiddleware': 500,              # Sets User-Agent
    'aioscrapy.libs.downloader.retry.RetryMiddleware': 550,                      # Retries failed requests
    'aioscrapy.libs.downloader.stats.DownloaderStats': 850,                      # Collects download stats
    'aioscrapy.libs.downloader.ja3fingerprint.TLSCiphersMiddleware': 950,        # Manages TLS fingerprints
    # Downloader side middlewares
    # 下载器端中间件
}

# Whether to collect downloader statistics
# 是否收集下载器统计信息
DOWNLOADER_STATS = True

# Duplicate filter settings (commented out by default)
# 重复过滤器设置（默认注释掉）

# Class to use for filtering duplicate requests
# 用于过滤重复请求的类
# DUPEFILTER_CLASS = 'aioscrapy.dupefilters.disk.RFPDupeFilter'

# Whether to enable debug logging for the duplicate filter
# 是否为重复过滤器启用调试日志记录
# DUPEFILTER_DEBUG = False

# Editor to use when editing spiders with the 'edit' command
# 使用'edit'命令编辑爬虫时使用的编辑器
EDITOR = 'vi'
if sys.platform == 'win32':
    EDITOR = '%s -m idlelibs.idle'

# Extensions settings
# 扩展设置

# Custom extensions to enable
# 要启用的自定义扩展
EXTENSIONS = {}

# Base extensions with their priorities
# 基本扩展及其优先级
EXTENSIONS_BASE = {
    # Core statistics extension
    # 核心统计扩展
    'aioscrapy.libs.extensions.corestats.CoreStats': 0,

    # Close spider extension (handles automatic closing)
    # 关闭爬虫扩展（处理自动关闭）
    'aioscrapy.libs.extensions.closespider.CloseSpider': 0,

    # Log statistics extension
    # 日志统计扩展
    'aioscrapy.libs.extensions.logstats.LogStats': 0,

    # Auto throttle extension (commented out by default)
    # 自动限流扩展（默认注释掉）
    # 'aioscrapy.libs.extensions.throttle.AutoThrottle': 0,
}

# File storage settings
# 文件存储设置

# Access control list for Amazon S3 file storage
# Amazon S3文件存储的访问控制列表
FILES_STORE_S3_ACL = 'private'

# Access control list for Google Cloud Storage file storage
# Google Cloud Storage文件存储的访问控制列表
FILES_STORE_GCS_ACL = ''

# HTTP proxy settings
# HTTP代理设置

# Whether to enable HTTP proxy support
# 是否启用HTTP代理支持
HTTPPROXY_ENABLED = True

# Encoding used for proxy authentication
# 用于代理认证的编码
HTTPPROXY_AUTH_ENCODING = 'latin-1'

# Item processing settings
# 项目处理设置

# Class to use for processing items
# 用于处理项目的类
ITEM_PROCESSOR = 'aioscrapy.middleware.ItemPipelineManager'

# Custom item pipelines to enable
# 要启用的自定义项目管道
ITEM_PIPELINES = {}

# Base item pipelines
# 基本项目管道
ITEM_PIPELINES_BASE = {}

# Logging settings
# 日志设置

# Whether to enable logging
# 是否启用日志记录
LOG_ENABLED = True

# Encoding used for log files
# 用于日志文件的编码
LOG_ENCODING = 'utf-8'

# Log file rotation size
# 日志文件轮转大小
LOG_ROTATION = '20MB'

# Number of log files to keep
# 要保留的日志文件数量
LOG_RETENTION = 10

# Class to use for formatting log messages
# 用于格式化日志消息的类
LOG_FORMATTER = 'aioscrapy.logformatter.LogFormatter'

# Format string for log messages
# 日志消息的格式字符串
LOG_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{process}</cyan> | <cyan>{extra[spidername]}</cyan> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>"

# Whether to log to standard output
# 是否记录到标准输出
LOG_STDOUT = True

# Minimum level of messages to log
# 要记录的消息的最低级别
LOG_LEVEL = 'DEBUG'

# Log file path (None means no log file)
# 日志文件路径（None表示没有日志文件）
LOG_FILE = None

# Whether to enable debug logging for the scheduler
# 是否为调度器启用调试日志记录
SCHEDULER_DEBUG = False

# Interval in seconds between logging of crawl stats
# 爬取统计信息日志记录之间的间隔（秒）
LOGSTATS_INTERVAL = 60.0

# Module where newly created spiders will be placed
# 新创建的爬虫将被放置的模块
NEWSPIDER_MODULE = ''

# Whether to randomize the download delay (between 0.5 * DOWNLOAD_DELAY and 1.5 * DOWNLOAD_DELAY)
# 是否随机化下载延迟（在0.5 * DOWNLOAD_DELAY和1.5 * DOWNLOAD_DELAY之间）
RANDOMIZE_DOWNLOAD_DELAY = True

# Redirect settings
# 重定向设置

# Whether to follow redirects
# 是否跟随重定向
REDIRECT_ENABLED = True

# Maximum number of redirects to follow for a request
# 一个请求要跟随的最大重定向次数
REDIRECT_MAX_TIMES = 20

# Referer settings
# 引用设置

# Whether to enable referer middleware
# 是否启用引用中间件
REFERER_ENABLED = True

# Policy for setting the Referer header
# 设置Referer头的策略
REFERRER_POLICY = 'aioscrapy.libs.spider.referer.DefaultReferrerPolicy'

# Retry settings
# 重试设置

# Whether to retry failed requests
# 是否重试失败的请求
RETRY_ENABLED = True

# Number of times to retry a failed request (initial response + 2 retries = 3 requests)
# 重试失败请求的次数（初始响应 + 2次重试 = 3个请求）
RETRY_TIMES = 2

# HTTP status codes to retry
# 要重试的HTTP状态码
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429]

# Priority adjustment for retried requests (negative means lower priority)
# 重试请求的优先级调整（负数表示较低优先级）
RETRY_PRIORITY_ADJUST = -1

# Scheduler settings
# 调度器设置

# Scheduler class to use
# 要使用的调度器类
SCHEDULER = 'aioscrapy.core.scheduler.Scheduler'

# Queue class used by the scheduler
# 调度器使用的队列类
SCHEDULER_QUEUE_CLASS = 'aioscrapy.queue.memory.SpiderPriorityQueue'

# Serializer class used by the scheduler for serializing requests
# 调度器用于序列化请求的序列化器类
SCHEDULER_SERIALIZER = 'aioscrapy.serializer.JsonSerializer'

# Maximum size in bytes for the scraper slot (controls memory usage)
# 刮取器槽的最大大小（字节）（控制内存使用）
SCRAPER_SLOT_MAX_ACTIVE_SIZE = 5000000

# Spider loader settings
# 爬虫加载器设置

# Class to use for loading spiders
# 用于加载爬虫的类
SPIDER_LOADER_CLASS = 'aioscrapy.spiderloader.SpiderLoader'

# Whether to only warn (instead of error) when a spider module cannot be imported
# 当爬虫模块无法导入时是否只发出警告（而不是错误）
SPIDER_LOADER_WARN_ONLY = False

# Spider middleware settings
# 爬虫中间件设置

# Custom spider middlewares to enable
# 要启用的自定义爬虫中间件
SPIDER_MIDDLEWARES = {}

# Base spider middlewares with their priorities
# 基本爬虫中间件及其优先级
SPIDER_MIDDLEWARES_BASE = {
    # Handles HTTP errors (e.g., 404, 500)
    # 处理HTTP错误（例如，404、500）
    'aioscrapy.libs.spider.httperror.HttpErrorMiddleware': 50,

    # Filters out requests to URLs outside the domains allowed by the spider
    # 过滤掉对爬虫允许的域之外的URL的请求
    'aioscrapy.libs.spider.offsite.OffsiteMiddleware': 500,

    # Sets the Referer header
    # 设置Referer头
    'aioscrapy.libs.spider.referer.RefererMiddleware': 700,

    # Filters out requests with URLs longer than URLLENGTH_LIMIT
    # 过滤掉URL长度超过URLLENGTH_LIMIT的请求
    'aioscrapy.libs.spider.urllength.UrlLengthMiddleware': 800,

    # Tracks request depth
    # 跟踪请求深度
    'aioscrapy.libs.spider.depth.DepthMiddleware': 900,
}

# List of modules where spiders are expected to be defined
# 预期定义爬虫的模块列表
SPIDER_MODULES = []

# Statistics collection settings
# 统计收集设置

# Class to use for collecting crawler stats
# 用于收集爬虫统计信息的类
STATS_CLASS = 'aioscrapy.statscollectors.MemoryStatsCollector'

# Whether to dump stats when the spider finishes
# 爬虫完成时是否转储统计信息
STATS_DUMP = True

# Directory where project templates are stored
# 存储项目模板的目录
TEMPLATES_DIR = abspath(join(dirname(__file__), '..', 'templates'))

# Maximum allowed length for URLs
# URL的最大允许长度
URLLENGTH_LIMIT = 2083

# Whether to close the spider when it becomes idle (no more requests)
# 当爬虫变为空闲状态（没有更多请求）时是否关闭爬虫
CLOSE_SPIDER_ON_IDLE = False
