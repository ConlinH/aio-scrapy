import logging
import ssl

from aioscrapy.http import HtmlResponse

logger = logging.getLogger(__name__)

try:
    import httpx
except ImportError:
    logger.warning("Please run 'pip install httpx' when you want replace 'aiohttp' with 'httpx'")


class HttpxDownloadHandler(object):

    def __init__(self, settings, crawler):
        self.settings = settings
        self.crawler = crawler
        self.httpx_client_session_args = settings.get('HTTPX_CLIENT_SESSION_ARGS', {})
        self.verify_ssl = self.settings.get("VERIFY_SSL")
        self.ssl_protocol = self.settings.get("SSL_PROTOCOL")

    @classmethod
    def from_settings(cls, settings, crawler):
        return cls(settings, crawler)

    @classmethod
    def from_crawler(cls, crawler):
        return cls.from_settings(crawler.settings, crawler)

    async def download_request(self, request, spider):
        kwargs = {
            'timeout': self.settings.get('DOWNLOAD_TIMEOUT'),
            'cookies': dict(request.cookies),
            'data': request.body or None
        }
        headers = request.headers or self.settings.get('DEFAULT_REQUEST_HEADERS')
        kwargs['headers'] = headers

        session_args = self.httpx_client_session_args.copy()
        session_args.update({
            'follow_redirects': self.settings.getbool('REDIRECT_ENABLED', True) if request.meta.get(
                'dont_redirect') is None else request.meta.get('dont_redirect'),
            'max_redirects': self.settings.getint('REDIRECT_MAX_TIMES', 10),
        })
        ssl_ciphers = request.meta.get('TLS_CIPHERS')
        ssl_protocol = request.meta.get('ssl_protocol', self.ssl_protocol)
        if ssl_ciphers or ssl_protocol:
            if ssl_protocol:
                context = ssl.SSLContext(protocol=ssl_protocol)
            else:
                context = ssl.create_default_context()

            ssl_ciphers and context.set_ciphers(ssl_ciphers)
            session_args['verify'] = context

        proxy = request.meta.get("proxy")
        if proxy:
            session_args["proxies"] = proxy
            logger.debug(f"使用代理{proxy}抓取: {request.url}")

        async with httpx.AsyncClient(**session_args) as session:
            response = await session.request(request.method, request.url, **kwargs)
            content = response.read()

        return HtmlResponse(
            str(response.url),
            status=response.status_code,
            headers=response.headers,
            body=content,
            cookies=dict(response.cookies),
            encoding=response.encoding
        )
