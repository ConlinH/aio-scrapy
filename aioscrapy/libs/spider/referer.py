"""
Referer Middleware for AioScrapy
AioScrapy的Referer中间件

This middleware populates the 'Referer' HTTP header in requests based on the response
that generated them. It implements various referrer policies as defined in the W3C
Referrer Policy specification, allowing control over what information is included
in the Referer header for privacy and security reasons.
此中间件根据生成请求的响应填充请求中的'Referer' HTTP头。它实现了W3C Referer Policy
规范中定义的各种引用策略，允许出于隐私和安全原因控制Referer头中包含的信息。

The middleware supports all standard referrer policies:
中间件支持所有标准的引用策略：
- no-referrer
- no-referrer-when-downgrade
- same-origin
- origin
- strict-origin
- origin-when-cross-origin
- strict-origin-when-cross-origin
- unsafe-url
- aioscrapy-default (a variant of no-referrer-when-downgrade)
"""
import warnings
from typing import Tuple
from urllib.parse import urlparse

from w3lib.url import safe_url_string

from aioscrapy import signals
from aioscrapy.exceptions import NotConfigured
from aioscrapy.http import Request, Response
from aioscrapy.utils.misc import load_object
from aioscrapy.utils.python import to_unicode
from aioscrapy.utils.url import strip_url


LOCAL_SCHEMES = ('about', 'blob', 'data', 'filesystem',)

POLICY_NO_REFERRER = "no-referrer"
POLICY_NO_REFERRER_WHEN_DOWNGRADE = "no-referrer-when-downgrade"
POLICY_SAME_ORIGIN = "same-origin"
POLICY_ORIGIN = "origin"
POLICY_STRICT_ORIGIN = "strict-origin"
POLICY_ORIGIN_WHEN_CROSS_ORIGIN = "origin-when-cross-origin"
POLICY_STRICT_ORIGIN_WHEN_CROSS_ORIGIN = "strict-origin-when-cross-origin"
POLICY_UNSAFE_URL = "unsafe-url"
POLICY_AIOSCRAPY_DEFAULT = "aioscrapy-default"


