"""
Disk-based Request Fingerprint Duplicate Filter for AioScrapy
AioScrapy的基于磁盘的请求指纹重复过滤器

This module provides a duplicate filter that stores request fingerprints on disk,
allowing for persistence between crawler runs. It implements the DupeFilterBase
interface and is used to avoid crawling the same URL multiple times.
此模块提供了一个将请求指纹存储在磁盘上的重复过滤器，允许在爬虫运行之间保持持久性。
它实现了DupeFilterBase接口，用于避免多次爬取相同的URL。
"""

import os
from typing import Optional, Set

from aioscrapy import Request
from aioscrapy.dupefilters import DupeFilterBase


class DiskRFPDupeFilter(DupeFilterBase):
    """
    Request Fingerprint duplicates filter built with Disk storage.
    基于磁盘存储构建的请求指纹重复过滤器。

    This filter stores request fingerprints in memory and on disk, allowing for
    persistence between crawler runs. It implements the DupeFilterBase interface
    and is used to avoid crawling the same URL multiple times.
    此过滤器将请求指纹存储在内存和磁盘上，允许在爬虫运行之间保持持久性。
    它实现了DupeFilterBase接口，用于避免多次爬取相同的URL。
    """

    def __init__(self, path: Optional[str] = None, debug: bool = False, info: bool = False):
        """
        Initialize the disk-based request fingerprint filter.
        初始化基于磁盘的请求指纹过滤器。

        Args:
            path: Directory path where to store the requests.seen file.
                 存储requests.seen文件的目录路径。
                 If None, no persistence will be used.
                 如果为None，则不会使用持久性存储。
            debug: Whether to log filtered requests.
                  是否记录被过滤的请求。
            info: Whether to log duplicate requests.
                 是否记录重复的请求。
        """
        # File handle for the requests.seen file
        # requests.seen文件的文件句柄
        self.file: Optional[object] = None

        # Whether to log filtered requests
        # 是否记录被过滤的请求
        self.debug = debug

        # Set of request fingerprints
        # 请求指纹的集合
        self.fingerprints: Set = set()

        # Whether to log duplicate requests
        # 是否记录重复的请求
        self.logdupes: bool = True
        self.info: bool = info

        # If a path is provided, open the requests.seen file and load existing fingerprints
        # 如果提供了路径，则打开requests.seen文件并加载现有的指纹
        if path:
            self.file = open(os.path.join(path, 'requests.seen'), 'a+')
            self.file.seek(0)
            self.fingerprints.update(x.rstrip() for x in self.file)

    @classmethod
    def from_crawler(cls, crawler: "aioscrapy.crawler.Crawler"):
        """
        Create a DiskRFPDupeFilter instance from a crawler.
        从爬虫创建DiskRFPDupeFilter实例。

        This is the factory method used by AioScrapy to create the dupefilter.
        这是AioScrapy用于创建重复过滤器的工厂方法。

        Args:
            crawler: The crawler that will use this dupefilter.
                    将使用此重复过滤器的爬虫。

        Returns:
            DiskRFPDupeFilter: A new DiskRFPDupeFilter instance.
                              一个新的DiskRFPDupeFilter实例。
        """
        # Get debug setting from crawler settings
        # 从爬虫设置获取debug设置
        debug = crawler.settings.getbool('DUPEFILTER_DEBUG')

        # Get info setting from crawler settings
        # 从爬虫设置获取info设置
        info = crawler.settings.getbool('DUPEFILTER_INFO')

        # Get job directory from crawler settings, default to './job_dir'
        # 从爬虫设置获取作业目录，默认为'./job_dir'
        path = crawler.settings.get('JOBDIR', './job_dir')

        # Create the job directory if it doesn't exist
        # 如果作业目录不存在，则创建它
        if path and not os.path.exists(path):
            os.makedirs(path)

        # Create and return a new instance
        # 创建并返回一个新实例
        return cls(path, debug, info)

    async def request_seen(self, request: Request) -> bool:
        """
        Check if a request has been seen before.
        检查请求是否已经被看到过。

        This method checks if the request's fingerprint is in the set of seen
        fingerprints. If it is, the request is considered a duplicate. If not,
        the fingerprint is added to the set and written to the requests.seen file.
        此方法检查请求的指纹是否在已见过的指纹集合中。如果是，则认为请求是重复的。
        如果不是，则将指纹添加到集合中并写入requests.seen文件。

        Args:
            request: The request to check.
                    要检查的请求。

        Returns:
            bool: True if the request has been seen before, False otherwise.
                 如果请求之前已经被看到过，则为True，否则为False。
        """
        # Check if the request's fingerprint is in the set of seen fingerprints
        # 检查请求的指纹是否在已见过的指纹集合中
        if request.fingerprint in self.fingerprints:
            return True

        # Add the fingerprint to the set
        # 将指纹添加到集合中
        self.fingerprints.add(request.fingerprint)

        # If we're using a file, write the fingerprint to it
        # 如果我们使用文件，则将指纹写入文件
        if self.file:
            self.file.write(request.fingerprint + '\n')

        # The request has not been seen before
        # 请求之前未被看到过
        return False

    async def close(self, reason: str = '') -> None:
        """
        Close the dupefilter.
        关闭重复过滤器。

        This method is called when the spider is closed. It closes the requests.seen
        file if it was opened.
        当爬虫关闭时调用此方法。如果requests.seen文件已打开，则关闭它。

        Args:
            reason: The reason why the spider was closed.
                   爬虫被关闭的原因。
        """
        # Close the file if it was opened
        # 如果文件已打开，则关闭它
        if self.file:
            self.file.close()


# Alias for backward compatibility
# 用于向后兼容的别名
RFPDupeFilter = DiskRFPDupeFilter
