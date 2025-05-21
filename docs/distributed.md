# 分布式部署 | Distributed Deployment

AioScrapy支持分布式爬取，允许多个爬虫实例协同工作，提高爬取效率。本文档介绍了如何使用AioScrapy进行分布式部署。</br>
AioScrapy supports distributed crawling, allowing multiple spider instances to work together to improve crawling efficiency. This document describes how to use AioScrapy for distributed deployment.

## 分布式架构 | Distributed Architecture

AioScrapy的分布式架构基于以下组件：</br>
AioScrapy's distributed architecture is based on the following components:

1. **Redis队列**：存储待处理的请求，多个爬虫实例共享同一个队列
2. **Redis过滤器**：避免重复爬取相同的URL，多个爬虫实例共享同一个过滤器
3. **Scrapyd**：管理爬虫的部署和运行，提供REST API来控制爬虫

</br>

1. **Redis Queue**: Stores pending requests, multiple spider instances share the same queue
2. **Redis Filter**: Avoids crawling the same URL multiple times, multiple spider instances share the same filter
3. **Scrapyd**: Manages spider deployment and execution, provides a REST API to control spiders

## 使用Redis进行分布式爬取 | Using Redis for Distributed Crawling
### 配置Redis队列和过滤器 | Configuring Redis Queue and Filter

要使用Redis进行分布式爬取，您需要配置Redis队列和过滤器：</br>
To use Redis for distributed crawling, you need to configure Redis queue and filter:

```python
# 在settings.py中设置 | Set in settings.py

# 使用Redis队列 | Use Redis queue
SCHEDULER_QUEUE_CLASS = 'aioscrapy.queue.redis.SpiderPriorityQueue'

# 使用Redis过滤器 | Use Redis filter
DUPEFILTER_CLASS = 'aioscrapy.dupefilters.redis.RedisBloomDupeFilter'
BLOOMFILTER_BIT = 30
BLOOMFILTER_HASH_NUMBER = 6

# 启动时不清空队列，允许多个爬虫实例共享队列 | Don't clear the queue on startup, allowing multiple spider instances to share the queue
SCHEDULER_FLUSH_ON_START = False

# Redis连接设置 | Redis connection settings
REDIS_ARGS = {
    'queue': {
        'url': 'redis://localhost:6379/0',
        'max_connections': 10,
        'timeout': 30,
    }
}

```

### 创建分布式爬虫 | Creating a Distributed Spider

```python
from aioscrapy import Spider, Request

class DistributedSpider(Spider):
    name = 'distributed'
    start_urls = ['https://example.com']
    
    custom_settings = {
        'SCHEDULER_QUEUE_CLASS': 'aioscrapy.queue.redis.SpiderPriorityQueue',
        'DUPEFILTER_CLASS': 'aioscrapy.dupefilters.redis.RedisBloomDupeFilter',
        'SCHEDULER_FLUSH_ON_START': False,
        'REDIS_ARGS': {
            'queue': {
                'url': 'redis://localhost:6379/0',
            }
        },
        'BLOOMFILTER_BIT': 30,
        'BLOOMFILTER_HASH_NUMBER': 6,
    }
    
    # 处理响应 | Process the response
    async def parse(self, response):
        yield {'url': response.url, 'title': response.css('title::text').get()}
        
        # 添加新请求到队列 | Add new requests to the queue
        for href in response.css('a::attr(href)'):
            yield Request(response.urljoin(href), callback=self.parse)
```

### 运行分布式爬虫 | Running Distributed Spiders

您可以在多台机器上运行相同的爬虫，它们将共享Redis中的请求队列和已处理的URL集合：</br>
You can run the same spider on multiple machines, and they will share the request queue and processed URL set in Redis:

```bash
# 在机器A上运行 | Run on machine A
aioscrapy crawl distributed

# 在机器B上运行 | Run on machine B
aioscrapy crawl distributed

# 在机器C上运行 | Run on machine C
aioscrapy crawl distributed
```

## 使用Scrapyd进行分布式部署 | Using Scrapyd for Distributed Deployment

Scrapyd是一个用于部署和运行Scrapy爬虫的应用程序，AioScrapy提供了与Scrapyd兼容的接口，允许您使用Scrapyd来管理AioScrapy爬虫。</br>
Scrapyd is an application for deploying and running Scrapy spiders, and AioScrapy provides a Scrapyd-compatible interface that allows you to use Scrapyd to manage AioScrapy spiders.

