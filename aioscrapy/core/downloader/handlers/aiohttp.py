import asyncio
import logging
import ssl
import re

import aiohttp

from aioscrapy.http import HtmlResponse

logger = logging.getLogger(__name__)


class AioHttpDownloadHandler:
    session = None

    def __init__(self, settings):
        self.settings = settings
        self.aiohttp_client_session_args = settings.get('AIOHTTP_CLIENT_SESSION_ARGS', {})
        self.verify_ssl = self.settings.get("VERIFY_SSL")
        self.ssl_protocol = self.settings.get("SSL_PROTOCOL")

    @classmethod
    def from_settings(cls, settings):
        return cls(settings)

    def get_session(self, *args, **kwargs):
        if self.session is None:
            self.session = aiohttp.ClientSession(*args, **kwargs)
        return self.session

    async def download_request(self, request, spider):
        kwargs = {
            'verify_ssl': request.meta.get('verify_ssl', self.verify_ssl),
            'timeout': request.meta.get('download_timeout', 180),
            'cookies': dict(request.cookies),
            'data': request.body or None,
            'allow_redirects': self.settings.getbool('REDIRECT_ENABLED', True) if request.meta.get('dont_redirect') is None else request.meta.get('dont_redirect'),
            'max_redirects': self.settings.getint('REDIRECT_MAX_TIMES', 10),
        }

        headers = request.headers or self.settings.get('DEFAULT_REQUEST_HEADERS')
        kwargs['headers'] = headers

        ssl_ciphers = request.meta.get('TLS_CIPHERS')
        ssl_protocol = request.meta.get('ssl_protocol', self.ssl_protocol)
        if ssl_ciphers or ssl_protocol:
            if ssl_protocol:
                context = ssl.SSLContext(protocol=ssl_protocol)
            else:
                context = ssl.create_default_context()

            ssl_ciphers and context.set_ciphers(ssl_ciphers)
            kwargs['ssl'] = context

        proxy = request.meta.get("proxy")
        if proxy:
            kwargs["proxy"] = proxy
            logger.debug(f"使用代理{proxy}抓取: {request.url}")

            async with aiohttp.ClientSession(**self.aiohttp_client_session_args) as session:
                async with session.request(request.method, request.url, **kwargs) as response:
                    content = await response.read()

        # Don't close session on the proxy is not in use
        else:
            session = self.get_session(**self.aiohttp_client_session_args)
            async with session.request(request.method, request.url, **kwargs) as response:
                content = await response.read()

        r_cookies = response.cookies.output() or None
        if r_cookies:
            r_cookies = {
                cookie[0]: cookie[1] for cookie in re.findall(r'Set-Cookie: (.*?)=(.*?); Domain', r_cookies, re.S)
            }

        return HtmlResponse(
            str(response.url),
            status=response.status,
            headers=response.headers,
            body=content,
            cookies=r_cookies,
            encoding=response.charset
        )

    async def close(self):
        if self.session is not None:
            await self.session.close()

        # Wait 250 ms for the underlying SSL connections to close
        # https://docs.aiohttp.org/en/latest/client_advanced.html#graceful-shutdown
        await asyncio.sleep(0.250)
