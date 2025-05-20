"""
Metric Extension for AioScrapy
AioScrapy的指标扩展

This module provides extensions for collecting and reporting metrics from AioScrapy
spiders. It supports sending metrics to InfluxDB over HTTP or logging them to files.
此模块提供了用于收集和报告AioScrapy爬虫指标的扩展。
它支持通过HTTP将指标发送到InfluxDB或将它们记录到文件中。

The metrics are collected periodically and can be configured using the following settings:
指标会定期收集，可以使用以下设置进行配置：

* METRIC_INTERVAL: How often to collect and report metrics (in seconds)
                  收集和报告指标的频率（以秒为单位）
* METRIC_INFLUXDB_URL: URL of the InfluxDB server
                      InfluxDB服务器的URL
* METRIC_INFLUXDB_TOKEN: Authentication token for InfluxDB
                        InfluxDB的认证令牌
* METRIC_LOCATION: Location identifier for the metrics
                  指标的位置标识符
* METRIC_RETRY_TIMES: Number of times to retry sending metrics to InfluxDB
                     重试向InfluxDB发送指标的次数
* METRIC_LOG_ARGS: Arguments for configuring metric logging
                  配置指标日志记录的参数
* METRICS: Dictionary of metrics to collect (if not specified, all stats are collected)
          要收集的指标字典（如果未指定，则收集所有统计信息）
"""

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
    """
    Base class for InfluxDB metric reporters.
    InfluxDB指标报告器的基类。

    This abstract class defines the interface for classes that report metrics
    to InfluxDB or similar time-series databases. It provides methods for
    formatting metrics in InfluxDB line protocol format, recording metrics,
    and closing connections.
    这个抽象类定义了向InfluxDB或类似时间序列数据库报告指标的类的接口。
    它提供了以InfluxDB行协议格式格式化指标、记录指标和关闭连接的方法。
    """

    @staticmethod
    def format_metric(metric_name, value, spider_name, location, measurement=None):
        """
        Format a metric in InfluxDB line protocol format.
        以InfluxDB行协议格式格式化指标。

        The line protocol format is:
        <measurement>,<tag_set> <field_set> <timestamp>

        Args:
            metric_name: The name of the metric.
                        指标的名称。
            value: The value of the metric.
                  指标的值。
            spider_name: The name of the spider that generated the metric.
                        生成指标的爬虫的名称。
            location: The location identifier for the metric.
                     指标的位置标识符。
            measurement: Optional measurement name. If not provided, metric_name is used.
                        可选的测量名称。如果未提供，则使用metric_name。

        Returns:
            str: The formatted metric in InfluxDB line protocol format.
                 以InfluxDB行协议格式格式化的指标。
        """
        # Use metric_name as measurement if not provided
        # 如果未提供，则使用metric_name作为measurement
        measurement = measurement or metric_name

        # Format the metric in InfluxDB line protocol format
        # 以InfluxDB行协议格式格式化指标
        # Add a random component to the timestamp to avoid collisions
        # 向时间戳添加随机组件以避免冲突
        return f"{measurement},spider_name={spider_name},location={location} {metric_name}={value} {time.time_ns() + int(random.random() * 100000)}"

    async def record(self, obj: "Metric"):
        """
        Record metrics from a Metric object.
        记录来自Metric对象的指标。

        This is an abstract method that must be implemented by subclasses.
        这是一个必须由子类实现的抽象方法。

        Args:
            obj: The Metric object containing the metrics to record.
                包含要记录的指标的Metric对象。

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
                                此方法必须由子类实现。
        """
        raise NotImplementedError

    async def close(self):
        """
        Close any resources used by the reporter.
        关闭报告器使用的任何资源。

        This method is called when the spider is closed. It should release
        any resources used by the reporter, such as network connections.
        当爬虫关闭时调用此方法。它应该释放报告器使用的任何资源，
        例如网络连接。

        Returns:
            None
        """
        pass


