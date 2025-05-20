"""
Log Formatter Module
日志格式化模块

This module provides the LogFormatter class, which formats log messages for various
events that occur during the crawling process, such as crawling a page, scraping an item,
dropping an item, or encountering errors.
此模块提供LogFormatter类，用于格式化爬取过程中发生的各种事件的日志消息，
例如爬取页面、抓取项目、丢弃项目或遇到错误。

The LogFormatter can be customized by subclassing and overriding its methods to
change the format of log messages.
可以通过子类化并覆盖其方法来自定义LogFormatter，以更改日志消息的格式。
"""
import os

from aioscrapy.utils.request import referer_str

# Standard log message templates
# 标准日志消息模板
SCRAPEDMSG = "Scraped from %(src)s" + os.linesep + "%(item)s"
DROPPEDMSG = "Dropped: %(exception)s" + os.linesep + "%(item)s"
CRAWLEDMSG = "Crawled (%(status)s) %(request)s%(request_flags)s (referer: %(referer)s)%(response_flags)s"
ITEMERRORMSG = "Error processing %(item)s"
SPIDERERRORMSG = "Spider error processing %(request)s (referer: %(referer)s)"
DOWNLOADERRORMSG_SHORT = "Error downloading %(request)s"
DOWNLOADERRORMSG_LONG = "Error downloading %(request)s: %(errmsg)s"


