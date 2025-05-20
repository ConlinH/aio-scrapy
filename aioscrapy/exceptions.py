"""
aioscrapy core exceptions
aioscrapy核心异常
"""


# Internal


class NotConfigured(Exception):
    """
    Indicates a missing configuration situation.
    表示缺少配置的情况。

    This exception is raised when a component or extension is not configured properly.
    当组件或扩展未正确配置时，会引发此异常。
    """
    pass


class _InvalidOutput(TypeError):
    """
    Indicates an invalid value has been returned by a middleware's processing method.
    表示中间件的处理方法返回了无效值。

    Internal and undocumented, it should not be raised or caught by user code.
    内部使用且未记录，不应由用户代码引发或捕获。
    """
    pass


# HTTP and crawling


class IgnoreRequest(Exception):
    """
    Indicates a decision was made not to process a request.
    表示已决定不处理请求。

    This exception can be raised by downloader middlewares to indicate that a request
    should be ignored and not processed further.
    下载器中间件可以引发此异常，以指示应忽略请求且不进一步处理。
    """


class DontCloseSpider(Exception):
    """
    Request the spider not to be closed yet.
    请求不要立即关闭爬虫。

    This exception can be raised in the spider_idle signal handler to prevent
    the spider from being closed when it becomes idle.
    可以在spider_idle信号处理程序中引发此异常，以防止爬虫在变为空闲状态时被关闭。
    """
    pass


class CloseSpider(Exception):
    """
    Raise this from callbacks to request the spider to be closed.
    从回调中引发此异常以请求关闭爬虫。

    This exception can be raised from a spider callback to request the spider to be
    closed with a specific reason.
    可以从爬虫回调中引发此异常，以请求以特定原因关闭爬虫。
    """

    def __init__(self, reason='cancelled'):
        """
        Initialize the exception with a reason.
        使用原因初始化异常。

        Args:
            reason: The reason for closing the spider. Default is 'cancelled'.
                   关闭爬虫的原因。默认为'cancelled'。
        """
        super().__init__()
        self.reason = reason


class StopDownload(Exception):
    """
    Stop the download of the body for a given response.
    停止给定响应的正文下载。

    The 'fail' boolean parameter indicates whether or not the resulting partial response
    should be handled by the request errback. Note that 'fail' is a keyword-only argument.
    'fail'布尔参数指示是否应由请求的errback处理结果部分响应。请注意，'fail'是仅关键字参数。

    This exception can be raised during the download process to stop downloading
    the response body, for example when only the headers are needed.
    可以在下载过程中引发此异常以停止下载响应正文，例如当只需要头信息时。
    """

    def __init__(self, *, fail=True):
        """
        Initialize the exception.
        初始化异常。

        Args:
            fail: Whether the partial response should be treated as a failure.
                 部分响应是否应被视为失败。
                 If True, the request's errback will be called.
                 如果为True，将调用请求的errback。
                 If False, the request's callback will be called with the partial response.
                 如果为False，将使用部分响应调用请求的callback。
        """
        super().__init__()
        self.fail = fail


# Items


class DropItem(Exception):
    """
    Drop item from the item pipeline.
    从项目管道中丢弃项目。

    This exception can be raised by item pipeline components to indicate that an item
    should not be processed further and should be dropped.
    项目管道组件可以引发此异常，以指示不应进一步处理项目并应将其丢弃。
    """
    pass


class NotSupported(Exception):
    """
    Indicates a feature or method is not supported.
    表示不支持某个功能或方法。

    This exception is raised when attempting to use a feature or method that is
    not supported by the current implementation or configuration.
    当尝试使用当前实现或配置不支持的功能或方法时，会引发此异常。
    """
    pass


# Commands


class UsageError(Exception):
    """
    To indicate a command-line usage error.
    表示命令行使用错误。

    This exception is raised when a command-line tool is used incorrectly,
    with invalid arguments or options.
    当命令行工具使用不正确、带有无效参数或选项时，会引发此异常。
    """

    def __init__(self, *a, **kw):
        """
        Initialize the exception.
        初始化异常。

        Args:
            *a: Positional arguments for the exception message.
                异常消息的位置参数。
            **kw: Keyword arguments. Special keyword 'print_help' controls whether
                  to print help information when the exception is caught.
                  关键字参数。特殊关键字'print_help'控制在捕获异常时是否打印帮助信息。
        """
        self.print_help = kw.pop('print_help', True)
        super().__init__(*a, **kw)


class AioScrapyDeprecationWarning(Warning):
    """
    Warning category for deprecated features, since the default
    DeprecationWarning is silenced on Python 2.7+
    已弃用功能的警告类别，因为默认的DeprecationWarning在Python 2.7+上被静默。

    This warning is used to indicate that a feature or API is deprecated and will be
    removed in a future version of aioscrapy.
    此警告用于指示某个功能或API已弃用，并将在aioscrapy的未来版本中删除。
    """
    pass


class ContractFail(AssertionError):
    """
    Error raised in case of a failing contract.
    在合约失败的情况下引发的错误。

    This exception is raised when a spider contract fails during testing.
    当爬虫合约在测试期间失败时，会引发此异常。
    Spider contracts are used to test the behavior of spiders.
    爬虫合约用于测试爬虫的行为。
    """
    pass


class ProxyException(Exception):
    """
    Exception related to proxy usage.
    与代理使用相关的异常。

    This exception is raised when there is an issue with proxy configuration,
    connection, or authentication.
    当代理配置、连接或认证出现问题时，会引发此异常。
    """
    pass


class DownloadError(Exception):
    """
    Error that occurs when downloading a page.
    下载页面时发生的错误。

    This exception wraps the original error that occurred during the download process,
    providing additional context and formatting.
    此异常包装了下载过程中发生的原始错误，提供额外的上下文和格式化。
    """

    def __init__(self, *args, real_error=None):
        """
        Initialize the exception.
        初始化异常。

        Args:
            *args: Positional arguments for the exception message.
                  异常消息的位置参数。
            real_error: The original error that caused the download to fail.
                       导致下载失败的原始错误。
        """
        self.real_error = real_error
        super().__init__(*args)

    def __str__(self):
        """
        Return a string representation of the exception.
        返回异常的字符串表示。

        If there is a real error, returns a string in the format:
        如果有真实错误，则返回格式为：
        "module.ErrorClass: error message"

        Returns:
            String representation of the exception.
            异常的字符串表示。
        """
        if not self.real_error:
            return "DownloadError"

        return f"{self.real_error.__class__.__module__}.{self.real_error.__class__.__name__}: {str(self.real_error)}"


if __name__ == '__main__':
    e = Exception("xxx")
    reason = DownloadError(real_error=e)
    print(reason)
    obj = reason.real_error.__class__
    print(f"{obj.__module__}.{obj.__name__}")
