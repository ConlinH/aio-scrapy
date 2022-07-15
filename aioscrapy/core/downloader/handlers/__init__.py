"""Download handlers for different schemes"""

import logging
from abc import abstractmethod
from typing import Optional

from aioscrapy import signals, Request, Spider
from aioscrapy.exceptions import NotConfigured, NotSupported
from aioscrapy.http import HtmlResponse
from aioscrapy.utils.httpobj import urlparse_cached
from aioscrapy.utils.misc import load_instance
from aioscrapy.utils.python import without_none_values

logger = logging.getLogger(__name__)


class BaseDownloadHandler:
    @abstractmethod
    async def download_request(self, requests: Request, spider: Spider):
        raise NotImplementedError()

    @abstractmethod
    async def close(self):
        pass


class DownloadHandlerManager:

    def __init__(self, crawler):
        self._crawler = crawler

        # stores acceptable schemes on instancing
        self._schemes: dict = without_none_values(crawler.settings.getwithbase('DOWNLOAD_HANDLERS')) or {}
        self._handlers: dict = {}  # stores instanced handlers for schemes
        self._notconfigured: dict = {}  # remembers failed handlers
        crawler.signals.connect(self._close, signals.engine_stopped)

    @classmethod
    def for_crawler(cls, crawler) -> "DownloadHandlerManager":
        return cls(crawler)

    async def _get_handler(self, scheme: str) -> Optional[BaseDownloadHandler]:
        """Lazy-load the downloadhandler for a scheme
        only on the first request for that scheme.
        """
        if scheme in self._handlers:
            return self._handlers[scheme]
        if scheme in self._notconfigured:
            return None
        if scheme not in self._schemes:
            self._notconfigured[scheme] = 'no handler available for that scheme'
            return None

        return await self._load_handler(scheme)

    async def _load_handler(self, scheme: str) -> Optional[BaseDownloadHandler]:
        path: str = self._schemes[scheme]
        try:
            dh: BaseDownloadHandler = await load_instance(
                path,
                settings=self._crawler.settings,
            )
        except NotConfigured as ex:
            self._notconfigured[scheme] = str(ex)
            return None
        except Exception as ex:
            logger.error('Loading "%(clspath)s" for scheme "%(scheme)s"',
                         {"clspath": path, "scheme": scheme},
                         exc_info=True, extra={'crawler': self._crawler})
            self._notconfigured[scheme] = str(ex)
            return None
        else:
            self._handlers[scheme] = dh
            return dh

    async def download_request(self, request: Request, spider: Spider) -> HtmlResponse:
        scheme = urlparse_cached(request).scheme
        handler: BaseDownloadHandler = await self._get_handler(scheme)
        if not handler:
            raise NotSupported("Unsupported URL scheme '%s': %s" %
                               (scheme, self._notconfigured[scheme]))
        return await handler.download_request(request, spider)

    async def _close(self, *_a, **_kw) -> None:
        for dh in self._handlers.values():
            await dh.close()