class ReferrerPolicy:
    """
    Base class for implementing W3C Referrer Policy.
    实现W3C引用策略的基类。

    This abstract class defines the interface and common functionality for all
    referrer policy implementations. Each subclass implements a specific policy
    from the W3C Referrer Policy specification.
    这个抽象类为所有引用策略实现定义了接口和通用功能。每个子类实现W3C引用策略
    规范中的特定策略。

    Reference: https://www.w3.org/TR/referrer-policy/
    参考：https://www.w3.org/TR/referrer-policy/
    """

    # Schemes that should never send a referrer
    # 永远不应该发送引用的方案
    NOREFERRER_SCHEMES: Tuple[str, ...] = LOCAL_SCHEMES

    # Policy name (to be defined by subclasses)
    # 策略名称（由子类定义）
    name: str

    def referrer(self, response_url, request_url):
        """
        Determine the referrer value based on the policy.
        根据策略确定引用值。

        This method must be implemented by subclasses to determine what referrer
        value (if any) should be sent for a request, based on the response URL
        that generated the request and the request URL.
        此方法必须由子类实现，以根据生成请求的响应URL和请求URL确定应为请求
        发送什么引用值（如果有）。

        Args:
            response_url: The URL of the response that generated the request.
                         生成请求的响应的URL。
            request_url: The URL of the request being made.
                        正在发出的请求的URL。

        Returns:
            str or None: The referrer value to use, or None if no referrer should be sent.
                        要使用的引用值，如果不应发送引用，则为None。
        """
        raise NotImplementedError()

    def stripped_referrer(self, url):
        """
        Return a stripped version of the URL suitable for use as a referrer.
        返回适合用作引用的URL的剥离版本。

        This method strips sensitive information from a URL according to the
        referrer policy specification.
        此方法根据引用策略规范从URL中剥离敏感信息。

        Args:
            url: The URL to strip.
                要剥离的URL。

        Returns:
            str or None: The stripped URL, or None if the URL uses a scheme that
                        should never send a referrer.
                        剥离后的URL，如果URL使用的方案永远不应该发送引用，则为None。
        """
        if urlparse(url).scheme not in self.NOREFERRER_SCHEMES:
            return self.strip_url(url)
        return None

    def origin_referrer(self, url):
        """
        Return only the origin portion of a URL for use as a referrer.
        仅返回URL的源部分以用作引用。

        This method returns just the scheme, host, and port of a URL, which is
        useful for policies that only send the origin as the referrer.
        此方法仅返回URL的方案、主机和端口，这对于仅发送源作为引用的策略很有用。

        Args:
            url: The URL to get the origin from.
                要获取源的URL。

        Returns:
            str or None: The origin of the URL, or None if the URL uses a scheme that
                        should never send a referrer.
                        URL的源，如果URL使用的方案永远不应该发送引用，则为None。
        """
        if urlparse(url).scheme not in self.NOREFERRER_SCHEMES:
            return self.origin(url)
        return None

    def strip_url(self, url, origin_only=False):
        """
        Strip a URL according to the referrer policy specification.
        根据引用策略规范剥离URL。

        Reference: https://www.w3.org/TR/referrer-policy/#strip-url
        参考：https://www.w3.org/TR/referrer-policy/#strip-url

        If url is null, return no referrer.
        If url's scheme is a local scheme, then return no referrer.
        Set url's username to the empty string.
        Set url's password to null.
        Set url's fragment to null.
        If the origin-only flag is true, then:
            Set url's path to null.
            Set url's query to null.
        Return url.

        Args:
            url: The URL to strip.
                要剥离的URL。
            origin_only: Whether to strip the URL to just its origin.
                        是否将URL剥离为仅其源。

        Returns:
            str or None: The stripped URL, or None if the URL is empty.
                        剥离后的URL，如果URL为空，则为None。
        """
        if not url:
            return None
        return strip_url(url,
                         strip_credentials=True,
                         strip_fragment=True,
                         strip_default_port=True,
                         origin_only=origin_only)

    def origin(self, url):
        """
        Return serialized origin (scheme, host, port) for a URL.
        返回URL的序列化源（方案、主机、端口）。

        The origin of a URL is just its scheme, host, and port, without path,
        query, or fragment.
        URL的源只是其方案、主机和端口，没有路径、查询或片段。

        Args:
            url: The URL to get the origin from.
                要获取源的URL。

        Returns:
            str or None: The origin of the URL, or None if the URL is empty.
                        URL的源，如果URL为空，则为None。
        """
        return self.strip_url(url, origin_only=True)

    def potentially_trustworthy(self, url):
        """
        Determine if a URL is potentially trustworthy.
        确定URL是否可能值得信任。

        This is a simplified implementation that considers HTTPS and FTPS URLs
        as potentially trustworthy, and data URLs as not trustworthy.
        这是一个简化的实现，将HTTPS和FTPS URL视为可能值得信任，将数据URL视为不值得信任。

        Note: this does not follow the full algorithm from:
        注意：这不遵循以下完整算法：
        https://w3c.github.io/webappsec-secure-contexts/#is-url-trustworthy

        Args:
            url: The URL to check.
                要检查的URL。

        Returns:
            bool: True if the URL is potentially trustworthy, False otherwise.
                 如果URL可能值得信任，则为True，否则为False。
        """
        # Note: this does not follow https://w3c.github.io/webappsec-secure-contexts/#is-url-trustworthy
        parsed_url = urlparse(url)
        if parsed_url.scheme in ('data',):
            return False
        return self.tls_protected(url)

    def tls_protected(self, url):
        """
        Determine if a URL is protected by TLS (HTTPS or FTPS).
        确定URL是否受TLS（HTTPS或FTPS）保护。

        Args:
            url: The URL to check.
                要检查的URL。

        Returns:
            bool: True if the URL uses HTTPS or FTPS, False otherwise.
                 如果URL使用HTTPS或FTPS，则为True，否则为False。
        """
        return urlparse(url).scheme in ('https', 'ftps')


