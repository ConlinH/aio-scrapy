import asyncio
import os
import platform
import random
import time

from aiohttp import ClientSession

from aioscrapy import Settings
from aioscrapy import signals
from aioscrapy.utils.log import _logger, logger
from aioscrapy.utils.tools import create_task


class InfluxBase:
    @staticmethod
    def format_metric(metric_name, value, spider_name, location, measurement=None):
        measurement = measurement or metric_name
        return f"{measurement},spider_name={spider_name},location={location} {metric_name}={value} {time.time_ns() + int(random.random() * 100000)}"

    async def record(self, obj: "Metric"):
        raise NotImplementedError

    async def close(self):
        pass


class InfluxHttp(InfluxBase):
    def __init__(self, spider_name: str, settings: Settings):
        influxdb_url = settings.get('METRIC_INFLUXDB_URL')
        token = settings.get('METRIC_INFLUXDB_TOKEN')
        location = settings.get('METRIC_LOCATION')
        self.retry_times = settings.getint('METRIC_RETRY_TIMES', 5)
        self.location = location or f"{platform.node()}_{os.getpid()}"
        self.spider_name = spider_name
        self.session = ClientSession(headers={
            "Authorization": f"Token {token}",
            "Content-Type": "text/plain; charset=utf-8",
            "Accept": "application/json",
        })
        self.url = influxdb_url
        self.lock = asyncio.Lock()

    async def emit(self, data):
        async with self.session.post(self.url, data=data) as response:
            await response.read()
            logger.debug(f"emit metric success<{response.status}>: \n{data}")

    async def record(self, obj: "Metric"):
        async with self.lock:
            data = ''
            for metric_name in obj.metrics.keys():
                current_cnt = obj.stats.get_value(metric_name, 0)
                if not isinstance(current_cnt, (int, float)):
                    continue
                cnt = current_cnt - obj.prev.get(metric_name, 0)
                if cnt:
                    data += self.format_metric(
                        metric_name.replace('/', '-'), cnt, self.spider_name, self.location
                    ) + '\n'
                obj.prev[metric_name] = current_cnt
            if data:
                for _ in range(self.retry_times):
                    try:
                        await self.emit(data)
                        return
                    except:
                        continue
                logger.warning(f"emit metric failed:\n{data}")

    async def close(self):
        if self.session is not None:
            await self.session.close()
            await asyncio.sleep(0.250)


class InfluxLog(InfluxBase):
    def __init__(self, spider_name: str, settings: Settings):
        location = settings.get('METRIC_LOCATION')
        self.location = location or f"{platform.node()}_{os.getpid()}"
        self.spider_name = spider_name

        log_args = settings.getdict('METRIC_LOG_ARGS')
        log_args.update(dict(
            filter=lambda record: record["extra"].get("metric") is not None,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> <level>{message}</level>",
            encoding="utf-8"
        ))
        for k, v in dict(
                sink=f'{spider_name}.metric', level="INFO", rotation='20MB',
                retention=3
        ).items():
            log_args.setdefault(k, v)

        _logger.add(**log_args)
        self.log = _logger.bind(metric="metric")

    async def record(self, obj: "Metric"):
        for metric_name in obj.metrics.keys():
            current_cnt = obj.stats.get_value(metric_name, 0)
            if not isinstance(current_cnt, (int, float)):
                continue
            prev_cnt = obj.prev.get(metric_name, 0)
            cnt = current_cnt - prev_cnt
            if cnt:
                msg = self.format_metric(metric_name.replace('/', '-'), cnt, self.spider_name, self.location)
                self.log.info(msg)
                logger.debug(msg)
            obj.prev[metric_name] = current_cnt


class Metric:
    """Log Metric scraping stats periodically"""

    def __init__(self, stats, spider_name, settings, interval=10.0):
        if settings.get('METRIC_INFLUXDB_URL'):
            self.influx = InfluxHttp(spider_name, settings)
        else:
            self.influx = InfluxLog(spider_name, settings)
        self.stats = stats
        self.metrics = settings.getdict('METRICS') or self.stats._stats
        self.interval = interval
        self.task = None
        self.prev = {}

    @classmethod
    def from_crawler(cls, crawler):
        interval = crawler.settings.getfloat('METRIC_INTERVAL', 10.0)
        o = cls(crawler.stats, crawler.spider.name, crawler.settings, interval)
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(o.spider_closed, signal=signals.spider_closed)
        return o

    def spider_opened(self, spider):
        self.task = create_task(self.run(spider))

    async def run(self, spider):
        await asyncio.sleep(self.interval)
        await self.influx.record(self)
        self.task = create_task(self.run(spider))

    async def spider_closed(self, spider, reason):
        if self.task and not self.task.done():
            self.task.cancel()
        await self.influx.record(self)
        await self.influx.close()
