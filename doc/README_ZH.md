
<!--
![aio-scrapy](./images/aio-scrapy.png)
-->
### aio-scrapy

基于asyncio及aio全家桶, 使用scrapy框架流程及标准的一个异步爬虫框架

[English](../README.md) | 中文

### 概述

- aio-scrapy框架基于开源项目Scrapy & scrapy_redis，可以理解为scrapy-redis的asyncio版本。
- aio-scrapy实现了对scrapyd的支持。
- aio-scrapy实现了redis队列和rabbitmq队列。
- aio-scrapy是一个快速的高级web爬行和web抓取框架，用于抓取网站并从其页面提取结构化数据。
- 分布式爬虫。
### 需求

- Python 3.9+
- Works on Linux, Windows, macOS, BSD

### 安装

快速安装方式:

```shell
# 安装最新的代码
pip install git+https://github.com/conlin-huang/aio-scrapy

# default
pip install aio-scrapy

# 安装所有的依赖
pip install aio-scrapy[all]

# 需要使用到mysql/httpx/rabbitmq/mongo相关功能
pip install aio-scrapy[aiomysql,httpx,aio-pika,mongo]
```

### 用法

#### 创建项目爬虫:

```shell
aioscrapy startproject project_quotes
```

```
cd project_quotes
aioscrapy genspider quotes 
```

quotes.py

```python
from aioscrapy.spiders import Spider


class QuotesMemorySpider(Spider):
    name = 'QuotesMemorySpider'

    start_urls = ['https://quotes.toscrape.com']

    async def parse(self, response):
        for quote in response.css('div.quote'):
            yield {
                'author': quote.xpath('span/small/text()').get(),
                'text': quote.css('span.text::text').get(),
            }

        next_page = response.css('li.next a::attr("href")').get()
        if next_page is not None:
            yield response.follow(next_page, self.parse)


if __name__ == '__main__':
    QuotesMemorySpider.start()

```

运行爬虫:

```shell
aioscrapy crawl quotes
```

#### 创建单个爬虫脚本:

```shell
aioscrapy genspider single_quotes -t single
```

single_quotes.py:

```python
from aioscrapy.spiders import Spider


class QuotesMemorySpider(Spider):
    name = 'QuotesMemorySpider'
    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        'CLOSE_SPIDER_ON_IDLE': True,
        # 'DOWNLOAD_DELAY': 3,
        # 'RANDOMIZE_DOWNLOAD_DELAY': True,
        # 'CONCURRENT_REQUESTS': 1,
        # 'LOG_LEVEL': 'INFO'
    }

    start_urls = ['https://quotes.toscrape.com']

    @staticmethod
    async def process_request(request, spider):
        """ request middleware """
        pass

    @staticmethod
    async def process_response(request, response, spider):
        """ response middleware """
        return response

    @staticmethod
    async def process_exception(request, exception, spider):
        """ exception middleware """
        pass

    async def parse(self, response):
        for quote in response.css('div.quote'):
            yield {
                'author': quote.xpath('span/small/text()').get(),
                'text': quote.css('span.text::text').get(),
            }

        next_page = response.css('li.next a::attr("href")').get()
        if next_page is not None:
            yield response.follow(next_page, self.parse)

    async def process_item(self, item):
        print(item)


if __name__ == '__main__':
    QuotesMemorySpider.start()

```

运行爬虫:

```shell
aioscrapy runspider quotes.py
```


### 更多命令:

```shell
aioscrapy -h
```

#### [查看更多使用案例](./example)

### 使用文档

[文档](./documentation_zh.md)

### 准备

请向我通过issue的方式提出您的建议

### 联系

QQ: 995018884
WeChat: h995018884

## 感谢

[aiohttp](https://github.com/aio-libs/aiohttp/)

[scrapy](https://github.com/scrapy/scrapy)

