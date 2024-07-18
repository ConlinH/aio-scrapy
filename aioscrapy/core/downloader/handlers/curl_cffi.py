from curl_cffi.curl import CurlError
from curl_cffi.requests import AsyncSession

from aioscrapy import Request
from aioscrapy.core.downloader.handlers import BaseDownloadHandler
from aioscrapy.exceptions import DownloadError
from aioscrapy.http import HtmlResponse
from aioscrapy.settings import Settings
from aioscrapy.utils.log import logger


class CurlCffiDownloadHandler(BaseDownloadHandler):

    def __init__(self, settings):
        self.settings: Settings = settings
        self.httpx_client_session_args: dict = self.settings.get('CURL_CFFI_CLIENT_SESSION_ARGS', {})
        self.verify_ssl: bool = self.settings.get("VERIFY_SSL", True)

    @classmethod
    def from_settings(cls, settings: Settings):
        return cls(settings)

    async def download_request(self, request: Request, _) -> HtmlResponse:
        try:
            return await self._download_request(request)
        except CurlError as e:
            raise DownloadError from e

    async def _download_request(self, request: Request) -> HtmlResponse:
        kwargs = {
            'timeout': self.settings.get('DOWNLOAD_TIMEOUT'),
            'cookies': dict(request.cookies),
            'verify': request.meta.get('verify_ssl', self.verify_ssl),
            'allow_redirects': self.settings.getbool('REDIRECT_ENABLED', True) if request.meta.get(
                'dont_redirect') is None else request.meta.get('dont_redirect'),
            'impersonate': request.meta.get('impersonate'),
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

        session_args = self.httpx_client_session_args.copy()

        async with AsyncSession(**session_args) as session:
            response = await session.request(request.method, request.url, **kwargs)

        return HtmlResponse(
            str(response.url),
            status=response.status_code,
            headers=response.headers,
            body=response.content,
            cookies={j.name: j.value or '' for j in response.cookies.jar},
            encoding=response.encoding
        )

    async def close(self):
        pass
