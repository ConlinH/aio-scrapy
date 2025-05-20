"""
DefaultHeaders Downloader Middleware
默认头部下载器中间件

This middleware sets default headers for all requests, as specified in the
DEFAULT_REQUEST_HEADERS setting. These headers are only set if they are not
already present in the request.
此中间件为所有请求设置默认头部，如DEFAULT_REQUEST_HEADERS设置中指定的那样。
这些头部仅在请求中尚未存在时才会设置。
"""

from aioscrapy.utils.python import without_none_values


class DefaultHeadersMiddleware:
    """
    Middleware for setting default headers on requests.
    用于在请求上设置默认头部的中间件。

    This middleware adds default headers to all outgoing requests, as specified in the
    DEFAULT_REQUEST_HEADERS setting. Headers are only added if they are not already
    present in the request, allowing request-specific headers to take precedence.
    此中间件向所有传出请求添加默认头部，如DEFAULT_REQUEST_HEADERS设置中指定的那样。
    仅当请求中尚未存在头部时才会添加头部，允许特定于请求的头部优先。
    """

    def __init__(self, headers):
        """
        Initialize the DefaultHeadersMiddleware.
        初始化DefaultHeadersMiddleware。

        Args:
            headers: An iterable of (name, value) pairs representing the default headers.
                    表示默认头部的(名称, 值)对的可迭代对象。
        """
        # Store the default headers
        # 存储默认头部
        self._headers = headers

    @classmethod
    def from_crawler(cls, crawler):
        """
        Create a DefaultHeadersMiddleware instance from a crawler.
        从爬虫创建DefaultHeadersMiddleware实例。

        This is the factory method used by AioScrapy to create the middleware.
        这是AioScrapy用于创建中间件的工厂方法。

        Args:
            crawler: The crawler that will use this middleware.
                    将使用此中间件的爬虫。

        Returns:
            DefaultHeadersMiddleware: A new DefaultHeadersMiddleware instance.
                                     一个新的DefaultHeadersMiddleware实例。
        """
        # Get the default headers from settings, filtering out None values
        # 从设置获取默认头部，过滤掉None值
        headers = without_none_values(crawler.settings['DEFAULT_REQUEST_HEADERS'])

        # Create and return a new instance with the headers as (name, value) pairs
        # 使用作为(名称, 值)对的头部创建并返回一个新实例
        return cls(headers.items())

    def process_request(self, request, spider):
        """
        Process a request before it is sent to the downloader.
        在请求发送到下载器之前处理它。

        This method adds the default headers to the request if they are not already present.
        如果请求中尚未存在默认头部，此方法会将其添加到请求中。

        Args:
            request: The request being processed.
                    正在处理的请求。
            spider: The spider that generated the request.
                   生成请求的爬虫。

        Returns:
            None: This method does not return a response or a deferred.
                 此方法不返回响应或延迟对象。
        """
        # Add each default header to the request if it's not already set
        # 如果尚未设置，则将每个默认头部添加到请求中
        for k, v in self._headers:
            request.headers.setdefault(k, v)
