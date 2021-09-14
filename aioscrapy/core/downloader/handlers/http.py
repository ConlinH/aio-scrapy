import asyncio
import logging
import ssl
import sys

from scrapy.http import Headers
from aioscrapy.https import TextResponse
import aiohttp

logger = logging.getLogger(__name__)


class AioHttpDownloadHandler:
    session = None

    def __init__(self, settings, crawler=None):
        self._crawler = crawler
        self.settings = settings

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings, crawler)

    def get_session(self, *arg, **kw):
        if self.session is None:
            if sys.platform.startswith('win'):
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            self.session = aiohttp.ClientSession(*arg, **kw)
        return self.session

    async def download_request(self, request, spider):
        kwargs = {}

        if request.headers:
            headers = request.headers
        elif self.settings.get('headers', False):
            headers = self.settings.get('headers')
        else:
            headers = {}
        if isinstance(headers, Headers):
            headers = headers.to_unicode_dict()
        kwargs['headers'] = headers

        timeout = self.settings.get("DOWNLOAD_TIMEOUT", None)
        if timeout:
            kwargs['timeout'] = timeout

        proxy = request.meta.get("proxy")
        if proxy:
            kwargs["proxy"] = proxy
            logger.info(f"使用代理{proxy}抓取: {request.url}")

        cookies = request.cookies
        if cookies:
            kwargs['cookies'] = dict(cookies)

        ssl_ciphers = request.meta.get('TLS_CIPHERS')
        if ssl_ciphers:
            context = ssl.create_default_context()
            context.set_ciphers(ssl_ciphers)
            kwargs['ssl'] = context

        session = self.get_session()
        method = getattr(session, request.method.lower())
        if request.body:
            kwargs['data'] = request.body
        response = await method(request.url, **kwargs)
        content = await response.read()
        return TextResponse(str(response.url),
                            status=response.status,
                            headers=response.headers,
                            body=content,
                            cookies=response.cookies)

    async def close(self):
        if self.session is not None:
            await self.session.close()