class NoReferrerPolicy(ReferrerPolicy):
    """
    Implementation of the "no-referrer" referrer policy.
    "no-referrer"引用策略的实现。

    Reference: https://www.w3.org/TR/referrer-policy/#referrer-policy-no-referrer
    参考：https://www.w3.org/TR/referrer-policy/#referrer-policy-no-referrer

    The simplest policy is "no-referrer", which specifies that no referrer information
    is to be sent along with requests made from a particular request client to any origin.
    The header will be omitted entirely.
    最简单的策略是"no-referrer"，它指定不随特定请求客户端向任何源发出的请求
    发送任何引用信息。头将完全省略。
    """
    # Policy name
    # 策略名称
    name: str = POLICY_NO_REFERRER

    def referrer(self, response_url, request_url):
        """
        Determine the referrer value based on the no-referrer policy.
        根据no-referrer策略确定引用值。

        This policy always returns None, meaning no Referer header should be sent.
        此策略始终返回None，表示不应发送Referer头。

        Args:
            response_url: The URL of the response that generated the request.
                         生成请求的响应的URL。
            request_url: The URL of the request being made.
                        正在发出的请求的URL。

        Returns:
            None: Always returns None, indicating no referrer should be sent.
                 始终返回None，表示不应发送引用。
        """
        return None


class NoReferrerWhenDowngradePolicy(ReferrerPolicy):
    """
    https://www.w3.org/TR/referrer-policy/#referrer-policy-no-referrer-when-downgrade

    The "no-referrer-when-downgrade" policy sends a full URL along with requests
    from a TLS-protected environment settings object to a potentially trustworthy URL,
    and requests from clients which are not TLS-protected to any origin.

    Requests from TLS-protected clients to non-potentially trustworthy URLs,
    on the other hand, will contain no referrer information.
    A Referer HTTP header will not be sent.

    This is a user agent's default behavior, if no policy is otherwise specified.
    """
    name: str = POLICY_NO_REFERRER_WHEN_DOWNGRADE

    def referrer(self, response_url, request_url):
        if not self.tls_protected(response_url) or self.tls_protected(request_url):
            return self.stripped_referrer(response_url)


class SameOriginPolicy(ReferrerPolicy):
    """
    https://www.w3.org/TR/referrer-policy/#referrer-policy-same-origin

    The "same-origin" policy specifies that a full URL, stripped for use as a referrer,
    is sent as referrer information when making same-origin requests from a particular request client.

    Cross-origin requests, on the other hand, will contain no referrer information.
    A Referer HTTP header will not be sent.
    """
    name: str = POLICY_SAME_ORIGIN

    def referrer(self, response_url, request_url):
        if self.origin(response_url) == self.origin(request_url):
            return self.stripped_referrer(response_url)


class OriginPolicy(ReferrerPolicy):
    """
    https://www.w3.org/TR/referrer-policy/#referrer-policy-origin

    The "origin" policy specifies that only the ASCII serialization
    of the origin of the request client is sent as referrer information
    when making both same-origin requests and cross-origin requests
    from a particular request client.
    """
    name: str = POLICY_ORIGIN

    def referrer(self, response_url, request_url):
        return self.origin_referrer(response_url)


class StrictOriginPolicy(ReferrerPolicy):
    """
    https://www.w3.org/TR/referrer-policy/#referrer-policy-strict-origin

    The "strict-origin" policy sends the ASCII serialization
    of the origin of the request client when making requests:
    - from a TLS-protected environment settings object to a potentially trustworthy URL, and
    - from non-TLS-protected environment settings objects to any origin.

    Requests from TLS-protected request clients to non- potentially trustworthy URLs,
    on the other hand, will contain no referrer information.
    A Referer HTTP header will not be sent.
    """
    name: str = POLICY_STRICT_ORIGIN

    def referrer(self, response_url, request_url):
        if (
            self.tls_protected(response_url) and self.potentially_trustworthy(request_url)
            or not self.tls_protected(response_url)
        ):
            return self.origin_referrer(response_url)


class OriginWhenCrossOriginPolicy(ReferrerPolicy):
    """
    https://www.w3.org/TR/referrer-policy/#referrer-policy-origin-when-cross-origin

    The "origin-when-cross-origin" policy specifies that a full URL,
    stripped for use as a referrer, is sent as referrer information
    when making same-origin requests from a particular request client,
    and only the ASCII serialization of the origin of the request client
    is sent as referrer information when making cross-origin requests
    from a particular request client.
    """
    name: str = POLICY_ORIGIN_WHEN_CROSS_ORIGIN

    def referrer(self, response_url, request_url):
        origin = self.origin(response_url)
        if origin == self.origin(request_url):
            return self.stripped_referrer(response_url)
        else:
            return origin


