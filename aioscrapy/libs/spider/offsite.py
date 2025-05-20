"""
Offsite Spider Middleware
站外爬虫中间件

This middleware filters out requests to URLs not belonging to the domains specified
in the spider's allowed_domains attribute. It helps prevent the crawler from
following links to external sites, which is useful for keeping crawls focused on
specific domains.
此中间件过滤掉对不属于爬虫的allowed_domains属性中指定的域的URL的请求。
它有助于防止爬虫跟随指向外部站点的链接，这对于使爬取集中在特定域上很有用。
"""
import re
import warnings

from aioscrapy import signals
from aioscrapy.http import Request
from aioscrapy.utils.httpobj import urlparse_cached
from aioscrapy.utils.log import logger


class OffsiteMiddleware:
    """
    Spider middleware to filter out requests to offsite domains.
    用于过滤掉对站外域的请求的爬虫中间件。

    This middleware filters out requests to URLs not belonging to the domains specified
    in the spider's allowed_domains attribute. It helps prevent the crawler from
    following links to external sites, which is useful for keeping crawls focused on
    specific domains.
    此中间件过滤掉对不属于爬虫的allowed_domains属性中指定的域的URL的请求。
    它有助于防止爬虫跟随指向外部站点的链接，这对于使爬取集中在特定域上很有用。
    """

    def __init__(self, stats):
        """
        Initialize the offsite middleware.
        初始化站外中间件。

        Args:
            stats: Stats collector instance.
                  统计收集器实例。
        """
        # Stats collector instance
        # 统计收集器实例
        self.stats = stats

    @classmethod
    def from_crawler(cls, crawler):
        """
        Create an OffsiteMiddleware instance from a crawler.
        从爬虫创建OffsiteMiddleware实例。

        This is the factory method used by AioScrapy to create the middleware.
        这是AioScrapy用于创建中间件的工厂方法。

        Args:
            crawler: The crawler that will use this middleware.
                    将使用此中间件的爬虫。

        Returns:
            OffsiteMiddleware: A new OffsiteMiddleware instance.
                              一个新的OffsiteMiddleware实例。
        """
        # Create a new instance with the crawler's stats collector
        # 使用爬虫的统计收集器创建一个新实例
        o = cls(crawler.stats)

        # Connect the spider_opened method to the spider_opened signal
        # 将spider_opened方法连接到spider_opened信号
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)

        # Return the new instance
        # 返回新实例
        return o

    async def process_spider_output(self, response, result, spider):
        """
        Process the spider output to filter out offsite requests.
        处理爬虫输出以过滤掉站外请求。

        This method processes each request yielded by the spider and filters out
        requests to URLs not belonging to the domains specified in the spider's
        allowed_domains attribute.
        此方法处理爬虫产生的每个请求，并过滤掉对不属于爬虫的allowed_domains属性中
        指定的域的URL的请求。

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
        # Process each item in the result
        # 处理结果中的每个项目
        async for x in result:
            # If the item is a Request, check if it should be followed
            # 如果项目是一个Request，检查是否应该跟随它
            if isinstance(x, Request):
                # If the request has dont_filter set or it's for an allowed domain, yield it
                # 如果请求设置了dont_filter或它是针对允许的域，则产生它
                if x.dont_filter or self.should_follow(x, spider):
                    yield x
                else:
                    # Get the domain of the request
                    # 获取请求的域
                    domain = urlparse_cached(x).hostname

                    # If this is a new domain, log it and update stats
                    # 如果这是一个新域，记录它并更新统计信息
                    if domain and domain not in self.domains_seen:
                        self.domains_seen.add(domain)
                        logger.debug(
                            "Filtered offsite request to %(domain)r: %(request)s" % {'domain': domain, 'request': x}
                        )
                        self.stats.inc_value('offsite/domains', spider=spider)

                    # Update filtered requests stats
                    # 更新过滤的请求统计信息
                    self.stats.inc_value('offsite/filtered', spider=spider)
            else:
                # If the item is not a Request, yield it unchanged
                # 如果项目不是一个Request，则不变地产生它
                yield x

    def should_follow(self, request, spider):
        """
        Check if a request should be followed.
        检查是否应该跟随请求。

        This method checks if the hostname of the request URL matches the allowed
        domains pattern.
        此方法检查请求URL的主机名是否匹配允许的域模式。

        Args:
            request: The request to check.
                    要检查的请求。
            spider: The spider that generated the request.
                   生成请求的爬虫。

        Returns:
            bool: True if the request should be followed, False otherwise.
                 如果应该跟随请求，则为True；否则为False。
        """
        # Get the compiled regex pattern for allowed domains
        # 获取允许的域的编译正则表达式模式
        regex = self.host_regex

        # Get the hostname from the request URL
        # 从请求URL获取主机名
        # hostname can be None for wrong urls (like javascript links)
        # 对于错误的URL（如javascript链接），主机名可能为None
        host = urlparse_cached(request).hostname or ''

        # Check if the hostname matches the allowed domains pattern
        # 检查主机名是否匹配允许的域模式
        return bool(regex.search(host))

    def get_host_regex(self, spider):
        """
        Get a regex pattern for the allowed domains.
        获取允许的域的正则表达式模式。

        This method creates a regex pattern that matches hostnames belonging to
        the domains specified in the spider's allowed_domains attribute.
        此方法创建一个正则表达式模式，匹配属于爬虫的allowed_domains属性中指定的域的主机名。

        Args:
            spider: The spider whose allowed_domains attribute to use.
                   使用其allowed_domains属性的爬虫。

        Returns:
            re.Pattern: A compiled regex pattern for the allowed domains.
                       允许的域的编译正则表达式模式。

        Note:
            Override this method to implement a different offsite policy.
            覆盖此方法以实现不同的站外策略。
        """
        # Get the allowed_domains attribute from the spider
        # 从爬虫获取allowed_domains属性
        allowed_domains = getattr(spider, 'allowed_domains', None)

        # If no allowed_domains are specified, allow all domains
        # 如果未指定allowed_domains，则允许所有域
        if not allowed_domains:
            return re.compile('')  # allow all by default

        # Compile patterns for validating domains
        # 编译用于验证域的模式
        url_pattern = re.compile(r"^https?://.*$")
        port_pattern = re.compile(r":\d+$")

        # Process each domain in allowed_domains
        # 处理allowed_domains中的每个域
        domains = []
        for domain in allowed_domains:
            # Skip None values
            # 跳过None值
            if domain is None:
                continue
            # Warn about URL entries
            # 警告URL条目
            elif url_pattern.match(domain):
                message = ("allowed_domains accepts only domains, not URLs. "
                           f"Ignoring URL entry {domain} in allowed_domains.")
                warnings.warn(message, URLWarning)
            # Warn about domains with ports
            # 警告带有端口的域
            elif port_pattern.search(domain):
                message = ("allowed_domains accepts only domains without ports. "
                           f"Ignoring entry {domain} in allowed_domains.")
                warnings.warn(message, PortWarning)
            else:
                # Add valid domains to the list, escaping special regex characters
                # 将有效域添加到列表中，转义特殊的正则表达式字符
                domains.append(re.escape(domain))

        # Create a regex pattern that matches the allowed domains and their subdomains
        # 创建一个正则表达式模式，匹配允许的域及其子域
        regex = fr'^(.*\.)?({"|".join(domains)})$'

        # Compile and return the regex pattern
        # 编译并返回正则表达式模式
        return re.compile(regex)

    def spider_opened(self, spider):
        """
        Initialize middleware state when a spider is opened.
        当爬虫打开时初始化中间件状态。

        This method is called when a spider is opened. It initializes the regex
        pattern for allowed domains and the set of seen domains.
        当爬虫打开时调用此方法。它初始化允许的域的正则表达式模式和已见过的域集合。

        Args:
            spider: The spider that was opened.
                   被打开的爬虫。
        """
        # Initialize the regex pattern for allowed domains
        # 初始化允许的域的正则表达式模式
        self.host_regex = self.get_host_regex(spider)

        # Initialize the set of seen domains
        # 初始化已见过的域集合
        self.domains_seen = set()


class URLWarning(Warning):
    """
    Warning raised when a URL is provided in allowed_domains.
    当在allowed_domains中提供URL时引发的警告。

    This warning is raised by the OffsiteMiddleware when it encounters a URL
    (e.g., 'http://example.com') in the spider's allowed_domains attribute.
    The allowed_domains attribute should only contain domain names without
    the protocol (e.g., 'example.com').
    当OffsiteMiddleware在爬虫的allowed_domains属性中遇到URL
    （例如，'http://example.com'）时，会引发此警告。
    allowed_domains属性应该只包含没有协议的域名（例如，'example.com'）。
    """
    pass


class PortWarning(Warning):
    """
    Warning raised when a domain with port is provided in allowed_domains.
    当在allowed_domains中提供带有端口的域时引发的警告。

    This warning is raised by the OffsiteMiddleware when it encounters a domain
    with a port (e.g., 'example.com:8080') in the spider's allowed_domains attribute.
    The allowed_domains attribute should only contain domain names without
    ports (e.g., 'example.com').
    当OffsiteMiddleware在爬虫的allowed_domains属性中遇到带有端口的域
    （例如，'example.com:8080'）时，会引发此警告。
    allowed_domains属性应该只包含没有端口的域名（例如，'example.com'）。
    """
    pass
