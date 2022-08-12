"""
aioscrapy - a web crawling and web scraping framework written for Python
"""

import pkgutil
import sys

# Declare top-level shortcuts
from aioscrapy.spiders import Spider
from aioscrapy.http import Request, FormRequest
from aioscrapy.settings import Settings
from aioscrapy.crawler import Crawler


__all__ = [
    '__version__', 'version_info', 'Spider', 'Request', 'FormRequest', 'Crawler'
]


# aioscrapy versions
__version__ = (pkgutil.get_data(__package__, "VERSION") or b"").decode("ascii").strip()
version_info = tuple(int(v) if v.isdigit() else v for v in __version__.split('.'))


# Check minimum required Python version
if sys.version_info < (3, 7):
    print("aioscrapy %s requires Python 3.7+" % __version__)
    sys.exit(1)


del pkgutil
del sys