class StrictOriginWhenCrossOriginPolicy(ReferrerPolicy):
    """
    https://www.w3.org/TR/referrer-policy/#referrer-policy-strict-origin-when-cross-origin

    The "strict-origin-when-cross-origin" policy specifies that a full URL,
    stripped for use as a referrer, is sent as referrer information
    when making same-origin requests from a particular request client,
    and only the ASCII serialization of the origin of the request client
    when making cross-origin requests:

    - from a TLS-protected environment settings object to a potentially trustworthy URL, and
    - from non-TLS-protected environment settings objects to any origin.

    Requests from TLS-protected clients to non- potentially trustworthy URLs,
    on the other hand, will contain no referrer information.
    A Referer HTTP header will not be sent.
    """
    name: str = POLICY_STRICT_ORIGIN_WHEN_CROSS_ORIGIN

    def referrer(self, response_url, request_url):
        origin = self.origin(response_url)
        if origin == self.origin(request_url):
            return self.stripped_referrer(response_url)
        elif (
            self.tls_protected(response_url) and self.potentially_trustworthy(request_url)
            or not self.tls_protected(response_url)
        ):
            return self.origin_referrer(response_url)


class UnsafeUrlPolicy(ReferrerPolicy):
    """
    https://www.w3.org/TR/referrer-policy/#referrer-policy-unsafe-url

    The "unsafe-url" policy specifies that a full URL, stripped for use as a referrer,
    is sent along with both cross-origin requests
    and same-origin requests made from a particular request client.

    Note: The policy's name doesn't lie; it is unsafe.
    This policy will leak origins and paths from TLS-protected resources
    to insecure origins.
    Carefully consider the impact of setting such a policy for potentially sensitive documents.
    """
    name: str = POLICY_UNSAFE_URL

    def referrer(self, response_url, request_url):
        return self.stripped_referrer(response_url)


class DefaultReferrerPolicy(NoReferrerWhenDowngradePolicy):
    """
    A variant of "no-referrer-when-downgrade",
    with the addition that "Referer" is not sent if the parent request was
    using ``file://`` or ``s3://`` scheme.
    """
    NOREFERRER_SCHEMES: Tuple[str, ...] = LOCAL_SCHEMES + ('file', 's3')
    name: str = POLICY_AIOSCRAPY_DEFAULT


_policy_classes = {p.name: p for p in (
    NoReferrerPolicy,
    NoReferrerWhenDowngradePolicy,
    SameOriginPolicy,
    OriginPolicy,
    StrictOriginPolicy,
    OriginWhenCrossOriginPolicy,
    StrictOriginWhenCrossOriginPolicy,
    UnsafeUrlPolicy,
    DefaultReferrerPolicy,
)}

# Reference: https://www.w3.org/TR/referrer-policy/#referrer-policy-empty-string
_policy_classes[''] = NoReferrerWhenDowngradePolicy


def _load_policy_class(policy, warning_only=False):
    """
    Load a referrer policy class by name or path.
    通过名称或路径加载引用策略类。

    This function attempts to load a referrer policy class either by importing it
    from a path or by looking it up in the standard policy classes dictionary.
    此函数尝试通过从路径导入或在标准策略类字典中查找来加载引用策略类。

    Args:
        policy: A string representing either a path to a policy class or a standard
               policy name from the W3C Referrer Policy specification.
               表示策略类路径或W3C引用策略规范中的标准策略名称的字符串。
        warning_only: If True, warnings will be issued instead of raising exceptions
                     when a policy cannot be loaded.
                     如果为True，当无法加载策略时将发出警告而不是引发异常。

    Returns:
        A referrer policy class, or None if the policy could not be loaded and
        warning_only is True.
        引用策略类，如果无法加载策略且warning_only为True，则为None。

    Raises:
        RuntimeError: If the policy could not be loaded and warning_only is False.
                     如果无法加载策略且warning_only为False，则引发RuntimeError。
    """
    try:
        # Try to load the policy as a Python object (e.g., 'mymodule.MyPolicy')
        # 尝试将策略作为Python对象加载（例如，'mymodule.MyPolicy'）
        return load_object(policy)
    except ValueError:
        try:
            # Try to load the policy as a standard policy name
            # 尝试将策略作为标准策略名称加载
            return _policy_classes[policy.lower()]
        except KeyError:
            # Policy could not be loaded
            # 无法加载策略
            msg = f"Could not load referrer policy {policy!r}"
            if not warning_only:
                raise RuntimeError(msg)
            else:
                warnings.warn(msg, RuntimeWarning)
                return None


