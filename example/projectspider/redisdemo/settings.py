BOT_NAME = 'redisdemo'

SPIDER_MODULES = ['redisdemo.spiders']
NEWSPIDER_MODULE = 'redisdemo.spiders'

# 是否配置去重及去重的方式
# DUPEFILTER_CLASS = 'aioscrapy.dupefilters.disk.RFPDupeFilter'
# DUPEFILTER_CLASS = 'aioscrapy.dupefilters.redis.RFPDupeFilter'
# DUPEFILTER_CLASS = 'aioscrapy.dupefilters.redis.BloomDupeFilter'

# 配置队列任务的序列化
# SCHEDULER_SERIALIZER = 'aioscrapy.serializer.JsonSerializer'      # 默认
# SCHEDULER_SERIALIZER = 'aioscrapy.serializer.PickleSerializer'

# 下载中间件
DOWNLOADER_MIDDLEWARES = {
    'redisdemo.middlewares.DemoDownloaderMiddleware': 543,
}

# 爬虫中间件
SPIDER_MIDDLEWARES = {
    'redisdemo.middlewares.DemoSpiderMiddleware': 543,
}

# item的处理方式
ITEM_PIPELINES = {
    'redisdemo.pipelines.DemoPipeline': 100,
}

# 扩展
# EXTENSIONS = {
# }

# 使用什么包发送请求
DOWNLOAD_HANDLERS_TYPE = "aiohttp"  # aiohttp httpx pyhttpx requests playwright 不配置则默认为aiohttp
# 自定义发包方式请用scrapy的形式，例如：
# DOWNLOAD_HANDLERS={
#     'http': 'aioscrapy.core.downloader.handlers.aiohttp.AioHttpDownloadHandler',
#     'https': 'aioscrapy.core.downloader.handlers.aiohttp.AioHttpDownloadHandler',
# }

# 下载延迟
# DOWNLOAD_DELAY = 3

# 随机下载延迟
# RANDOMIZE_DOWNLOAD_DELAY = True

# 并发数
CONCURRENT_REQUESTS = 16  # 总并发的个数 默认为16
CONCURRENT_REQUESTS_PER_DOMAIN = 8  # 按域名并发的个数 默认为8

# 爬虫空闲时是否关闭
CLOSE_SPIDER_ON_IDLE = False  # 默认为True

# 日志
# LOG_FILE = './log/info.log'            # 保存日志的位置及名称
LOG_STDOUT = True  # 是否将日志输出到控制台 默认为True
LOG_LEVEL = 'DEBUG'  # 日志等级

# 用redis当作任务队列
SCHEDULER_QUEUE_CLASS = 'aioscrapy.queue.redis.SpiderPriorityQueue'  # 配置redis的优先级队列
# SCHEDULER_FLUSH_ON_START = False                                   # 重启爬虫时是否清空任务队列 默认False
# redis 参数配置
REDIS_ARGS = {
    # "queue" 队列存放的别名, 用于存放求情到改redis连接池中
    'queue': {
        'url': 'redis://:@192.168.43.165:6379/10',
        'max_connections': 2,
        'timeout': None,
        'retry_on_timeout': True,
        'health_check_interval': 30,
    },

    # "proxy"是代理池的别名， 用以存放代理ip到改redis连接池中
    # 'proxy': {
    #     'url': 'redis://username:password@192.168.234.128:6379/2',
    #     'max_connections': 2,
    #     'timeout': None,
    #     'retry_on_timeout': True,
    #     'health_check_interval': 30,
    # }
}

# 代理配置
USE_PROXY = True  # 是否使用代理 默认为 False
PROXY_HANDLER = 'redisdemo.proxy.MyProxy'  # 代理类的加载路径 可参考aioscrapy.proxy.redis.RedisProxy代理的实现


# 本框架基本实现了scrapy/scrapy-redis的功能 想要配置更多参数，请参考scrapy
