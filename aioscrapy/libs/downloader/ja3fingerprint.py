"""
SSL/TLS指纹随机中间件
"""
import random


ORIGIN_CIPHERS = ('ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+HIGH:'
                  'DH+HIGH:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+HIGH:RSA+3DES:!aNULL:!eNULL:!MD5')


class TLSCiphersMiddleware:
    """SSL/TLS指纹中间件"""

    def __init__(self, ciphers, is_random):
        if ciphers == 'DEFAULT':
            self.ciphers = None

        self.is_random = is_random

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            ciphers=crawler.settings.get('DOWNLOADER_CLIENT_TLS_CIPHERS', 'DEFAULT'),
            is_random=crawler.settings.get('RANDOM_TLS_CIPHERS', False)
        )

    def process_request(self, request, spider):
        if not (self.ciphers or self.is_random):
            return

        ciphers = self.ciphers or ORIGIN_CIPHERS
        if self.is_random:
            ciphers = ciphers.split(":")
            random.shuffle(ciphers)
            ciphers = ":".join(ciphers)
        request.meta['TLS_CIPHERS'] = ciphers