class InfluxHttp(InfluxBase):
    """
    InfluxDB HTTP reporter for metrics.
    用于指标的InfluxDB HTTP报告器。

    This class sends metrics to an InfluxDB server over HTTP using the InfluxDB
    line protocol. It handles authentication, retries, and connection management.
    此类使用InfluxDB行协议通过HTTP将指标发送到InfluxDB服务器。
    它处理身份验证、重试和连接管理。
    """

    def __init__(self, spider_name: str, settings: Settings):
        """
        Initialize the InfluxDB HTTP reporter.
        初始化InfluxDB HTTP报告器。

        Args:
            spider_name: The name of the spider generating the metrics.
                        生成指标的爬虫的名称。
            settings: The AioScrapy settings object.
                     AioScrapy设置对象。
        """
        # Get configuration from settings
        # 从设置获取配置
        influxdb_url = settings.get('METRIC_INFLUXDB_URL')
        token = settings.get('METRIC_INFLUXDB_TOKEN')
        location = settings.get('METRIC_LOCATION')
        self.retry_times = settings.getint('METRIC_RETRY_TIMES', 5)

        # Set location identifier, using node name and process ID as default
        # 设置位置标识符，默认使用节点名称和进程ID
        self.location = location or f"{platform.node()}_{os.getpid()}"
        self.spider_name = spider_name

        # Create HTTP session with appropriate headers for InfluxDB
        # 创建带有适用于InfluxDB的适当头部的HTTP会话
        self.session = ClientSession(headers={
            "Authorization": f"Token {token}",
            "Content-Type": "text/plain; charset=utf-8",
            "Accept": "application/json",
        })
        self.url = influxdb_url

        # Lock to ensure only one record operation happens at a time
        # 锁定以确保一次只发生一个记录操作
        self.lock = asyncio.Lock()

    async def emit(self, data):
        """
        Send metrics data to the InfluxDB server.
        将指标数据发送到InfluxDB服务器。

        Args:
            data: The metrics data in InfluxDB line protocol format.
                 InfluxDB行协议格式的指标数据。

        Returns:
            None
        """
        # Send data to InfluxDB server
        # 将数据发送到InfluxDB服务器
        async with self.session.post(self.url, data=data) as response:
            await response.read()
            logger.debug(f"emit metric success<{response.status}>: \n{data}")

    async def record(self, obj: "Metric"):
        """
        Record metrics from a Metric object to InfluxDB.
        将Metric对象中的指标记录到InfluxDB。

        This method calculates the delta for each metric since the last recording
        and sends only the changes to InfluxDB.
        此方法计算自上次记录以来每个指标的增量，并仅将更改发送到InfluxDB。

        Args:
            obj: The Metric object containing the metrics to record.
                包含要记录的指标的Metric对象。
        """
        # Use lock to ensure only one record operation happens at a time
        # 使用锁确保一次只发生一个记录操作
        async with self.lock:
            data = ''

            # Process each metric
            # 处理每个指标
            for metric_name in obj.metrics.keys():
                # Get current value
                # 获取当前值
                current_cnt = obj.stats.get_value(metric_name, 0)

                # Skip non-numeric metrics
                # 跳过非数字指标
                if not isinstance(current_cnt, (int, float)):
                    continue

                # Calculate delta since last recording
                # 计算自上次记录以来的增量
                cnt = current_cnt - obj.prev.get(metric_name, 0)

                # Only record if there's a change
                # 仅在有变化时记录
                if cnt:
                    data += self.format_metric(
                        metric_name.replace('/', '-'), cnt, self.spider_name, self.location
                    ) + '\n'

                # Update previous value
                # 更新先前的值
                obj.prev[metric_name] = current_cnt

            # If we have data to send
            # 如果我们有数据要发送
            if data:
                # Try to send data with retries
                # 尝试使用重试发送数据
                for _ in range(self.retry_times):
                    try:
                        await self.emit(data)
                        return
                    except:
                        continue

                # Log warning if all retries failed
                # 如果所有重试都失败，则记录警告
                logger.warning(f"emit metric failed:\n{data}")

    async def close(self):
        """
        Close the HTTP session.
        关闭HTTP会话。

        This method is called when the spider is closed. It closes the HTTP session
        and waits a short time to ensure all pending requests are completed.
        当爬虫关闭时调用此方法。它关闭HTTP会话并等待短暂时间以确保所有
        待处理的请求都已完成。
        """
        if self.session is not None:
            await self.session.close()
            # Wait a short time to ensure all pending requests are completed
            # 等待短暂时间以确保所有待处理的请求都已完成
            await asyncio.sleep(0.250)


