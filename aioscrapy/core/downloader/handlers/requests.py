import asyncio

import requests
from requests.exceptions import RequestException as RequestsError

from aioscrapy import Request
from aioscrapy.core.downloader.handlers import BaseDownloadHandler
from aioscrapy.exceptions import DownloadError
from aioscrapy.http import HtmlResponse
from aioscrapy.settings import Settings
from aioscrapy.utils.log import logger


class RequestsDownloadHandler(BaseDownloadHandler):

    def __init__(self, settings):
        self.settings: Settings = settings
        self.verify_ssl: bool = self.settings.get("VERIFY_SSL", True)

    @classmethod
    def from_settings(cls, settings: Settings):
        return cls(settings)

    async def download_request(self, request: Request, _) -> HtmlResponse:
        try:
            return await self._download_request(request)
        except RequestsError as e:
            raise DownloadError(real_error=e) from e

    async def _download_request(self, request: Request) -> HtmlResponse:
        kwargs = {
            'timeout': self.settings.get('DOWNLOAD_TIMEOUT'),
            'cookies': dict(request.cookies),
            'verify': request.meta.get('verify_ssl', self.verify_ssl),
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
            kwargs["proxies"] = {'http': proxy, 'https': proxy}
            logger.debug(f"use proxy {proxy}: {request.url}")

        response = await asyncio.to_thread(requests.request, request.method, request.url, **kwargs)
        return HtmlResponse(
            response.url,
            status=response.status_code,
            headers=response.headers,
            body=response.content,
            cookies={k: v or '' for k, v in response.cookies.items()},
            encoding=response.encoding
        )

    async def close(self):
        pass
