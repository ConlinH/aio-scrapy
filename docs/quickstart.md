# 快速入门 | Quick Start

本指南将帮助您快速开始使用AioScrapy进行网页爬取。</br>
This guide will help you quickly get started with web scraping using AioScrapy.

## 创建项目 | Create a Project

首先，使用`aioscrapy startproject`命令创建一个新项目：</br>
First, create a new project using the `aioscrapy startproject` command:

```bash
aioscrapy startproject myproject
```

这将创建一个包含以下文件结构的项目：</br>
This will create a project with the following file structure:

```
myproject/
├── aioscrapy.cfg     # 项目配置文件 | Project configuration file
├── myproject/        # 项目的Python模块 | Project's Python module
│   ├── __init__.py
│   ├── middlewares.py  # 项目中间件文件 | Project middleware file
│   ├── pipelines.py    # 项目管道文件 | Project pipeline file
│   ├── settings.py     # 项目设置文件 | Project settings file
│   └── spiders/        # 放置爬虫的目录 | Directory where spiders are placed
│       └── __init__.py
```

## 创建爬虫 | Create a Spider

进入项目目录，并使用`aioscrapy genspider`命令创建一个新的爬虫：</br>
Navigate to the project directory and create a new spider using the `aioscrapy genspider` command:

```bash
cd myproject
aioscrapy genspider example example.com
```

这将在`myproject/spiders`目录下创建一个名为`example.py`的爬虫文件，内容如下：</br>
This will create a spider file named `example.py` in the `myproject/spiders` directory with the following content:

```python
from aioscrapy import Spider


class ExampleSpider(Spider):
    name = 'example'
    custom_settings = {
        "CLOSE_SPIDER_ON_IDLE": True
    }
    start_urls = []

    async def parse(self, response):
        item = {
            'title': '\n'.join(response.xpath('//title/text()').extract()),
        }
        yield item


if __name__ == '__main__':
    ExampleSpider.start()
```

## 编写爬虫 | Write a Spider

编辑爬虫文件，添加起始URL并定义解析逻辑：</br>
Edit the spider file, add starting URLs and define parsing logic:

```python
from aioscrapy import Spider, Request


class ExampleSpider(Spider):
    name = 'example'
    custom_settings = {
        "CLOSE_SPIDER_ON_IDLE": True
    }
    start_urls = ['https://quotes.toscrape.com']

    async def parse(self, response):
        # 提取所有引用 | Extract all quotes
        for quote in response.css('div.quote'):
            yield {
                'text': quote.css('span.text::text').get(),
                'author': quote.xpath('span/small/text()').get(),
                'tags': quote.css('div.tags a.tag::text').getall(),
            }

        # 跟随下一页链接 | Follow link to next page
        next_page = response.css('li.next a::attr(href)').get()
        if next_page is not None:
            yield Request(f"https://quotes.toscrape.com{next_page}", callback=self.parse)


if __name__ == '__main__':
    ExampleSpider.start()
```

## 运行爬虫 | Run the Spider

有两种方式运行爬虫：</br>
There are two ways to run the spider:

### 使用aioscrapy命令 | Using the aioscrapy command

```bash
aioscrapy crawl example
```

### 直接运行Python文件 | Running the Python file directly

```bash
python myproject/spiders/example.py
```

## 处理爬取的数据 | Process Scraped Data

### 使用管道 | Using Pipelines

编辑`myproject/pipelines.py`文件，添加一个处理爬取数据的管道：</br>
Edit the `myproject/pipelines.py` file to add a pipeline for processing scraped data:

```python
from aioscrapy import logger


class MyprojectPipeline:
    def process_item(self, item, spider):
        logger.info(f"Processing item: {item}")
        return item
```

然后在`myproject/settings.py`中启用该管道：
Then enable the pipeline in `myproject/settings.py`:

```python
ITEM_PIPELINES = {
    'myproject.pipelines.MyprojectPipeline': 300,
}
```

## 创建单文件爬虫 | Create a Single-File Spider


AioScrapy也支持创建独立的单文件爬虫，无需完整的项目结构：</br>
AioScrapy also supports creating standalone single-file spiders without a full project structure:

```bash
aioscrapy genspider -t single myspider example.com
```

这将创建一个包含所有必要组件的单文件爬虫：</br>
This will create a single-file spider with all necessary components:

```python
from aioscrapy import Spider, logger


class MyspiderSpider(Spider):
    name = 'myspider'
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


if __name__ == '__main__':
    MyspiderSpider.start()
```

## 下一步 | Next Steps


现在您已经了解了AioScrapy的基础知识，可以继续探索以下主题：</br>
Now that you understand the basics of AioScrapy, you can continue exploring the following topics:

- [爬虫指南](spiders.md) - 了解更多关于爬虫的信息
- [下载器](downloaders.md) - 学习如何配置和使用不同的下载器
- [中间件](middlewares.md) - 了解如何使用中间件扩展功能
- [管道](pipelines.md) - 学习如何处理和存储爬取的数据
- [配置参考](settings.md) - 了解所有可用的配置选项
