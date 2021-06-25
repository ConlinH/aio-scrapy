
try:
    from asyncio.exceptions import TimeoutError
except:
    from concurrent.futures._base import TimeoutError
from aiohttp.client_exceptions import ClientError

from scrapy.downloadermiddlewares.retry import RetryMiddleware as ScrapyRetryMiddleware


class RetryMiddleware(ScrapyRetryMiddleware):

    EXCEPTIONS_TO_RETRY = ScrapyRetryMiddleware.EXCEPTIONS_TO_RETRY + (TimeoutError, ClientError)
