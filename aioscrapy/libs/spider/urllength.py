"""
Url Length Spider Middleware
URL长度爬虫中间件

This middleware filters out requests with URLs that exceed a configurable maximum
length. It helps prevent issues with excessively long URLs that might cause problems
with servers, proxies, or browsers.
此中间件过滤掉URL超过可配置最大长度的请求。它有助于防止过长的URL可能导致
服务器、代理或浏览器出现问题。
"""

from aioscrapy.exceptions import NotConfigured
from aioscrapy.http import Request
from aioscrapy.utils.log import logger


class UrlLengthMiddleware:
    """
    Spider middleware to filter out requests with excessively long URLs.
    用于过滤掉URL过长的请求的爬虫中间件。

    This middleware checks the length of URLs in requests and filters out those
    that exceed a configurable maximum length. This helps prevent issues with
    servers, proxies, or browsers that might have trouble handling very long URLs.
    此中间件检查请求中URL的长度，并过滤掉超过可配置最大长度的URL。
    这有助于防止服务器、代理或浏览器在处理非常长的URL时可能遇到的问题。
    """

    def __init__(self, maxlength):
        """
        Initialize the URL length middleware.
        初始化URL长度中间件。

        Args:
            maxlength: The maximum allowed URL length in characters.
                      允许的URL最大长度（以字符为单位）。
        """
        # Maximum allowed URL length
        # 允许的URL最大长度
        self.maxlength = maxlength

    @classmethod
    def from_settings(cls, settings):
        """
        Create a UrlLengthMiddleware instance from settings.
        从设置创建UrlLengthMiddleware实例。

        This is the factory method used by AioScrapy to create the middleware.
        这是AioScrapy用于创建中间件的工厂方法。

        Args:
            settings: The AioScrapy settings object.
                     AioScrapy设置对象。

        Returns:
            UrlLengthMiddleware: A new UrlLengthMiddleware instance.
                                一个新的UrlLengthMiddleware实例。

        Raises:
            NotConfigured: If URLLENGTH_LIMIT is not set or is zero in the settings.
                          如果在设置中未设置URLLENGTH_LIMIT或其值为零。
        """
        # Get the maximum URL length from settings
        # 从设置获取最大URL长度
        maxlength = settings.getint('URLLENGTH_LIMIT')

        # If no maximum length is configured, disable the middleware
        # 如果未配置最大长度，则禁用中间件
        if not maxlength:
            raise NotConfigured

        # Create and return a new instance
        # 创建并返回一个新实例
        return cls(maxlength)

    async def process_spider_output(self, response, result, spider):
        """
        Process the spider output to filter out requests with long URLs.
        处理爬虫输出以过滤掉具有长URL的请求。

        This method processes each request yielded by the spider and filters out
        those with URLs that exceed the configured maximum length.
        此方法处理爬虫产生的每个请求，并过滤掉URL超过配置的最大长度的请求。

        Args:
            response: The response being processed.
                     正在处理的响应。
            result: The result returned by the spider.
                   爬虫返回的结果。
            spider: The spider that generated the result.
                   生成结果的爬虫。

        Returns:
            An async generator yielding filtered requests and other items.
            一个产生过滤后的请求和其他项目的异步生成器。
        """
        def _filter(request):
            """
            Filter function to check if a request's URL is too long.
            检查请求的URL是否过长的过滤函数。

            Args:
                request: The request to check.
                         要检查的请求。

            Returns:
                bool: True if the request should be kept, False if it should be filtered out.
                     如果应保留请求，则为True；如果应过滤掉请求，则为False。
            """
            # Check if the item is a Request and if its URL exceeds the maximum length
            # 检查项目是否为Request，以及其URL是否超过最大长度
            if isinstance(request, Request) and len(request.url) > self.maxlength:
                # Log the ignored request
                # 记录被忽略的请求
                logger.info(
                    "Ignoring link (url length > %(maxlength)d): %(url)s " % {
                        'maxlength': self.maxlength, 'url': request.url
                    }
                )
                # Update statistics
                # 更新统计信息
                spider.crawler.stats.inc_value('urllength/request_ignored_count', spider=spider)
                # Filter out this request
                # 过滤掉此请求
                return False
            else:
                # Keep all other items
                # 保留所有其他项目
                return True

        # Filter the results using the _filter function
        # 使用_filter函数过滤结果
        return (r async for r in result or () if _filter(r))