class InfluxLog(InfluxBase):
    """
    Logger-based reporter for metrics.
    基于日志记录器的指标报告器。

    This class logs metrics to a file or other logging sink instead of sending them
    to an InfluxDB server. It formats the metrics in InfluxDB line protocol format
    for consistency with the InfluxHttp reporter.
    此类将指标记录到文件或其他日志接收器，而不是将它们发送到InfluxDB服务器。
    它以InfluxDB行协议格式格式化指标，以与InfluxHttp报告器保持一致。
    """

    def __init__(self, spider_name: str, settings: Settings):
        """
        Initialize the logger-based metric reporter.
        初始化基于日志记录器的指标报告器。

        Args:
            spider_name: The name of the spider generating the metrics.
                        生成指标的爬虫的名称。
            settings: The AioScrapy settings object.
                     AioScrapy设置对象。
        """
        # Get location from settings or use default
        # 从设置获取位置或使用默认值
        location = settings.get('METRIC_LOCATION')
        self.location = location or f"{platform.node()}_{os.getpid()}"
        self.spider_name = spider_name

        # Configure logging based on settings
        # 根据设置配置日志记录
        log_args = settings.getdict('METRIC_LOG_ARGS')
        if log_args:
            # Add filter to only log records with metric extra field
            # 添加过滤器，仅记录具有metric额外字段的记录
            log_args.update(dict(
                filter=lambda record: record["extra"].get("metric") is not None,
                encoding="utf-8"
            ))

            # Set default logging parameters if not provided
            # 如果未提供，则设置默认日志参数
            for k, v in dict(
                    sink=f'{spider_name}.metric', level="INFO", rotation='20MB', retention=3,
                    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> <level>{message}</level>",
            ).items():
                log_args.setdefault(k, v)

            # Configure logger with the specified parameters
            # 使用指定的参数配置日志记录器
            _logger.add(**log_args)
            self.log = _logger.bind(metric="metric")
        else:
            # Use default logger if no specific configuration
            # 如果没有特定配置，则使用默认日志记录器
            self.log = logger

    async def record(self, obj: "Metric"):
        """
        Record metrics from a Metric object to the log.
        将Metric对象中的指标记录到日志。

        This method calculates the delta for each metric since the last recording
        and logs only the changes.
        此方法计算自上次记录以来每个指标的增量，并仅记录更改。

        Args:
            obj: The Metric object containing the metrics to record.
                包含要记录的指标的Metric对象。
        """
        # Process each metric
        # 处理每个指标
        for metric_name in obj.metrics.keys():
            # Get current value
            # 获取当前值
            current_cnt = obj.stats.get_value(metric_name, 0)

            # Skip non-numeric metrics
            # 跳过非数字指标
            if not isinstance(current_cnt, (int, float)):
                continue

            # Calculate delta since last recording
            # 计算自上次记录以来的增量
            prev_cnt = obj.prev.get(metric_name, 0)
            cnt = current_cnt - prev_cnt

            # Only log if there's a change
            # 仅在有变化时记录
            if cnt:
                # Format the metric and log it
                # 格式化指标并记录它
                msg = self.format_metric(metric_name.replace('/', '-'), cnt, self.spider_name, self.location)
                self.log.info(f'METRIC: {msg}')

            # Update previous value
            # 更新先前的值
            obj.prev[metric_name] = current_cnt


