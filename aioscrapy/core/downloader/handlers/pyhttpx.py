import asyncio

import pyhttpx

from aioscrapy import Request
from aioscrapy.core.downloader.handlers import BaseDownloadHandler
from aioscrapy.http import HtmlResponse
from aioscrapy.settings import Settings
from aioscrapy.utils.log import logger


class PyhttpxDownloadHandler(BaseDownloadHandler):

    def __init__(self, settings):
        self.settings: Settings = settings
        self.pyhttpx_client_args: dict = self.settings.get('PYHTTPX_CLIENT_ARGS', {})
        self.verify_ssl = self.settings.get("VERIFY_SSL", True)
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
            kwargs["proxies"] = {'https': proxy}
            logger.debug(f"use proxy {proxy}: {request.url}")

        session_args = self.pyhttpx_client_args.copy()
        session_args.setdefault('http2', True)
        with pyhttpx.HttpSession(**session_args) as session:
            response = await asyncio.to_thread(session.request, request.method, request.url, **kwargs)
            return HtmlResponse(
                request.url,
                status=response.status_code,
                headers=response.headers,
                body=response.content,
                cookies=dict(response.cookies),
                encoding=response.encoding
            )

    async def close(self):
        pass
