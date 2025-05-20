"""
User-Agent Middleware
用户代理中间件

This middleware sets the User-Agent header for all requests, using either a
spider-specific user_agent attribute, or a default value from the USER_AGENT setting.
此中间件为所有请求设置User-Agent头，使用爬虫特定的user_agent属性，
或来自USER_AGENT设置的默认值。

The User-Agent header is important for identifying your crawler to websites and
can affect how websites respond to your requests.
User-Agent头对于向网站标识您的爬虫很重要，可能会影响网站对您的请求的响应方式。
"""

from aioscrapy import signals


class UserAgentMiddleware:
    """
    Middleware for setting the User-Agent header on requests.
    用于在请求上设置User-Agent头的中间件。

    This middleware allows spiders to override the default User-Agent by specifying
    a user_agent attribute. If no spider-specific User-Agent is defined, it uses
    the default value from the USER_AGENT setting.
    此中间件允许爬虫通过指定user_agent属性来覆盖默认的User-Agent。
    如果未定义爬虫特定的User-Agent，则使用USER_AGENT设置中的默认值。
    """

    def __init__(self, user_agent='Scrapy'):
        """
        Initialize the UserAgentMiddleware.
        初始化UserAgentMiddleware。

        Args:
            user_agent: The default User-Agent string to use.
                       要使用的默认User-Agent字符串。
                       Defaults to 'Scrapy'.
                       默认为'Scrapy'。
        """
        # Store the default user agent
        # 存储默认用户代理
        self.user_agent = user_agent

    @classmethod
    def from_crawler(cls, crawler):
        """
        Create a UserAgentMiddleware instance from a crawler.
        从爬虫创建UserAgentMiddleware实例。

        This is the factory method used by AioScrapy to create the middleware.
        这是AioScrapy用于创建中间件的工厂方法。

        Args:
            crawler: The crawler that will use this middleware.
                    将使用此中间件的爬虫。

        Returns:
            UserAgentMiddleware: A new UserAgentMiddleware instance.
                               一个新的UserAgentMiddleware实例。
        """
        # Create a new instance with the user agent from settings
        # 使用来自设置的用户代理创建一个新实例
        o = cls(crawler.settings['USER_AGENT'])

        # Connect to the spider_opened signal
        # 连接到spider_opened信号
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)

        # Return the new instance
        # 返回新实例
        return o

    def spider_opened(self, spider):
        """
        Handle the spider_opened signal.
        处理spider_opened信号。

        This method is called when a spider is opened. It updates the user agent
        with the spider's user_agent attribute if it exists.
        当爬虫打开时调用此方法。如果存在，它会使用爬虫的user_agent属性更新用户代理。

        Args:
            spider: The spider that was opened.
                   被打开的爬虫。
        """
        # Update the user agent with the spider's user_agent attribute if it exists
        # 如果存在，则使用爬虫的user_agent属性更新用户代理
        self.user_agent = getattr(spider, 'user_agent', self.user_agent)

    def process_request(self, request, spider):
        """
        Process a request before it is sent to the downloader.
        在请求发送到下载器之前处理它。

        This method sets the User-Agent header in the request if it's not already set
        and if a user agent is configured.
        如果尚未设置User-Agent头且已配置用户代理，此方法会在请求中设置它。

        Args:
            request: The request being processed.
                    正在处理的请求。
            spider: The spider that generated the request.
                   生成请求的爬虫。

        Returns:
            None: This method does not return a response or a deferred.
                 此方法不返回响应或延迟对象。
        """
        # Set the User-Agent header in the request if it's not already set
        # and if a user agent is configured
        # 如果尚未设置User-Agent头且已配置用户代理，则在请求中设置它
        if self.user_agent:
            request.headers.setdefault('User-Agent', self.user_agent)
