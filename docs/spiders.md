# 爬虫指南 | Spider Guide

爬虫是AioScrapy的核心组件，负责定义如何爬取网站和提取数据。
Spiders are the core components of AioScrapy, responsible for defining how to crawl websites and extract data.

## 爬虫类 | Spider Class

所有AioScrapy爬虫必须继承自`Spider`基类：
All AioScrapy spiders must inherit from the `Spider` base class:

```python
from aioscrapy import Spider

class MySpider(Spider):
    name = 'myspider'
    start_urls = ['https://example.com']

    async def parse(self, response): 
    # 解析响应并提取数据 | Parse response and extract data
        pass
```

### 主要属性 | Main Attributes

- **name**：爬虫的唯一标识符，必须是唯一的
- **proxy**：可选的代理处理器
- **dupefilter**：可选的重复过滤器
- **custom_settings**：用于覆盖项目设置的字典
- **stats**：统计收集器
- **pause**：爬虫是否暂停
- **start_urls**：开始爬取的URL列表

- **name**: The unique identifier for the spider, must be unique
- **proxy**: Optional proxy handler
- **dupefilter**: Optional duplicate filter
- **custom_settings**: Dictionary of settings to override project settings
- **stats**: Statistics collector
- **pause**: Whether the spider is paused
- **start_urls**: List of URLs to start crawling from

### 主要方法 | Main Methods
#### `__init__(self, name=None, **kwargs)`

初始化爬虫。
Initialize the spider.

```python
def __init__(self, name=None, **kwargs):
    if name is not None:
        self.name = name
    elif not getattr(self, 'name', None):
        raise ValueError(f"{type(self).__name__} must have a name")
    self.__dict__.update(kwargs)
    if not hasattr(self, 'start_urls'):
        self.start_urls = []
```

#### `async parse(self, response)`

处理下载的响应并提取数据。这是爬虫的主要方法，必须在子类中实现。
Process downloaded responses and extract data. This is the main method of the spider and must be implemented in subclasses.

```python
async def parse(self, response):
    """
    Default callback used to process downloaded responses.
    用于处理下载响应的默认回调方法。

    This method must be implemented in subclasses.
    必须在子类中实现此方法。
    """
    raise NotImplementedError(f'{self.__class__.__name__}.parse callback is not defined')
```

#### `@classmethod update_settings(cls, settings)`

使用爬虫自定义设置更新设置。
Update settings with spider custom settings.

```python
@classmethod
def update_settings(cls, settings):
    settings.setdict(cls.custom_settings or {}, priority='spider')
```

#### `@classmethod start(cls, setting_path=None, use_windows_selector_eventLoop: bool = False)`

使用此爬虫开始爬取。这是一个便捷方法，它创建一个CrawlerProcess，添加爬虫，并启动爬取过程。
Start crawling using this spider. This is a convenience method that creates a CrawlerProcess, adds the spider, and starts the crawling process.

```python
@classmethod
def start(cls, setting_path=None, use_windows_selector_eventLoop: bool = False):
    from aioscrapy.crawler import CrawlerProcess
    from aioscrapy.utils.project import get_project_settings

    settings = get_project_settings()
    if setting_path is not None:
        settings.setmodule(setting_path)
    cp = CrawlerProcess(settings)
    cp.crawl(cls)
    cp.start(use_windows_selector_eventLoop)
```

## 爬虫类型 | Spider Types
### 基本爬虫 | Basic Spider

最简单的爬虫类型，适用于简单的爬取任务：
The simplest type of spider, suitable for simple crawling tasks:

```python
from aioscrapy import Spider

class BasicSpider(Spider):
    name = 'basic'
    start_urls = ['https://example.com']

    async def parse(self, response):
# 提取数据 | Extract data

        yield {'title': response.css('title::text').get()}
        
# 跟随链接 | Follow links

        for href in response.css('a::attr(href)'):
            yield response.follow(href, self.parse)
```

### 单文件爬虫 | Single-File Spider

包含所有必要组件的独立爬虫：
A standalone spider that contains all necessary components:

```python
from aioscrapy import Spider, logger

class SingleSpider(Spider):
    name = 'single'
    custom_settings = {
        "CLOSE_SPIDER_ON_IDLE": True
    }
    start_urls = ["https://quotes.toscrape.com"]

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
            item = {
                'author': quote.xpath('span/small/text()').get(),
                'text': quote.css('span.text::text').get(),
            }
            yield item

    async def process_item(self, item):
        logger.info(item)
```

## 爬虫生命周期 | Spider Lifecycle

1. **初始化**：爬虫实例被创建
2. **开始请求**：生成初始请求
3. **处理响应**：使用回调函数处理响应
4. **提取数据**：从响应中提取数据
5. **生成新请求**：根据需要生成新的请求
6. **关闭**：爬取完成后关闭爬虫

1. **Initialization**: The spider instance is created
2. **Start Requests**: Initial requests are generated
3. **Process Responses**: Responses are processed using callback functions
4. **Extract Data**: Data is extracted from responses
5. **Generate New Requests**: New requests are generated as needed
6. **Close**: The spider is closed after crawling is complete

## 请求和响应 | Requests and Responses
### 创建请求 | Creating Requests

```python
from aioscrapy import Request

# 基本请求 | Basic request

request = Request(url='https://example.com')

# 带回调的请求 | Request with callback

request = Request(
    url='https://example.com',
    callback=self.parse_item
)

# 带元数据的请求 | Request with metadata

request = Request(
    url='https://example.com',
    meta={'key': 'value'}
)

# 带请求头的请求 | Request with headers

request = Request(
    url='https://example.com',
    headers={'User-Agent': 'Custom User Agent'}
)
```

### 处理响应 | Processing Responses

```python
async def parse(self, response):
    # 使用CSS选择器提取数据 | Extract data using CSS selectors
    title = response.css('title::text').get()
    
    # 使用XPath提取数据 | Extract data using XPath
    heading = response.xpath('//h1/text()').get()
    
    # 提取多个元素 | Extract multiple elements
    paragraphs = response.css('p::text').getall()
    
    # 跟随链接 | Follow links
    for href in response.css('a::attr(href)'):
        yield response.follow(href, self.parse_item)
```

## 最佳实践 | Best Practices

1. **使用描述性名称**：为爬虫和回调函数使用描述性名称
2. **分离关注点**：使用不同的回调函数处理不同类型的页面
3. **使用元数据**：通过请求的`meta`属性传递数据
4. **处理错误**：实现错误处理逻辑
5. **限制请求速率**：使用设置控制爬取速度
6. **遵守robots.txt**：尊重网站的爬取规则

1. **Use Descriptive Names**: Use descriptive names for spiders and callback functions
2. **Separate Concerns**: Use different callback functions for different types of pages
3. **Use Metadata**: Pass data through the `meta` attribute of requests
4. **Handle Errors**: Implement error handling logic
5. **Limit Request Rate**: Use settings to control crawling speed
6. **Respect robots.txt**: Honor website crawling rules
