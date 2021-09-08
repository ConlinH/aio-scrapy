"""
SSL/TLS指纹随机中间件
"""
import random
import ssl


ORIGIN_CIPHERS = ('ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+HIGH:'
                  'DH+HIGH:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+HIGH:RSA+3DES')


def ssl_ciphers_factory():
    ciphers = ORIGIN_CIPHERS.split(":")
    random.shuffle(ciphers)
    ciphers = ":".join(ciphers)
    ciphers = ciphers + ":!aNULL:!eNULL:!MD5"
    context = ssl.create_default_context()
    context.set_ciphers(ciphers)
    return context


class SSLCiphersMiddleware:
    """Set Basic HTTP Authorization header
    (http_user and http_pass spider class attributes)"""

    def __init__(self, ciphers=None, is_random=False):
        self.ciphers = None if ciphers=='DEFAULT' else ciphers
        self.is_random = is_random

    @classmethod
    def from_crawler(cls, crawler):
        o = cls(ciphers=crawler.settings.get('DOWNLOADER_CLIENT_TLS_CIPHERS', None),
                is_random=crawler.settings.get('RANDOM_TLS_CIPHERS', False))
        return o

    def process_request(self, request, spider):
        if self.is_random:
            request.meta.update({"SSL_CIPHERS": ssl_ciphers_factory()})
        elif self.ciphers:
            request.meta.update({"SSL_CIPHERS": self.ciphers})