class Metric:
    """
    Extension to log metrics from spider scraping stats periodically.
    定期记录爬虫抓取统计信息指标的扩展。

    This extension periodically collects statistics from the spider's stats collector
    and records them using either an InfluxDB HTTP reporter or a logger-based reporter.
    It calculates the delta for each metric since the last recording to track the
    rate of change.
    此扩展定期从爬虫的统计收集器收集统计信息，并使用InfluxDB HTTP报告器或
    基于日志记录器的报告器记录它们。它计算自上次记录以来每个指标的增量，
    以跟踪变化率。
    """

    def __init__(self, stats, spider_name, settings, interval=10.0):
        """
        Initialize the Metric extension.
        初始化Metric扩展。

        Args:
            stats: The stats collector instance.
                  统计收集器实例。
            spider_name: The name of the spider.
                        爬虫的名称。
            settings: The AioScrapy settings object.
                     AioScrapy设置对象。
            interval: How often to collect and record metrics, in seconds.
                     收集和记录指标的频率，以秒为单位。
                     Defaults to 10.0 seconds.
                     默认为10.0秒。
        """
        # Choose the appropriate reporter based on settings
        # 根据设置选择适当的报告器
        if settings.get('METRIC_INFLUXDB_URL'):
            self.influx = InfluxHttp(spider_name, settings)
        else:
            self.influx = InfluxLog(spider_name, settings)

        self.stats = stats

        # Get metrics to collect from settings, or use all stats if not specified
        # 从设置获取要收集的指标，如果未指定，则使用所有统计信息
        self.metrics = settings.getdict('METRICS') or self.stats._stats
        self.interval = interval
        self.task = None

        # Dictionary to store previous values for calculating deltas
        # 用于存储先前值以计算增量的字典
        self.prev = {}

    @classmethod
    def from_crawler(cls, crawler):
        """
        Create a Metric instance from a crawler.
        从爬虫创建Metric实例。

        This is the factory method used by AioScrapy to create extension instances.
        这是AioScrapy用于创建扩展实例的工厂方法。

        Args:
            crawler: The crawler that will use this extension.
                    将使用此扩展的爬虫。

        Returns:
            Metric: A new Metric instance.
                   一个新的Metric实例。
        """
        # Get interval from settings
        # 从设置获取间隔
        interval = crawler.settings.getfloat('METRIC_INTERVAL', 10.0)

        # Create instance
        # 创建实例
        o = cls(crawler.stats, crawler.spider.name, crawler.settings, interval)

        # Connect to signals
        # 连接到信号
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(o.spider_closed, signal=signals.spider_closed)

        return o

    def spider_opened(self, spider):
        """
        Signal handler for the spider_opened signal.
        spider_opened信号的处理程序。

        Starts the periodic task to collect and record metrics.
        启动定期收集和记录指标的任务。

        Args:
            spider: The spider that was opened.
                   被打开的爬虫。
        """
        # Start the periodic task
        # 启动定期任务
        self.task = create_task(self.run(spider))

    async def run(self, spider):
        """
        Periodically collect and record metrics.
        定期收集和记录指标。

        This method waits for the configured interval, records the current metrics,
        then schedules itself to run again.
        此方法等待配置的间隔，记录当前指标，然后安排自己再次运行。

        Args:
            spider: The spider instance.
                   爬虫实例。
        """
        # Wait for the configured interval
        # 等待配置的间隔
        await asyncio.sleep(self.interval)

        # Record metrics
        # 记录指标
        await self.influx.record(self)

        # Schedule next run
        # 安排下一次运行
        self.task = create_task(self.run(spider))

    async def spider_closed(self, spider, reason):
        """
        Signal handler for the spider_closed signal.
        spider_closed信号的处理程序。

        Cancels the periodic task, records final metrics, and closes the reporter.
        取消定期任务，记录最终指标，并关闭报告器。

        Args:
            spider: The spider that was closed.
                   被关闭的爬虫。
            reason: The reason why the spider was closed.
                   爬虫被关闭的原因。
        """
        # Cancel the periodic task if it's running
        # 如果定期任务正在运行，则取消它
        if self.task and not self.task.done():
            self.task.cancel()

        # Record final metrics
        # 记录最终指标
        await self.influx.record(self)

        # Close the reporter
        # 关闭报告器
        await self.influx.close()
