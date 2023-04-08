import asyncio
import logging
from urllib.parse import urlparse

import pyhttpx

from aioscrapy import Request
from aioscrapy.core.downloader.handlers import BaseDownloadHandler
from aioscrapy.http import HtmlResponse
from aioscrapy.settings import Settings

logger = logging.getLogger(__name__)


class PyhttpxHandler(BaseDownloadHandler):

    def __init__(self, settings):
        self.settings: Settings = settings
        self.pyhttpx_client_args: dict = self.settings.get('PYHTTPX_CLIENT_ARGS', {})
        self.verify_ssl: bool = self.settings.get("VERIFY_SSL")
        self.loop = asyncio.get_running_loop()

    @classmethod
    def from_settings(cls, settings: Settings):
        return cls(settings)

    async def download_request(self, request: Request, _) -> HtmlResponse:
        kwargs = {
            'timeout': self.settings.get('DOWNLOAD_TIMEOUT'),
            'cookies': dict(request.cookies),
            'verify': self.verify_ssl,
            'allow_redirects': self.settings.getbool('REDIRECT_ENABLED', True) if request.meta.get(
                'dont_redirect') is None else request.meta.get('dont_redirect')
        }
        post_data = request.body or None
        if isinstance(post_data, dict):
            kwargs['json'] = post_data
        else:
            kwargs['data'] = post_data

        headers = request.headers or self.settings.get('DEFAULT_REQUEST_HEADERS')
        kwargs['headers'] = headers

        proxy = request.meta.get("proxy")
        if proxy:
            parsed_url = urlparse(proxy)
            kwargs["proxies"] = {'https': parsed_url.netloc.split('@')[-1]}
            if parsed_url.password or parsed_url.username:
                kwargs['proxy_auth'] = (parsed_url.username, parsed_url.password)
            logger.debug(f"use proxy {proxy}: {request.url}")

        session_args = self.pyhttpx_client_args.copy()
        session = pyhttpx.HttpSession(**session_args)
        response = await asyncio.to_thread(session.request, request.method, request.url, **kwargs)
        return HtmlResponse(
            '',
            status=response.status_code,
            headers=response.headers,
            body=response.content,
            cookies=dict(response.cookies),
            encoding=response.encoding
        )

    async def close(self):
        pass
