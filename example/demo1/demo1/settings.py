# Scrapy settings for demo1 project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = 'demo1'

SPIDER_MODULES = ['demo1.spiders']
NEWSPIDER_MODULE = 'demo1.spiders'


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36"
DOWNLOAD_DELAY = 3
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS = 1
RANDOM_TLS_CIPHERS = True

SCHEDULER = 'aioscrapy.core.scheduler.Scheduler'
SCHEDULER_QUEUE_CLASS = 'aioscrapy.core.scheduler.queue.PriorityQueue'
DUPEFILTER_CLASS = 'aioscrapy.core.scheduler.dupefilter.RFPDupeFilter'
# SCHEDULER_SERIALIZER = 'aioscrapy.core.scheduler.serializ.JsonCompat'
REDIS_ARGS = {
    'url': 'redis://:erpteam_redis@192.168.5.216:6381/9',
    'max_connections': 2,
}