class RefererMiddleware:
    """
    Middleware for populating the 'Referer' HTTP header in requests.
    用于填充请求中的'Referer' HTTP头的中间件。

    This middleware sets the 'Referer' HTTP header in requests based on the response
    that generated them, following the W3C Referrer Policy specification. It allows
    control over what information is included in the Referer header for privacy and
    security reasons.
    此中间件根据生成请求的响应设置请求中的'Referer' HTTP头，遵循W3C引用策略规范。
    它允许出于隐私和安全原因控制Referer头中包含的信息。
    """

    def __init__(self, settings=None):
        """
        Initialize the RefererMiddleware.
        初始化RefererMiddleware。

        Args:
            settings: The AioScrapy settings object.
                     AioScrapy设置对象。
                     If None, the default policy will be used.
                     如果为None，将使用默认策略。
        """
        # Set the default policy
        # 设置默认策略
        self.default_policy = DefaultReferrerPolicy

        # If settings are provided, load the policy from settings
        # 如果提供了设置，从设置加载策略
        if settings is not None:
            self.default_policy = _load_policy_class(
                settings.get('REFERRER_POLICY'))

    @classmethod
    def from_crawler(cls, crawler):
        """
        Create a RefererMiddleware instance from a crawler.
        从爬虫创建RefererMiddleware实例。

        This is the factory method used by AioScrapy to create the middleware.
        这是AioScrapy用于创建中间件的工厂方法。

        Args:
            crawler: The crawler that will use this middleware.
                    将使用此中间件的爬虫。

        Returns:
            RefererMiddleware: A new RefererMiddleware instance.
                              一个新的RefererMiddleware实例。

        Raises:
            NotConfigured: If REFERER_ENABLED is False in the crawler settings.
                          如果爬虫设置中的REFERER_ENABLED为False。
        """
        # Check if the middleware is enabled
        # 检查中间件是否已启用
        if not crawler.settings.getbool('REFERER_ENABLED'):
            raise NotConfigured

        # Create a new instance with the crawler's settings
        # 使用爬虫的设置创建一个新实例
        mw = cls(crawler.settings)

        # Connect the request_scheduled method to the request_scheduled signal
        # to handle redirections
        # 将request_scheduled方法连接到request_scheduled信号以处理重定向
        # Note: this hook is a bit of a hack to intercept redirections
        # 注意：这个钩子有点像一个黑客，用于拦截重定向
        crawler.signals.connect(mw.request_scheduled, signal=signals.request_scheduled)

        # Return the new instance
        # 返回新实例
        return mw

    def policy(self, resp_or_url, request):
        """
        Determine the Referrer-Policy to use for a request.
        确定用于请求的引用策略。

        This method determines which referrer policy to use based on the following
        precedence rules:
        此方法根据以下优先级规则确定要使用的引用策略：

        - If a valid policy is set in Request meta, it is used.
          如果在Request meta中设置了有效的策略，则使用它。
        - If the policy is set in meta but is wrong (e.g. a typo error),
          the policy from settings is used.
          如果在meta中设置了策略但是错误的（例如，拼写错误），
          则使用设置中的策略。
        - If the policy is not set in Request meta,
          but there is a Referrer-Policy header in the parent response,
          it is used if valid.
          如果在Request meta中未设置策略，
          但在父响应中有Referrer-Policy头，
          如果有效，则使用它。
        - Otherwise, the policy from settings is used.
          否则，使用设置中的策略。

        Args:
            resp_or_url: The parent Response object or URL string.
                        父Response对象或URL字符串。
            request: The Request object being processed.
                    正在处理的Request对象。

        Returns:
            ReferrerPolicy: An instance of the appropriate referrer policy class.
                           适当的引用策略类的实例。
        """
        # Try to get the policy name from the request meta
        # 尝试从请求元数据获取策略名称
        policy_name = request.meta.get('referrer_policy')

        # If no policy in meta, try to get it from the response headers
        # 如果元数据中没有策略，尝试从响应头获取
        if policy_name is None:
            if isinstance(resp_or_url, Response):
                policy_header = resp_or_url.headers.get('Referrer-Policy')
                if policy_header is not None:
                    policy_name = to_unicode(policy_header.decode('latin1') if isinstance(policy_header, bytes) else policy_header)

        # If no policy was found, use the default
        # 如果未找到策略，使用默认值
        if policy_name is None:
            return self.default_policy()

        # Try to load the policy class
        # 尝试加载策略类
        cls = _load_policy_class(policy_name, warning_only=True)

        # Return an instance of the policy class, or the default if loading failed
        # 返回策略类的实例，如果加载失败，则返回默认值
        return cls() if cls else self.default_policy()

    async def process_spider_output(self, response, result, spider):
        """
        Process the spider output to set the 'Referer' header in requests.
        处理爬虫输出以在请求中设置'Referer'头。

        This method processes each request yielded by the spider and sets the
        'Referer' header based on the appropriate referrer policy.
        此方法处理爬虫产生的每个请求，并根据适当的引用策略设置'Referer'头。

        Args:
            response: The response being processed.
                     正在处理的响应。
            result: The result returned by the spider.
                   爬虫返回的结果。
            spider: The spider that generated the result.
                   生成结果的爬虫。

        Returns:
            An async generator yielding processed requests and other items.
            一个产生处理后的请求和其他项目的异步生成器。
        """
        def _set_referer(r):
            """
            Set the 'Referer' header for a request if it's a Request object.
            如果是Request对象，则为请求设置'Referer'头。

            Args:
                r: The item to process.
                   要处理的项目。

            Returns:
                The processed item.
                处理后的项目。
            """
            # Only process Request objects
            # 只处理Request对象
            if isinstance(r, Request):
                # Get the referrer value based on the policy
                # 根据策略获取引用值
                referrer = self.policy(response, r).referrer(response.url, r.url)

                # If a referrer value was returned, set it in the request headers
                # 如果返回了引用值，则在请求头中设置它
                if referrer is not None:
                    r.headers.setdefault('Referer', referrer)

            # Return the item, possibly modified
            # 返回可能已修改的项目
            return r

        # Process each item in the result
        # 处理结果中的每个项目
        return (_set_referer(r) async for r in result or ())

    def request_scheduled(self, request, spider):
        """
        Handle scheduled requests to patch the 'Referer' header if necessary.
        处理计划的请求，以在必要时修补'Referer'头。

        This method is called when a request is scheduled. It handles redirected
        requests by updating the 'Referer' header according to the appropriate
        referrer policy.
        当请求被计划时调用此方法。它通过根据适当的引用策略更新'Referer'头来处理
        重定向的请求。

        Args:
            request: The request being scheduled.
                    正在计划的请求。
            spider: The spider that generated the request.
                   生成请求的爬虫。
        """
        # Check if this is a redirected request
        # 检查这是否是重定向的请求
        redirected_urls = request.meta.get('redirect_urls', [])
        if redirected_urls:
            # Get the current 'Referer' header value
            # 获取当前的'Referer'头值
            request_referrer = request.headers.get('Referer')

            # We don't patch the referrer value if there is none
            # 如果没有引用值，我们不会修补它
            if request_referrer is not None:
                # The request's referrer header value acts as a surrogate
                # for the parent response URL
                # 请求的引用头值作为父响应URL的替代品
                #
                # Note: if the 3xx response contained a Referrer-Policy header,
                #       the information is not available using this hook
                # 注意：如果3xx响应包含Referrer-Policy头，
                #       使用此钩子无法获取信息
                parent_url = safe_url_string(request_referrer)

                # Get the referrer value based on the policy
                # 根据策略获取引用值
                policy_referrer = self.policy(parent_url, request).referrer(
                    parent_url, request.url)

                # If the policy referrer is different from the current referrer,
                # update the header
                # 如果策略引用与当前引用不同，则更新头
                if policy_referrer != request_referrer:
                    if policy_referrer is None:
                        # Remove the 'Referer' header if the policy says not to send one
                        # 如果策略说不发送引用，则删除'Referer'头
                        request.headers.pop('Referer')
                    else:
                        # Update the 'Referer' header with the policy value
                        # 使用策略值更新'Referer'头
                        request.headers['Referer'] = policy_referrer

