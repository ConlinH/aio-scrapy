"""
Downloader Statistics Middleware for AioScrapy
AioScrapy的下载器统计中间件

This module provides a middleware that collects statistics about the downloader
component, including request and response counts, bytes transferred, HTTP methods,
response status codes, and exceptions.
此模块提供了一个中间件，用于收集有关下载器组件的统计信息，
包括请求和响应计数、传输的字节数、HTTP方法、响应状态码和异常。
"""

from aioscrapy.exceptions import NotConfigured
from aioscrapy.utils.request import request_httprepr
from aioscrapy.utils.python import global_object_name


class DownloaderStats:
    """
    Middleware to collect statistics about the downloader component.
    用于收集下载器组件统计信息的中间件。

    This middleware collects various statistics about the downloader component,
    such as the number of requests and responses, bytes transferred, HTTP methods used,
    response status codes, and exceptions encountered. These statistics are stored
    in the crawler's stats collector and can be used for monitoring and debugging.
    此中间件收集有关下载器组件的各种统计信息，例如请求和响应的数量、
    传输的字节数、使用的HTTP方法、响应状态码和遇到的异常。
    这些统计信息存储在爬虫的统计收集器中，可用于监控和调试。
    """

    def __init__(self, stats):
        """
        Initialize the DownloaderStats middleware.
        初始化DownloaderStats中间件。

        Args:
            stats: The stats collector instance to use for storing statistics.
                  用于存储统计信息的统计收集器实例。
        """
        self.stats = stats

    @classmethod
    def from_crawler(cls, crawler):
        """
        Create a DownloaderStats instance from a crawler.
        从爬虫创建DownloaderStats实例。

        This is the factory method used by AioScrapy to create middleware instances.
        It checks if the DOWNLOADER_STATS setting is enabled before creating the middleware.
        这是AioScrapy用于创建中间件实例的工厂方法。
        它在创建中间件之前检查DOWNLOADER_STATS设置是否启用。

        Args:
            crawler: The crawler that will use this middleware.
                    将使用此中间件的爬虫。

        Returns:
            DownloaderStats: A new DownloaderStats instance.
                            一个新的DownloaderStats实例。

        Raises:
            NotConfigured: If DOWNLOADER_STATS setting is disabled.
                          如果DOWNLOADER_STATS设置被禁用。
        """
        if not crawler.settings.getbool('DOWNLOADER_STATS'):
            raise NotConfigured
        return cls(crawler.stats)

    def process_request(self, request, spider):
        """
        Process a request to collect request statistics.
        处理请求以收集请求统计信息。

        This method is called for every request that passes through the middleware.
        It increments counters for the total number of requests, requests by HTTP method,
        and the total number of bytes in requests.
        此方法在每个通过中间件的请求上调用。
        它增加总请求数、按HTTP方法的请求数和请求中的总字节数的计数器。

        Args:
            request: The request being processed.
                    正在处理的请求。
            spider: The spider that generated the request.
                   生成请求的爬虫。

        Returns:
            None: This method returns None to continue processing the request.
                 此方法返回None以继续处理请求。
        """
        # Increment the total request count
        # 增加总请求计数
        self.stats.inc_value('downloader/request_count', spider=spider)

        # Increment the count for this specific HTTP method
        # 增加此特定HTTP方法的计数
        self.stats.inc_value(f'downloader/request_method_count/{request.method}', spider=spider)

        # Add the request size to the total bytes counter
        # 将请求大小添加到总字节计数器
        self.stats.inc_value('downloader/request_bytes', len(request_httprepr(request)), spider=spider)

    def process_response(self, request, response, spider):
        """
        Process a response to collect response statistics.
        处理响应以收集响应统计信息。

        This method is called for every response that passes through the middleware.
        It increments counters for the total number of responses, responses by status code,
        and the total number of bytes in responses.
        此方法在每个通过中间件的响应上调用。
        它增加总响应数、按状态码的响应数和响应中的总字节数的计数器。

        Args:
            request: The request that generated this response.
                    生成此响应的请求。
            response: The response being processed.
                     正在处理的响应。
            spider: The spider that generated the request.
                   生成请求的爬虫。

        Returns:
            Response: The response object, unchanged.
                     响应对象，未更改。
        """
        # Increment the total response count
        # 增加总响应计数
        self.stats.inc_value('downloader/response_count', spider=spider)

        # Increment the count for this specific status code
        # 增加此特定状态码的计数
        self.stats.inc_value(f'downloader/response_status_count/{response.status}', spider=spider)

        # Add the response size to the total bytes counter
        # 将响应大小添加到总字节计数器
        self.stats.inc_value('downloader/response_bytes', len(response.body), spider=spider)

        # Return the response unchanged
        # 返回未更改的响应
        return response

    def process_exception(self, request, exception, spider):
        """
        Process an exception to collect exception statistics.
        处理异常以收集异常统计信息。

        This method is called when an exception occurs during request processing.
        It increments counters for the total number of exceptions and exceptions by type.
        当请求处理期间发生异常时调用此方法。
        它增加总异常数和按类型的异常数的计数器。

        Args:
            request: The request that caused the exception.
                    导致异常的请求。
            exception: The exception that was raised.
                      引发的异常。
            spider: The spider that generated the request.
                   生成请求的爬虫。

        Returns:
            None: This method returns None to continue processing the exception.
                 此方法返回None以继续处理异常。
        """
        # Get the full class name of the exception
        # 获取异常的完整类名
        ex_class = global_object_name(exception.__class__)

        # Increment the total exception count
        # 增加总异常计数
        self.stats.inc_value('downloader/exception_count', spider=spider)

        # Increment the count for this specific exception type
        # 增加此特定异常类型的计数
        self.stats.inc_value(f'downloader/exception_type_count/{ex_class}', spider=spider)
