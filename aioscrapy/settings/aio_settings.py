# =============调度=======================================
SCHEDULER = 'aioscrapy.core.scheduler.Scheduler'
SCHEDULER_QUEUE_KEY = '%(spider)s:requests'
SCHEDULER_QUEUE_CLASS = 'aioscrapy.core.scheduler.queue.PriorityQueue'
SCHEDULER_PERSIST = True

# 去重
SCHEDULER_DUPEFILTER_KEY = '%(spider)s:dupefilter'
DUPEFILTER_CLASS = 'aioscrapy.core.scheduler.dupefilter.RFPDupeFilter'
# =============调度=======================================


# ===========下载器===================
DOWNLOADER = 'aioscrapy.core.downloader.Downloader'
DOWNLOAD_HANDLERS_BASE = {
    'http': 'aioscrapy.core.downloader.handlers.http.AioHttpDownloadHandler',
    'https': 'aioscrapy.core.downloader.handlers.http.AioHttpDownloadHandler',
}
# ===========下载器===================


# ===========下载中间件 ======================
DOWNLOADER_MIDDLEWARES = {
    # 不需要对response做压缩相关的处理, aiohttp已经处理了
    'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': None,
}
# ===========下载中间件 ======================


# ===========item中间件 ======================
ITEM_PROCESSOR = 'aioscrapy.middleware.ItemPipelineManager'
# ===========item中间件 ======================


# =========扩展中间件===============================
EXTENSIONS_BASE = {
    'aioscrapy.extensions.corestats.CoreStats': 0,
    # 'aioscrapy.extensions.telnet.TelnetConsole': 0,
    'aioscrapy.extensions.memusage.MemoryUsage': 0,
    'aioscrapy.extensions.memdebug.MemoryDebugger': 0,
    'aioscrapy.extensions.closespider.CloseSpider': 0,
    # 'aioscrapy.extensions.feedexport.FeedExporter': 0,
    'aioscrapy.extensions.logstats.LogStats': 0,
    'aioscrapy.extensions.spiderstate.SpiderState': 0,
    'aioscrapy.extensions.throttle.AutoThrottle': 0,
}
# =========扩展中间件===============================
