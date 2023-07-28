<!--
![aio-scrapy](./doc/images/aio-scrapy.png)
-->
### aio-scrapy

An asyncio + aiolibs crawler  imitate scrapy framework

English | [中文](./doc/README_ZH.md)

### Overview
- aio-scrapy framework is base on opensource project Scrapy & scrapy_redis.
- aio-scrapy implements compatibility with scrapyd.
- aio-scrapy implements redis queue and rabbitmq queue.
- aio-scrapy is a fast high-level web crawling and web scraping framework, used to crawl websites and extract structured data from their pages.
- Distributed crawling/scraping.
### Requirements

- Python 3.9+
- Works on Linux, Windows, macOS, BSD

### Install

The quick way:

```shell
# Install the latest aio-scrapy
pip install git+https://github.com/conlin-huang/aio-scrapy

# default
pip install aio-scrapy

# Install all dependencies 
pip install aio-scrapy[all]

# When you need to use mysql/httpx/rabbitmq/mongo
pip install aio-scrapy[aiomysql,httpx,aio-pika,mongo]
```

### Usage

#### create project spider:

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

run the spider:

```shell
aioscrapy crawl quotes
```

#### create single script spider:

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

run the spider:

```shell
aioscrapy runspider quotes.py
```


### more commands:

```shell
aioscrapy -h
```

### Documentation
[doc](./doc/documentation.md)

### Ready

please submit your sugguestion to owner by issue

## Thanks

[aiohttp](https://github.com/aio-libs/aiohttp/)

[scrapy](https://github.com/scrapy/scrapy)

