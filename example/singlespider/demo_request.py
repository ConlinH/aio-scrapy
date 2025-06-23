import json
from aioscrapy import Spider
from aioscrapy.http import Response, Request, FormRequest, JsonRequest


class DemoRequestSpider(Spider):
    name = 'DemoRequestSpider'

    custom_settings = dict(
        CONCURRENT_REQUESTS=1,
        LOG_LEVEL='INFO',
        CLOSE_SPIDER_ON_IDLE=True,
        DOWNLOAD_HANDLERS_TYPE="aiohttp",
        # DOWNLOAD_HANDLERS_TYPE="curl_cffi",
        # DOWNLOAD_HANDLERS_TYPE="requests",
        # DOWNLOAD_HANDLERS_TYPE="httpx",
        # DOWNLOAD_HANDLERS_TYPE="pyhttpx",
    )

    start_urls = []

    async def start_requests(self):
        # 发送get请求
        # 等价于 requests.get("https://httpbin.org/get", params=dict(test="test"))
        yield Request("https://httpbin.org/get?a=a", params=dict(b="b"))

        # 发送post form请求
        # 等价于 requests.post("https://httpbin.org/post", data=dict(test="test"))
        yield Request("https://httpbin.org/post", method='POST', data=dict(test="test"))    # 写法一 (推荐)
        yield FormRequest("https://httpbin.org/post", formdata=dict(test="test"))         # 写法二
        yield Request("https://httpbin.org/post", method='POST', body="test=test",          # 写法三 (不推荐)
                      headers={'Content-Type': 'application/x-www-form-urlencoded'})

        # 发送post json请求
        # 等价于 requests.post("https://httpbin.org/post", json=dict(test="test"))
        yield Request("https://httpbin.org/post", method='POST', json=dict(test="test"))    # 写法一 (推荐)
        yield JsonRequest("https://httpbin.org/post", data=dict(test="test"))             # 写法二
        yield Request("https://httpbin.org/post", method='POST',                            # 写法三 (不推荐)
                      body=json.dumps(dict(test="test")),
                      headers={'Content-Type': 'application/json'})

    async def parse(self, response: Response):
        print(response.text)


if __name__ == '__main__':
    DemoRequestSpider.start()