### 安装Scrapyd | Installing Scrapyd

```bash
pip install scrapyd
```

### 配置Scrapyd | Configuring Scrapyd

创建一个`scrapyd.conf`文件，配置Scrapyd使用AioScrapy的运行器：</br>
Create a `scrapyd.conf` file, configuring Scrapyd to use AioScrapy's runner:

```ini
[scrapyd]
eggs_dir    = eggs
logs_dir    = logs
items_dir   =
jobs_to_keep = 5
dbs_dir     = dbs
max_proc    = 0
max_proc_per_cpu = 4
finished_to_keep = 100
poll_interval = 5.0
bind_address = 0.0.0.0
http_port   = 6800
debug       = off
runner      = aioscrapy.scrapyd.runner
application = scrapyd.app.application
launcher    = scrapyd.launcher.Launcher
webroot     = scrapyd.website.Root

[services]
schedule.json     = scrapyd.webservice.Schedule
cancel.json       = scrapyd.webservice.Cancel
addversion.json   = scrapyd.webservice.AddVersion
listprojects.json = scrapyd.webservice.ListProjects
listversions.json = scrapyd.webservice.ListVersions
listspiders.json  = scrapyd.webservice.ListSpiders
delproject.json   = scrapyd.webservice.DeleteProject
delversion.json   = scrapyd.webservice.DeleteVersion
listjobs.json     = scrapyd.webservice.ListJobs
daemonstatus.json = scrapyd.webservice.DaemonStatus
```

### 启动Scrapyd | Starting Scrapyd

```bash
scrapyd
```

Scrapyd将在`http://localhost:6800`上启动一个Web服务器，您可以通过这个Web界面来管理爬虫。</br>
Scrapyd will start a web server at `http://localhost:6800`, and you can manage spiders through this web interface.

### 配置项目 | Configuring the Project

在项目根目录下创建一个`setup.py`文件：</br>
Create a `setup.py` file in the project root directory:

```python
from setuptools import setup, find_packages

setup(
    name         = 'project',
    version      = '1.0',
    packages     = find_packages(),
    entry_points = {'aioscrapy': ['settings = myproject.settings']},
)
```

在项目根目录下创建一个`aioscrapy.cfg`文件：</br>
Create an `aioscrapy.cfg` file in the project root directory:

```ini
[settings]
default = myproject.settings

[deploy:local]
url = http://localhost:6800/
project = myproject

[deploy:production]
url = http://example.com:6800/
project = myproject
```

### 部署爬虫 | Deploying Spiders

使用`scrapyd-deploy`命令部署爬虫：</br>
Use the `scrapyd-deploy` command to deploy spiders:

```bash
# 安装scrapyd-client | Install scrapyd-client
pip install scrapyd-client

# 部署到本地Scrapyd | Deploy to local Scrapyd
scrapyd-deploy local

# 部署到生产环境Scrapyd | Deploy to production Scrapyd
scrapyd-deploy production
```

或者使用AioScrapy提供的`deploy.py`脚本：</br>
Or use the `deploy.py` script provided by AioScrapy:

```bash
# 创建deploy.py脚本 | Create deploy.py script
python -c "from aioscrapy.commands.deploy import main; main()" > deploy.py

# 部署到本地Scrapyd | Deploy to local Scrapyd
python deploy.py local

# 部署到生产环境Scrapyd | Deploy to production Scrapyd
python deploy.py production
```

### 运行爬虫 | Running Spiders

通过Scrapyd的REST API运行爬虫：</br>
Run spiders through Scrapyd's REST API:

```bash
# 使用curl | Using curl
curl http://localhost:6800/schedule.json -d project=myproject -d spider=distributed

# 使用Python requests | Using Python requests
import requests
requests.post('http://localhost:6800/schedule.json', data={
    'project': 'myproject',
    'spider': 'distributed'
})
```

### 监控爬虫 | Monitoring Spiders

通过Scrapyd的REST API监控爬虫：</br>
Monitor spiders through Scrapyd's REST API:

