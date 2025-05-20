"""
Download Timeout Middleware
下载超时中间件

This middleware sets a default timeout for all requests, as specified in the
DOWNLOAD_TIMEOUT setting or the spider's download_timeout attribute. The timeout
can be overridden on a per-request basis by setting the 'download_timeout' key
in the request's meta dictionary.
此中间件为所有请求设置默认超时，如DOWNLOAD_TIMEOUT设置或爬虫的download_timeout
属性中指定的那样。可以通过在请求的meta字典中设置'download_timeout'键来覆盖每个
请求的超时。
"""

from aioscrapy import signals


class DownloadTimeoutMiddleware:
    """
    Middleware for setting default download timeouts on requests.
    用于在请求上设置默认下载超时的中间件。

    This middleware sets a default timeout for all outgoing requests, as specified in the
    DOWNLOAD_TIMEOUT setting or the spider's download_timeout attribute. The timeout
    can be overridden on a per-request basis by setting the 'download_timeout' key
    in the request's meta dictionary.
    此中间件为所有传出请求设置默认超时，如DOWNLOAD_TIMEOUT设置或爬虫的download_timeout
    属性中指定的那样。可以通过在请求的meta字典中设置'download_timeout'键来覆盖每个
    请求的超时。
    """

    def __init__(self, timeout=180):
        """
        Initialize the DownloadTimeoutMiddleware.
        初始化DownloadTimeoutMiddleware。

        Args:
            timeout: The default download timeout in seconds.
                    默认下载超时（以秒为单位）。
                    Defaults to 180 seconds.
                    默认为180秒。
        """
        # Store the default timeout
        # 存储默认超时
        self._timeout = timeout

    @classmethod
    def from_crawler(cls, crawler):
        """
        Create a DownloadTimeoutMiddleware instance from a crawler.
        从爬虫创建DownloadTimeoutMiddleware实例。

        This is the factory method used by AioScrapy to create the middleware.
        这是AioScrapy用于创建中间件的工厂方法。

        Args:
            crawler: The crawler that will use this middleware.
                    将使用此中间件的爬虫。

        Returns:
            DownloadTimeoutMiddleware: A new DownloadTimeoutMiddleware instance.
                                      一个新的DownloadTimeoutMiddleware实例。
        """
        # Create a new instance with the timeout from settings
        # 使用来自设置的超时创建一个新实例
        o = cls(crawler.settings.getfloat('DOWNLOAD_TIMEOUT'))

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

        This method is called when a spider is opened. It updates the default timeout
        with the spider's download_timeout attribute if it exists.
        当爬虫打开时调用此方法。如果存在，它会使用爬虫的download_timeout属性更新默认超时。

        Args:
            spider: The spider that was opened.
                   被打开的爬虫。
        """
        # Update the timeout with the spider's download_timeout attribute if it exists
        # 如果存在，则使用爬虫的download_timeout属性更新超时
        self._timeout = getattr(spider, 'download_timeout', self._timeout)

    def process_request(self, request, spider):
        """
        Process a request before it is sent to the downloader.
        在请求发送到下载器之前处理它。

        This method sets the default download timeout in the request's meta dictionary
        if it's not already set and if a default timeout is configured.
        如果尚未设置默认下载超时且已配置默认超时，此方法会在请求的meta字典中设置它。

        Args:
            request: The request being processed.
                    正在处理的请求。
            spider: The spider that generated the request.
                   生成请求的爬虫。

        Returns:
            None: This method does not return a response or a deferred.
                 此方法不返回响应或延迟对象。
        """
        # Set the default download timeout in the request's meta if it's not already set
        # and if a default timeout is configured
        # 如果尚未设置默认下载超时且已配置默认超时，则在请求的meta中设置它
        if self._timeout:
            request.meta.setdefault('download_timeout', self._timeout)
