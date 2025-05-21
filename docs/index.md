# AioScrapy 文档 | AioScrapy Documentation

欢迎使用AioScrapy文档！AioScrapy是一个基于Python异步IO的高级Web爬取和抓取框架。
Welcome to the AioScrapy documentation! AioScrapy is a high-level Web Crawling and Web Scraping framework based on Python's asyncio.

## 概述 | Overview

AioScrapy是一个强大的异步网络爬虫框架，它基于Python的asyncio库构建，提供了一套完整的工具，用于高效地从网站提取数据。它的设计理念源自Scrapy，但完全基于异步IO实现，提供更高的性能和更灵活的配置选项。

AioScrapy is a powerful asynchronous web crawling framework built on Python's asyncio library, providing a complete set of tools for efficiently extracting data from websites. Its design philosophy is inspired by Scrapy, but it's completely implemented with asynchronous IO, offering higher performance and more flexible configuration options.

### 主要特性 | Key Features

- **异步架构**：基于Python的asyncio，实现高效的并发爬取
- **灵活的下载器**：支持多种HTTP客户端，包括aiohttp、httpx、requests、pyhttpx和playwright
- **可扩展的中间件系统**：轻松添加自定义功能和处理逻辑
- **强大的数据处理管道**：支持多种数据库存储选项
- **内置信号系统**：方便的事件处理机制
- **丰富的配置选项**：高度可定制的爬虫行为

- **Asynchronous Architecture**: Based on Python's asyncio for efficient concurrent crawling
- **Flexible Downloaders**: Support for multiple HTTP clients including aiohttp, httpx, requests, pyhttpx, and playwright
- **Extensible Middleware System**: Easily add custom functionality and processing logic
- **Powerful Data Processing Pipelines**: Support for various database storage options
- **Built-in Signal System**: Convenient event handling mechanism
- **Rich Configuration Options**: Highly customizable crawler behavior

## 安装 | Installation
### 要求 | Requirements

- Python 3.9+

### 使用pip安装 | Install with pip

```bash
pip install aio-scrapy

# Install the latest aio-scrapy
# pip install git+https://github.com/ConlinH/aio-scrapy
```

### 安装可选依赖 | Install optional dependencies

```bash
# 安装所有可选依赖 | Install all optional dependencies
pip install aio-scrapy[all]

# 仅安装特定依赖 | Install specific dependencies only
pip install aio-scrapy[redis]  # 安装Redis支持 | Install Redis support
pip install aio-scrapy[mysql]  # 安装MySQL支持 | Install MySQL support
pip install aio-scrapy[mongo]  # 安装MongoDB支持 | Install MongoDB support
```

## 快速入门 | Quick Start
### 创建项目 | Create a project

```bash
aioscrapy startproject myproject
cd myproject
```

### 创建爬虫 | Create a spider

```bash
aioscrapy genspider example example.com
```

这将在`myproject/spiders`目录下创建一个名为`example.py`的爬虫文件。
This will create a spider file named `example.py` in the `myproject/spiders` directory.

### 编写爬虫 | Write a spider

```python
from aioscrapy import Spider

class ExampleSpider(Spider):
    name = 'example'
    custom_settings = {
        "CLOSE_SPIDER_ON_IDLE": True
    }
    start_urls = ['https://example.com']

    async def parse(self, response):
        item = {
            'title': '\n'.join(response.xpath('//title/text()').extract()),
        }
        yield item

if __name__ == '__main__':
    ExampleSpider.start()
```

### 运行爬虫 | Run the spider

```bash
aioscrapy crawl example
```

或者直接运行Python文件 | Or run the Python file directly：

```bash
python myproject/spiders/example.py
```

## 文档目录 | Documentation Contents

- [安装指南 | Installation Guide](installation.md)
- [快速入门 | Quick Start](quickstart.md)
- [核心概念 | Core Concepts](concepts.md)
- [爬虫指南 | Spider Guide](spiders.md)
- [下载器 | Downloaders](downloaders.md)
- [中间件 | Middlewares](middlewares.md)
- [管道 | Pipelines](pipelines.md)
- [队列 | Queues](queues.md)
- [请求过滤器 | Request Filters](dupefilters.md)
- [代理 | Proxy](proxy.md)
- [数据库连接 | Database Connections](databases.md)
- [分布式部署 | Distributed Deployment](distributed.md)
- [配置参考 | Settings Reference](settings.md)
- [API参考 | API Reference](api.md)
- [高级用法 | Advanced Usage](advanced.md)
