"""
JA3 Fingerprint Randomization Middleware
JA3指纹随机化中间件

This module provides a middleware for randomizing SSL/TLS cipher suites to help
avoid fingerprinting and detection when making HTTPS requests. JA3 is a method
for creating SSL/TLS client fingerprints that can be used to identify specific
clients regardless of the presented hostname or client IP address.
此模块提供了一个中间件，用于随机化SSL/TLS密码套件，以帮助在发出HTTPS请求时
避免指纹识别和检测。JA3是一种创建SSL/TLS客户端指纹的方法，可用于识别特定
客户端，而不考虑所呈现的主机名或客户端IP地址。

By randomizing the order of cipher suites, this middleware helps to generate
different JA3 fingerprints for each request, making it harder for servers to
track or block the crawler based on its TLS fingerprint.
通过随机化密码套件的顺序，此中间件有助于为每个请求生成不同的JA3指纹，
使服务器更难基于其TLS指纹跟踪或阻止爬虫。
"""
import random


# Default cipher suite string used when no custom ciphers are specified
# 未指定自定义密码套件时使用的默认密码套件字符串
ORIGIN_CIPHERS = ('ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+HIGH:'
                  'DH+HIGH:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+HIGH:RSA+3DES:!aNULL:!eNULL:!MD5')


class TLSCiphersMiddleware:
    """
    SSL/TLS Fingerprint Randomization Middleware.
    SSL/TLS指纹随机化中间件。

    This middleware modifies the SSL/TLS cipher suites used in HTTPS requests
    to help avoid fingerprinting and detection. It can use custom cipher suites
    or randomize the order of the default cipher suites.
    此中间件修改HTTPS请求中使用的SSL/TLS密码套件，以帮助避免指纹识别和检测。
    它可以使用自定义密码套件或随机化默认密码套件的顺序。
    """

    def __init__(self, ciphers, is_random):
        """
        Initialize the TLS Ciphers Middleware.
        初始化TLS密码套件中间件。

        Args:
            ciphers: The cipher suites to use, or 'DEFAULT' to use the default ciphers.
                    要使用的密码套件，或'DEFAULT'以使用默认密码套件。
            is_random: Whether to randomize the order of cipher suites.
                      是否随机化密码套件的顺序。
        """
        # If ciphers is 'DEFAULT', set self.ciphers to None to use ORIGIN_CIPHERS later
        # 如果ciphers是'DEFAULT'，将self.ciphers设置为None以便稍后使用ORIGIN_CIPHERS
        if ciphers == 'DEFAULT':
            self.ciphers = None
        else:
            self.ciphers = ciphers

        self.is_random = is_random

    @classmethod
    def from_crawler(cls, crawler):
        """
        Create a TLSCiphersMiddleware instance from a crawler.
        从爬虫创建TLSCiphersMiddleware实例。

        This is the factory method used by AioScrapy to create middleware instances.
        这是AioScrapy用于创建中间件实例的工厂方法。

        Args:
            crawler: The crawler that will use this middleware.
                    将使用此中间件的爬虫。

        Returns:
            TLSCiphersMiddleware: A new TLSCiphersMiddleware instance.
                                 一个新的TLSCiphersMiddleware实例。
        """
        return cls(
            # Get custom cipher suites from settings, or use 'DEFAULT'
            # 从设置获取自定义密码套件，或使用'DEFAULT'
            ciphers=crawler.settings.get('DOWNLOADER_CLIENT_TLS_CIPHERS', 'DEFAULT'),
            # Get whether to randomize cipher suites from settings
            # 从设置获取是否随机化密码套件
            is_random=crawler.settings.get('RANDOM_TLS_CIPHERS', False)
        )

    def process_request(self, request, spider):
        """
        Process a request before it is sent to the downloader.
        在请求发送到下载器之前处理它。

        This method sets the TLS cipher suites for the request, optionally
        randomizing their order to generate different JA3 fingerprints.
        此方法为请求设置TLS密码套件，可选择随机化它们的顺序以生成不同的JA3指纹。

        Args:
            request: The request being processed.
                    正在处理的请求。
            spider: The spider that generated the request.
                   生成请求的爬虫。

        Returns:
            None: This method returns None to continue processing the request.
                 此方法返回None以继续处理请求。
        """
        # Skip if neither custom ciphers nor randomization is enabled
        # 如果既没有启用自定义密码套件也没有启用随机化，则跳过
        if not (self.ciphers or self.is_random):
            return

        # Use custom ciphers if specified, otherwise use default
        # 如果指定了自定义密码套件则使用它，否则使用默认值
        ciphers = self.ciphers or ORIGIN_CIPHERS

        # Randomize cipher suite order if enabled
        # 如果启用了随机化，则随机化密码套件顺序
        if self.is_random:
            # Split the cipher string into individual ciphers
            # 将密码字符串拆分为单个密码
            ciphers = ciphers.split(":")
            # Shuffle the ciphers randomly
            # 随机打乱密码
            random.shuffle(ciphers)
            # Join the ciphers back into a string
            # 将密码重新连接成字符串
            ciphers = ":".join(ciphers)

        # Set the cipher suites in the request metadata
        # 在请求元数据中设置密码套件
        request.meta['TLS_CIPHERS'] = ciphers
