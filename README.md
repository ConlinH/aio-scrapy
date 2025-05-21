# AioScrapy

AioScrapy是一个基于Python异步IO的强大网络爬虫框架。它的设计理念源自Scrapy，但完全基于异步IO实现，提供更高的性能和更灵活的配置选项。</br>
AioScrapy is a powerful asynchronous web crawling framework built on Python's asyncio library. It is inspired by Scrapy but completely reimplemented with asynchronous IO, offering higher performance and more flexible configuration options.

## 特性 | Features

- **完全异步**：基于Python的asyncio库，实现高效的并发爬取
- **多种下载处理程序**：支持多种HTTP客户端，包括aiohttp、httpx、requests、pyhttpx、curl_cffi、DrissionPage和playwright
- **灵活的中间件系统**：轻松添加自定义功能和处理逻辑
- **强大的数据处理管道**：支持多种数据库存储选项
- **内置信号系统**：方便的事件处理机制
- **丰富的配置选项**：高度可定制的爬虫行为
- **分布式爬取**：支持使用Redis和RabbitMQ进行分布式爬取
- **数据库集成**：内置支持Redis、MySQL、MongoDB、PostgreSQL和RabbitMQ


- **Fully Asynchronous**: Built on Python's asyncio for efficient concurrent crawling
- **Multiple Download Handlers**: Support for various HTTP clients including aiohttp, httpx, requests, pyhttpx, curl_cffi, DrissionPage and playwright
- **Flexible Middleware System**: Easily add custom functionality and processing logic
- **Powerful Data Processing Pipelines**: Support for various database storage options
- **Built-in Signal System**: Convenient event handling mechanism
- **Rich Configuration Options**: Highly customizable crawler behavior
- **Distributed Crawling**: Support for distributed crawling using Redis and RabbitMQ
- **Database Integration**: Built-in support for Redis, MySQL, MongoDB, PostgreSQL, and RabbitMQ

## 安装 | Installation

### 要求 | Requirements

- Python 3.9+

### 使用pip安装 | Install with pip

```bash
pip install aio-scrapy

# Install the latest aio-scrapy
# pip install git+https://github.com/ConlinH/aio-scrapy
```

## 文档 | Documentation

## 文档目录 | Documentation Contents
- [安装指南 | Installation Guide](docs/installation.md)
- [快速入门 | Quick Start](docs/quickstart.md)
- [核心概念 | Core Concepts](docs/concepts.md)
- [爬虫指南 | Spider Guide](docs/spiders.md)
- [下载器 | Downloaders](docs/downloaders.md)
- [中间件 | Middlewares](docs/middlewares.md)
- [管道 | Pipelines](docs/pipelines.md)
- [队列 | Queues](docs/queues.md)
- [请求过滤器 | Request Filters](docs/dupefilters.md)
- [代理 | Proxy](docs/proxy.md)
- [数据库连接 | Database Connections](docs/databases.md)
- [分布式部署 | Distributed Deployment](docs/distributed.md)
- [配置参考 | Settings Reference](docs/settings.md)
- [API参考 | API Reference](docs/api.md)
- [示例 | Example](example)

## 许可证 | License

本项目采用MIT许可证 - 详情请查看LICENSE文件。</br>
This project is licensed under the MIT License - see the LICENSE file for details.


## 联系
QQ: 995018884 </br>
WeChat: h995018884