```bash
# 列出所有项目 | List all projects
curl http://localhost:6800/listprojects.json

# 列出项目中的所有爬虫 | List all spiders in a project
curl http://localhost:6800/listspiders.json?project=myproject

# 列出所有正在运行的爬虫 | List all running spiders
curl http://localhost:6800/listjobs.json?project=myproject
```

### 取消爬虫 | Canceling Spiders

通过Scrapyd的REST API取消爬虫：</br>
Cancel spiders through Scrapyd's REST API:

```bash
# 取消爬虫 | Cancel a spider
curl http://localhost:6800/cancel.json -d project=myproject -d job=jobid
```

## 分布式部署最佳实践 | Best Practices for Distributed Deployment

1. **使用Redis队列和过滤器**：确保所有爬虫实例共享同一个请求队列和过滤器
2. **配置适当的并发设置**：根据服务器性能和目标网站的限制调整并发设置
3. **使用Scrapyd管理爬虫**：使用Scrapyd来部署、运行和监控爬虫
4. **使用Redis存储爬取结果**：将爬取结果存储在Redis中，方便后续处理
5. **使用监控工具**：使用监控工具来跟踪爬虫的性能和状态

</br>

1. **Use Redis Queue and Filter**: Ensure all spider instances share the same request queue and filter
2. **Configure Appropriate Concurrency Settings**: Adjust concurrency settings based on server performance and target website limitations
3. **Use Scrapyd to Manage Spiders**: Use Scrapyd to deploy, run, and monitor spiders
4. **Use Redis to Store Crawling Results**: Store crawling results in Redis for easy subsequent processing
5. **Use Monitoring Tools**: Use monitoring tools to track spider performance and status

## 分布式部署示例 | Distributed Deployment Example
### 项目结构 | Project Structure

```
myproject/
├── aioscrapy.cfg
├── setup.py
├── deploy.py
├── myproject/
│   ├── __init__.py
│   ├── middlewares.py
│   ├── pipelines.py
│   ├── settings.py
│   └── spiders/
│       ├── __init__.py
│       └── distributed.py
```

### settings.py

```python
# myproject/settings.py
# 基本设置 | Basic settings

BOT_NAME = 'myproject'
SPIDER_MODULES = ['myproject.spiders']
NEWSPIDER_MODULE = 'myproject.spiders'

# 并发设置 | Concurrency settings
CONCURRENT_REQUESTS = 32
CONCURRENT_REQUESTS_PER_DOMAIN = 16
# DOWNLOAD_DELAY = 0.5
# RANDOMIZE_DOWNLOAD_DELAY = True

# 分布式设置 | Distributed settings
SCHEDULER_QUEUE_CLASS = 'aioscrapy.queue.redis.SpiderPriorityQueue'
DUPEFILTER_CLASS = 'aioscrapy.dupefilters.redis.RedisBloomDupeFilter'
SCHEDULER_FLUSH_ON_START = False

# Redis设置 | Redis settings
REDIS_ARGS = {
    'queue': {
        'url': 'redis://localhost:6379/0',
        'max_connections': 10,
        'timeout': 30,
    }
}

# 布隆过滤器设置 | Bloom filter settings
BLOOMFILTER_BIT = 30
BLOOMFILTER_HASH_NUMBER = 6

# 管道设置 | Pipeline settings
ITEM_PIPELINES = {
    'myproject.pipelines.RedisPipeline': 300,
}
```

### distributed.py

```python
# myproject/spiders/distributed.py

from aioscrapy import Spider, Request

class DistributedSpider(Spider):
    name = 'distributed'
    start_urls = ['https://example.com']
    
    # 处理响应 | Process the response
    async def parse(self, response):
        yield {
            'url': response.url, 
            'title': response.css('title::text').get()
        }
        
        # 添加新请求到队列 | Add new requests to the queue
        for href in response.css('a::attr(href)'):
            yield Request(response.urljoin(href), callback=self.parse)
```

### pipelines.py

```python
# myproject/pipelines.py

from aioscrapy.db import db_manager

class RedisPipeline:
    def __init__(self):
        self.redis = None
    
    async def open_spider(self, spider):
        self.redis = db_manager.redis('queue')
    
    # 将爬取结果存储在Redis中 | Store crawling results in Redis
    async def process_item(self, item, spider):
        await self.redis.lpush('items', str(item))
        return item
```