class LogFormatter:
    """
    Formats log messages for various events during the crawling process.
    格式化爬取过程中各种事件的日志消息。

    This class provides methods to format log messages for events such as crawling a page,
    scraping an item, dropping an item, or encountering errors. It can be customized by
    subclassing and overriding its methods to change the format of log messages.
    此类提供方法来格式化爬取页面、抓取项目、丢弃项目或遇到错误等事件的日志消息。
    可以通过子类化并覆盖其方法来自定义它，以更改日志消息的格式。
    """

    @staticmethod
    def crawled(request, response, spider):
        """
        Format a log message for a crawled page.
        格式化已爬取页面的日志消息。

        This method is called when the crawler successfully downloads a webpage.
        It formats a log message that includes the response status, request URL,
        request flags, referer, and response flags.
        当爬虫成功下载网页时调用此方法。它格式化一条包含响应状态、请求URL、
        请求标志、引用者和响应标志的日志消息。

        Args:
            request: The request that was made.
                    发出的请求。
            response: The response that was received.
                     接收到的响应。
            spider: The spider that made the request.
                   发出请求的爬虫。

        Returns:
            dict: A dictionary with log level and message.
                 包含日志级别和消息的字典。
        """
        # Format request and response flags if they exist
        # 如果存在，则格式化请求和响应标志
        request_flags = f' {str(request.flags)}' if request.flags else ''
        response_flags = f' {str(response.flags)}' if response.flags else ''

        # Return a dictionary with log level and formatted message
        # 返回包含日志级别和格式化消息的字典
        return {
            '_Logger__level': "DEBUG",
            '_Logger__message': CRAWLEDMSG % {
                'status': response.status,
                'request': request,
                'request_flags': request_flags,
                'referer': referer_str(request),
                'response_flags': response_flags,
                'flags': response_flags
            }
        }

    @staticmethod
    def scraped(item, response, spider):
        """
        Format a log message for a scraped item.
        格式化已抓取项目的日志消息。

        This method is called when a spider successfully scrapes an item from a response.
        It formats a log message that includes the response source and the item details.
        当爬虫成功从响应中抓取项目时调用此方法。它格式化一条包含响应源和项目详细信息的日志消息。

        Args:
            item: The item that was scraped.
                 被抓取的项目。
            response: The response from which the item was scraped.
                     项目被抓取的响应。
            spider: The spider that scraped the item.
                   抓取项目的爬虫。

        Returns:
            dict: A dictionary with log level and message.
                 包含日志级别和消息的字典。
        """
        # Use the response as the source
        # 使用响应作为源
        src = response

        # Return a dictionary with log level and formatted message
        # 返回包含日志级别和格式化消息的字典
        return {
            '_Logger__level': "DEBUG",
            '_Logger__message': SCRAPEDMSG % {
                'src': src,
                'item': item,
            }
        }

    @staticmethod
    def dropped(item, exception, response, spider):
        """
        Format a log message for a dropped item.
        格式化已丢弃项目的日志消息。

        This method is called when an item is dropped while passing through the item pipeline.
        It formats a log message that includes the exception that caused the item to be dropped
        and the item details.
        当项目在通过项目管道时被丢弃时调用此方法。它格式化一条包含导致项目被丢弃的异常
        和项目详细信息的日志消息。

        Args:
            item: The item that was dropped.
                 被丢弃的项目。
            exception: The exception that caused the item to be dropped.
                      导致项目被丢弃的异常。
            response: The response from which the item was scraped.
                     项目被抓取的响应。
            spider: The spider that scraped the item.
                   抓取项目的爬虫。

        Returns:
            dict: A dictionary with log level and message.
                 包含日志级别和消息的字典。
        """
        # Return a dictionary with log level and formatted message
        # 返回包含日志级别和格式化消息的字典
        return {
            '_Logger__level': "WARNING",
            '_Logger__message': DROPPEDMSG % {
                'exception': exception,
                'item': item,
            }
        }

    @staticmethod
    def item_error(item, exception, response, spider):
        """
        Format a log message for an item processing error.
        格式化项目处理错误的日志消息。

        This method is called when an item causes an error while passing through the item pipeline.
        It formats a log message that includes the item details.
        当项目在通过项目管道时导致错误时调用此方法。它格式化一条包含项目详细信息的日志消息。

        Args:
            item: The item that caused the error.
                 导致错误的项目。
            exception: The exception that was raised.
                      引发的异常。
            response: The response from which the item was scraped.
                     项目被抓取的响应。
            spider: The spider that scraped the item.
                   抓取项目的爬虫。

        Returns:
            str: A formatted log message.
                格式化的日志消息。

        .. versionadded:: 2.0
        """
        # Return a formatted message with the item details
        # 返回包含项目详细信息的格式化消息
        return ITEMERRORMSG % {
            'item': item,
        }

    @staticmethod
    def spider_error(failure, request, response, spider):
        """
        Format a log message for a spider error.
        格式化爬虫错误的日志消息。

        This method is called when a spider raises an exception while processing a response.
        It formats a log message that includes the request URL and referer.
        当爬虫在处理响应时引发异常时调用此方法。它格式化一条包含请求URL和引用者的日志消息。

        Args:
            failure: The failure that occurred.
                    发生的失败。
            request: The request that was being processed.
                    正在处理的请求。
            response: The response that was being processed.
                     正在处理的响应。
            spider: The spider that raised the exception.
                   引发异常的爬虫。

        Returns:
            str: A formatted log message.
                格式化的日志消息。

        .. versionadded:: 2.0
        """
        # Return a formatted message with the request and referer
        # 返回包含请求和引用者的格式化消息
        return SPIDERERRORMSG % {
            'request': request,
            'referer': referer_str(request),
        }

    @staticmethod
    def download_error(failure, request, spider, errmsg=None):
        """
        Format a log message for a download error.
        格式化下载错误的日志消息。

        This method is called when there is an error downloading a request.
        It formats a log message that includes the request URL and optionally the error message.
        当下载请求时出错时调用此方法。它格式化一条包含请求URL和可选的错误消息的日志消息。

        Args:
            failure: The failure that occurred.
                    发生的失败。
            request: The request that failed to download.
                    下载失败的请求。
            spider: The spider that made the request.
                   发出请求的爬虫。
            errmsg: An optional error message.
                   可选的错误消息。
                   Defaults to None.
                   默认为None。

        Returns:
            str: A formatted log message.
                格式化的日志消息。

        .. versionadded:: 2.0
        """
        # Prepare arguments for the message
        # 准备消息的参数
        args = {'request': request}

        # Choose the appropriate message template based on whether an error message is provided
        # 根据是否提供错误消息选择适当的消息模板
        if errmsg:
            msg = DOWNLOADERRORMSG_LONG
            args['errmsg'] = errmsg
        else:
            msg = DOWNLOADERRORMSG_SHORT

        # Return the formatted message
        # 返回格式化的消息
        return msg % args

    @classmethod
    def from_crawler(cls, crawler):
        """
        Create a LogFormatter instance from a crawler.
        从爬虫创建LogFormatter实例。

        This is the factory method used by AioScrapy to create the log formatter.
        这是AioScrapy用于创建日志格式化器的工厂方法。

        Args:
            crawler: The crawler that will use this log formatter.
                    将使用此日志格式化器的爬虫。

        Returns:
            LogFormatter: A new LogFormatter instance.
                         一个新的LogFormatter实例。
        """
        # Create and return a new instance
        # 创建并返回一个新实例
        return cls()
