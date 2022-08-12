"""
This module contains the default values for all settings used by Aioscrapy.

For more information about these settings you can read the settings
documentation in docs/topics/settings.rst

Aioscrapy developers, if you add a setting here remember to:

* add it in alphabetical order
* group similar settings without leaving blank lines
* add its documentation to the available settings documentation
  (docs/topics/settings.rst)

"""

import sys
from os.path import join, abspath, dirname

AUTOTHROTTLE_ENABLED = False
AUTOTHROTTLE_DEBUG = False
AUTOTHROTTLE_MAX_DELAY = 60.0
AUTOTHROTTLE_START_DELAY = 5.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

BOT_NAME = 'aioscrapybot'

CLOSESPIDER_TIMEOUT = 0
CLOSESPIDER_PAGECOUNT = 0
CLOSESPIDER_ITEMCOUNT = 0
CLOSESPIDER_ERRORCOUNT = 0

COMMANDS_MODULE = ''

CONCURRENT_PARSER = 1

CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 8
CONCURRENT_REQUESTS_PER_IP = 0


DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en',
}

DEPTH_LIMIT = 0
DEPTH_STATS_VERBOSE = False
DEPTH_PRIORITY = 0

DOWNLOAD_DELAY = 0

DOWNLOAD_HANDLERS = {}
DOWNLOAD_HANDLERS_BASE = {
    'http': 'aioscrapy.core.downloader.handlers.aiohttp.AioHttpDownloadHandler',
    'https': 'aioscrapy.core.downloader.handlers.aiohttp.AioHttpDownloadHandler',
}

DOWNLOAD_TIMEOUT = 180      # 3mins

DOWNLOADER = 'aioscrapy.core.downloader.Downloader'

DOWNLOADER_MIDDLEWARES = {}

DOWNLOADER_MIDDLEWARES_BASE = {
    # Engine side
    'aioscrapy.libs.downloader.downloadtimeout.DownloadTimeoutMiddleware': 350,
    'aioscrapy.libs.downloader.defaultheaders.DefaultHeadersMiddleware': 400,
    'aioscrapy.libs.downloader.useragent.UserAgentMiddleware': 500,
    'aioscrapy.libs.downloader.retry.RetryMiddleware': 550,
    'aioscrapy.libs.downloader.stats.DownloaderStats': 850,
    'aioscrapy.libs.downloader.ja3fingerprint.TLSCiphersMiddleware': 950,
    # Downloader side
}

DOWNLOADER_STATS = True

# DUPEFILTER_CLASS = 'aioscrapy.dupefilters.disk.RFPDupeFilter'
# DUPEFILTER_DEBUG = False

EDITOR = 'vi'
if sys.platform == 'win32':
    EDITOR = '%s -m idlelibs.idle'

EXTENSIONS = {}

EXTENSIONS_BASE = {
    'aioscrapy.libs.extensions.corestats.CoreStats': 0,
    'aioscrapy.libs.extensions.closespider.CloseSpider': 0,
    'aioscrapy.libs.extensions.logstats.LogStats': 0,
    'aioscrapy.libs.extensions.throttle.AutoThrottle': 0,
}


FILES_STORE_S3_ACL = 'private'
FILES_STORE_GCS_ACL = ''

HTTPPROXY_ENABLED = True
HTTPPROXY_AUTH_ENCODING = 'latin-1'

ITEM_PROCESSOR = 'aioscrapy.middleware.ItemPipelineManager'

ITEM_PIPELINES = {}
ITEM_PIPELINES_BASE = {}

LOG_ENABLED = True
LOG_ENCODING = 'utf-8'
LOG_MAX_BYTES = 50*1024*1024
LOG_BACKUP_COUNT = 10
LOG_FORMATTER = 'aioscrapy.logformatter.LogFormatter'
LOG_FORMAT = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
LOG_DATEFORMAT = '%Y-%m-%d %H:%M:%S'
LOG_STDOUT = False
LOG_LEVEL = 'DEBUG'
LOG_FILE = None
LOG_SHORT_NAMES = False

SCHEDULER_DEBUG = False

LOGSTATS_INTERVAL = 60.0


METAREFRESH_ENABLED = True
METAREFRESH_IGNORE_TAGS = []
METAREFRESH_MAXDELAY = 100

NEWSPIDER_MODULE = ''

RANDOMIZE_DOWNLOAD_DELAY = True

REDIRECT_ENABLED = True
REDIRECT_MAX_TIMES = 20

REFERER_ENABLED = True
REFERRER_POLICY = 'aioscrapy.libs.spider.referer.DefaultReferrerPolicy'

RETRY_ENABLED = True
RETRY_TIMES = 2  # initial response + 2 retries = 3 requests
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429]
RETRY_PRIORITY_ADJUST = -1

SCHEDULER = 'aioscrapy.core.scheduler.Scheduler'
SCHEDULER_QUEUE_CLASS = 'aioscrapy.queue.memory.SpiderPriorityQueue'
SCHEDULER_SERIALIZER = 'aioscrapy.serializer.JsonSerializer'

SCRAPER_SLOT_MAX_ACTIVE_SIZE = 5000000

SPIDER_LOADER_CLASS = 'aioscrapy.spiderloader.SpiderLoader'
SPIDER_LOADER_WARN_ONLY = False

SPIDER_MIDDLEWARES = {}
SPIDER_MIDDLEWARES_BASE = {
    'aioscrapy.libs.spider.httperror.HttpErrorMiddleware': 50,
    'aioscrapy.libs.spider.offsite.OffsiteMiddleware': 500,
    'aioscrapy.libs.spider.referer.RefererMiddleware': 700,
    'aioscrapy.libs.spider.urllength.UrlLengthMiddleware': 800,
    'aioscrapy.libs.spider.depth.DepthMiddleware': 900,
}

SPIDER_MODULES = []

STATS_CLASS = 'aioscrapy.statscollectors.MemoryStatsCollector'
STATS_DUMP = True

TEMPLATES_DIR = abspath(join(dirname(__file__), '..', 'templates'))

URLLENGTH_LIMIT = 2083

CLOSE_SPIDER_ON_IDLE = False
