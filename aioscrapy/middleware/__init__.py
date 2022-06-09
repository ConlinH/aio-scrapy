
from aioscrapy.middleware.downloader import DownloaderMiddlewareManager
from aioscrapy.middleware.itempipeline import ItemPipelineManager
from aioscrapy.middleware.spider import SpiderMiddlewareManager
from aioscrapy.middleware.extension import ExtensionManager

__all__ = (
    "DownloaderMiddlewareManager", "ItemPipelineManager",
    "SpiderMiddlewareManager", "ExtensionManager"
)
