# _*_ coding: utf-8 _*_

""" 响应类 """
import re

from scrapy.http import Response
from scrapy.http import TextResponse as STextResponse

__all__ = ['Response', 'TextResponse']


class TextResponse(STextResponse):
    def __init__(self, *args, **kwargs):
        self.cookies = self.deal_cookies(kwargs.pop("cookies", None))
        super().__init__(*args, **kwargs)

    @staticmethod
    def deal_cookies(cookies_raw):
        cookies = {}
        if cookies_raw is None:
            return cookies
        cookies_str = cookies_raw.output()
        for cookie in re.findall(r'Set-Cookie: (.*?)=(.*?); Domain', cookies_str, re.S):
            cookies[cookie[0]] = cookie[1]
        return cookies
