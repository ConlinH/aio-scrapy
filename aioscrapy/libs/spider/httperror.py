"""
HttpError Spider Middleware
HTTP错误爬虫中间件

This middleware filters out responses with non-200 status codes and generates
appropriate exceptions. It allows you to specify which status codes should be
allowed through to the spider via settings or meta attributes.
此中间件过滤掉具有非200状态码的响应并生成适当的异常。它允许您通过设置或
元属性指定哪些状态码应该被允许传递给爬虫。
"""

from aioscrapy.exceptions import IgnoreRequest
from aioscrapy.utils.log import logger


class HttpError(IgnoreRequest):
    """
    Exception raised when a non-200 response is filtered.
    当过滤非200响应时引发的异常。

    This exception is raised by the HttpErrorMiddleware when it encounters a
    response with a status code that is not in the allowed list. It is a subclass
    of IgnoreRequest, which means the response will be ignored by the spider.
    当HttpErrorMiddleware遇到状态码不在允许列表中的响应时，会引发此异常。
    它是IgnoreRequest的子类，这意味着该响应将被爬虫忽略。
    """

    def __init__(self, response, *args, **kwargs):
        """
        Initialize the HttpError exception.
        初始化HttpError异常。

        Args:
            response: The response that triggered the exception.
                     触发异常的响应。
            *args: Variable length argument list passed to the parent class.
                  传递给父类的可变长度参数列表。
            **kwargs: Arbitrary keyword arguments passed to the parent class.
                     传递给父类的任意关键字参数。
        """
        # Store the response that triggered the exception
        # 存储触发异常的响应
        self.response = response

        # Initialize the parent IgnoreRequest class
        # 初始化父类IgnoreRequest
        super().__init__(*args, **kwargs)


class HttpErrorMiddleware:
    """
    Spider middleware to filter out responses with non-200 status codes.
    用于过滤掉具有非200状态码的响应的爬虫中间件。

    This middleware checks the status code of each response and raises an HttpError
    exception for responses with status codes that are not in the allowed list.
    The allowed list can be specified via settings, spider attributes, or response
    meta attributes.
    此中间件检查每个响应的状态码，并为状态码不在允许列表中的响应引发HttpError异常。
    允许列表可以通过设置、爬虫属性或响应元属性指定。
    """

    @classmethod
    def from_crawler(cls, crawler):
        """
        Create a HttpErrorMiddleware instance from a crawler.
        从爬虫创建HttpErrorMiddleware实例。

        This is the factory method used by AioScrapy to create the middleware.
        这是AioScrapy用于创建中间件的工厂方法。

        Args:
            crawler: The crawler that will use this middleware.
                    将使用此中间件的爬虫。

        Returns:
            HttpErrorMiddleware: A new HttpErrorMiddleware instance.
                                一个新的HttpErrorMiddleware实例。
        """
        # Create and return a new instance with the crawler's settings
        # 使用爬虫的设置创建并返回一个新实例
        return cls(crawler.settings)

    def __init__(self, settings):
        """
        Initialize the HttpErrorMiddleware.
        初始化HttpErrorMiddleware。

        Args:
            settings: The AioScrapy settings object.
                     AioScrapy设置对象。
        """
        # Whether to allow all HTTP status codes
        # 是否允许所有HTTP状态码
        self.handle_httpstatus_all = settings.getbool('HTTPERROR_ALLOW_ALL')

        # List of allowed HTTP status codes
        # 允许的HTTP状态码列表
        self.handle_httpstatus_list = settings.getlist('HTTPERROR_ALLOWED_CODES')

    def process_spider_input(self, response, spider):
        """
        Process a response before it is sent to the spider.
        在响应发送到爬虫之前处理它。

        This method checks if the response's status code is allowed. If not, it
        raises an HttpError exception, which will be caught by process_spider_exception.
        此方法检查响应的状态码是否被允许。如果不允许，它会引发HttpError异常，
        该异常将被process_spider_exception捕获。

        Args:
            response: The response being processed.
                     正在处理的响应。
            spider: The spider that will receive the response.
                   将接收响应的爬虫。

        Raises:
            HttpError: If the response's status code is not allowed.
                      如果响应的状态码不被允许。
        """
        # Allow responses with status codes in the 200-299 range (common case)
        # 允许状态码在200-299范围内的响应（常见情况）
        if 200 <= response.status < 300:
            return

        # Allow all status codes if specified in the response meta
        # 如果在响应元数据中指定，则允许所有状态码
        if response.meta.get('handle_httpstatus_all', False):
            return

        # Get the list of allowed status codes
        # 获取允许的状态码列表
        if 'handle_httpstatus_list' in response.meta:
            # Use the list from response meta if available
            # 如果可用，使用来自响应元数据的列表
            allowed_statuses = response.meta['handle_httpstatus_list']
        elif self.handle_httpstatus_all:
            # Allow all status codes if specified in settings
            # 如果在设置中指定，则允许所有状态码
            return
        else:
            # Use the list from spider attribute or middleware settings
            # 使用来自爬虫属性或中间件设置的列表
            allowed_statuses = getattr(spider, 'handle_httpstatus_list', self.handle_httpstatus_list)

        # Allow the response if its status code is in the allowed list
        # 如果响应的状态码在允许列表中，则允许该响应
        if response.status in allowed_statuses:
            return

        # Raise an HttpError for responses with disallowed status codes
        # 为具有不允许状态码的响应引发HttpError
        raise HttpError(response, 'Ignoring non-200 response')

    async def process_spider_exception(self, response, exception, spider):
        """
        Handle exceptions raised during spider processing.
        处理爬虫处理期间引发的异常。

        This method catches HttpError exceptions, logs them, updates statistics,
        and returns an empty result list to suppress the exception.
        此方法捕获HttpError异常，记录它们，更新统计信息，并返回一个空结果列表以抑制异常。

        Args:
            response: The response being processed when the exception was raised.
                     引发异常时正在处理的响应。
            exception: The exception raised.
                      引发的异常。
            spider: The spider that was processing the response.
                   正在处理响应的爬虫。

        Returns:
            list: An empty list if the exception is an HttpError, None otherwise.
                 如果异常是HttpError，则返回空列表；否则返回None。
        """
        # Only handle HttpError exceptions
        # 只处理HttpError异常
        if isinstance(exception, HttpError):
            # Update statistics
            # 更新统计信息
            spider.crawler.stats.inc_value('httperror/response_ignored_count')
            spider.crawler.stats.inc_value(
                f'httperror/response_ignored_status_count/{response.status}'
            )

            # Log the ignored response
            # 记录被忽略的响应
            logger.info("Ignoring response %(response)r: HTTP status code is not handled or not allowed" % {
                'response': response
            })

            # Return an empty list to suppress the exception
            # 返回空列表以抑制异常
            return []
