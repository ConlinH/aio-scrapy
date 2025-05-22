# 管道 | Pipelines

管道是AioScrapy中处理爬虫提取的数据的组件。它们负责处理数据、验证数据、清洗数据，以及将数据存储到数据库或文件中。</br>
Pipelines are components in AioScrapy that process data extracted by spiders. They are responsible for processing data, validating data, cleaning data, and storing data in databases or files.

## 管道架构 | Pipeline Architecture

AioScrapy的管道系统基于一个处理链，每个管道组件按顺序处理爬虫提取的数据项。</br>
AioScrapy's pipeline system is based on a processing chain, where each pipeline component processes items extracted by the spider in sequence.

## 创建管道 | Creating a Pipeline

管道是一个Python类，实现了一个或多个以下方法：</br>
A pipeline is a Python class that implements one or more of the following methods:

```python
class MyPipeline:

    # 这个方法用于从爬虫创建管道实例 | This method is used to create pipeline instances from a crawler
    @classmethod
    async def from_crawler(cls, crawler):
        return cls()


    # 当爬虫开始时调用 | Called when the spider starts
    async def open_spider(self, spider):
        pass

    # 当爬虫关闭时调用 | Called when the spider closes
    async def close_spider(self, spider):
        pass

    # 处理爬虫提取的数据项 | Process items extracted by the spider
    async def process_item(self, item, spider):
        return item  # 返回处理后的数据项，传递给下一个管道 | Return the processed item, pass to the next pipeline

        # 或者 | or
        # raise DropItem(...)  # 丢弃数据项，不再传递给后续管道 | Drop the item, do not pass to subsequent pipelines

```

## 启用管道 | Enabling a Pipeline

要启用管道，将其添加到项目的`settings.py`文件中的`ITEM_PIPELINES`设置：</br>
To enable a pipeline, add it to the `ITEM_PIPELINES` setting in your project's `settings.py` file:

```python
ITEM_PIPELINES = {
    'myproject.pipelines.MyPipeline': 300,
}
```

数字表示管道的顺序，数字越小，管道越靠前执行；数字越大，管道越靠后执行。</br>
The number represents the order of the pipeline, with lower numbers being executed earlier and higher numbers being executed later.

## 内置管道 | Built-in Pipelines

AioScrapy提供了多个内置管道，用于将爬取的数据导出到不同的文件格式或存储到不同的数据库中。这些管道位于`aioscrapy.libs.pipelines`包中。</br>
AioScrapy provides several built-in pipelines for exporting scraped data to different file formats or storing it in different databases. These pipelines are located in the `aioscrapy.libs.pipelines` package.

### 文件导出管道 | File Export Pipelines

#### CsvPipeline | CSV Pipeline

将数据项导出为CSV文件。</br>
Exports items to CSV files.

```python
# 在settings.py中设置
# Set in settings.py
ITEM_PIPELINES = {
    'aioscrapy.libs.pipelines.csv.CsvPipeline': 100,
}

# 在爬虫中使用
# Usage in spider
async def parse(self, response):
    yield {
        'title': 'Example Title',
        'content': 'Example Content',
        '__csv__': {
            'filename': 'articles',  # 文件名（不含扩展名）/ Filename (without extension)
        }
    }
```

#### ExcelPipeline | Excel Pipeline

将数据项导出为Excel文件。</br>
Exports items to Excel files.

```python
# 在settings.py中设置
# Set in settings.py
ITEM_PIPELINES = {
    'aioscrapy.libs.pipelines.excel.ExcelPipeline': 100,
}

# 在爬虫中使用
# Usage in spider
async def parse(self, response):
    yield {
        'title': 'Example Title',
        'content': 'Example Content',
        '__excel__': {
            'filename': 'articles',  # 文件名（不含扩展名）/ Filename (without extension)
            'sheet': 'sheet1',  # 工作表名称 | Sheet name

            # 'img_fields': ['img'],    # 图片字段 当指定图片字段时 自行下载图片 并保存到表格里
            # 'img_size': (100, 100)    # 指定图片大小时 自动将图片转换为指定大小

            # 传递给Workbook的参数 xlsxwriter.Workbook(filename, {'strings_to_urls': False})
            'strings_to_urls': False
        }
    }
```

### 数据库管道 | Database Pipelines

#### MySQLPipeline | MySQL Pipeline

将数据项存储到MySQL数据库。</br>
Stores items in a MySQL database.

```python
# 在settings.py中设置
# Set in settings.py
ITEM_PIPELINES = {
    'aioscrapy.libs.pipelines.mysql.MySQLPipeline': 100,
}

# MySQL连接设置
# MySQL connection settings
MYSQL_ARGS = {
    'default': {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': 'root',
        'db': 'test',
        'charset': 'utf8mb4',
    }
}

# 批量存储设置
# Batch storage settings
SAVE_CACHE_NUM = 1000  # 每次存储的最大数量 | Maximum number of items to store at once
SAVE_CACHE_INTERVAL = 10  # 存储间隔（秒）/ Storage interval (seconds)

# 在爬虫中使用
# Usage in spider
async def parse(self, response):
    yield {
        'title': 'Example Title',
        'content': 'Example Content',
        '__mysql__': {
            'db_alias': 'default',  # MySQL连接别名，对应MYSQL_ARGS中的键 | MySQL connection alias, corresponding to the key in MYSQL_ARGS
            'table_name': 'articles',  # 表名 | Table name

            'insert_type': 'insert',  # 写入数据库的方式： 默认insert方式  
                                      # insert：普通写入 出现主键或唯一键冲突时抛出异常
                                      # update_insert：更新插入 出现主键或唯一键冲突时，更新写入
                                      # ignore_insert：忽略写入 写入时出现冲突 丢掉该条数据 不抛出异常

            # 更新指定字段（只能在insert_type为update_insert的时候使用）
            # 'update_fields': ['title']
        }
    }
```

#### MongoPipeline | MongoDB Pipeline

将数据项存储到MongoDB数据库。</br>
Stores items in a MongoDB database.

```python
# 在settings.py中设置
# Set in settings.py
ITEM_PIPELINES = {
    'aioscrapy.libs.pipelines.mongo.MongoPipeline': 100,
}

# MongoDB连接设置
# MongoDB connection settings
MONGO_ARGS = {
    'default': {
        'host': 'mongodb://localhost:27017',
        'db': 'test',
    }
}

# 批量存储设置
# Batch storage settings
SAVE_CACHE_NUM = 1000  # 每次存储的最大数量 | Maximum number of items to store at once
SAVE_CACHE_INTERVAL = 10  # 存储间隔（秒）/ Storage interval (seconds)

# 在爬虫中使用
# Usage in spider
async def parse(self, response):
    yield {
        'title': 'Example Title',
        'content': 'Example Content',
        '__mongo__': {
            'db_alias': 'default',  # MongoDB连接别名，对应MONGO_ARGS中的键 | MongoDB connection alias, corresponding to the key in MONGO_ARGS
            'table_name': 'articles',  # 集合名称 | Collection name
            # 'db_name': 'custom_db',  # 可选，数据库名称，覆盖MONGO_ARGS中的db | Optional, database name, overrides db in MONGO_ARGS
            # 'ordered': False,  # 可选，批量写入时是否有序 | Optional, whether to use ordered inserts in batch operations
        }
    }
```

#### PGPipeline | PostgreSQL Pipeline

将数据项存储到PostgreSQL数据库。</br>
Stores items in a PostgreSQL database.

```python
# 在settings.py中设置
# Set in settings.py
ITEM_PIPELINES = {
    'aioscrapy.libs.pipelines.pg.PGPipeline': 100,
}

# PostgreSQL连接设置
# PostgreSQL connection settings
PG_ARGS = {
    'default': {
        'user': 'root',
        'password': 'root',
        'database': 'test',
        'host': 'localhost',
        'port': 5432,
    }
}

# 批量存储设置
# Batch storage settings
SAVE_CACHE_NUM = 1000  # 每次存储的最大数量 | Maximum number of items to store at once
SAVE_CACHE_INTERVAL = 10  # 存储间隔（秒）/ Storage interval (seconds)

# 在爬虫中使用
# Usage in spider
async def parse(self, response):
    yield {
        'title': 'Example Title',
        'content': 'Example Content',
        '__pg__': {
            'db_alias': 'default',  # PostgreSQL连接别名，对应PG_ARGS中的键 | PostgreSQL connection alias, corresponding to the key in PG_ARGS
            'table_name': 'test.articles',  # 要存储的schema和表名字，用.隔开 表名 

            'insert_type': 'insert', # 写入数据库的方式： 默认insert方式  
                                        # insert：普通写入 出现主键或唯一键冲突时抛出异常
                                        # update_insert：更新插入 出现on_conflict指定的冲突时，更新写入
                                        # ignore_insert：忽略写入 写入时出现冲突 丢掉该条数据 不抛出异常
            # 'on_conflict': 'id',  # insert_type为update_insert方式下时必需指定约束，不指定默认为conflict为"id"
        }
    }
```

## 管道示例 | Pipeline Examples
### 基本管道 | Basic Pipeline

```python
from aioscrapy import logger

class BasicPipeline:
    def process_item(self, item, spider):
        logger.info(f"Processing item: {item}")
        return item
```

### 数据验证管道 | Data Validation Pipeline

```python
from aioscrapy.exceptions import DropItem

class ValidationPipeline:
    def process_item(self, item, spider):
        if not item.get('title'):
            raise DropItem("Missing title in item")
        if not item.get('url'):
            raise DropItem("Missing url in item")
        return item
```

### 数据清洗管道 | Data Cleaning Pipeline

```python
import re

class CleaningPipeline:

    # 清理标题中的HTML标签 | Clean HTML tags from title
    def process_item(self, item, spider):
        if 'title' in item:
            item['title'] = re.sub(r'<[^>]+>', '', item['title']).strip()

        # 清理描述中的额外空白 | Clean extra whitespace from description
        if 'description' in item:
            item['description'] = re.sub(r'\s+', ' ', item['description']).strip()

        return item
```

### 图片下载管道 | Image Download Pipeline

```python
import os
import aiohttp
from urllib.parse import urlparse
from aioscrapy import logger

class ImageDownloadPipeline:
    def __init__(self, images_dir):
        self.images_dir = images_dir
        self.session = None

    @classmethod
    async def from_crawler(cls, crawler):
        images_dir = crawler.settings.get('IMAGES_DIR', 'images')
        return cls(images_dir)

    async def open_spider(self, spider):
        # 创建图片目录 | Create images directory
        os.makedirs(self.images_dir, exist_ok=True)
        
        # 创建aiohttp会话 | Create aiohttp session
        self.session = aiohttp.ClientSession()


    # 关闭aiohttp会话 | Close aiohttp session
    async def close_spider(self, spider):
        if self.session:
            await self.session.close()

    # 如果项目中有图片URL，下载图片 | If the item has an image URL, download the image
    async def process_item(self, item, spider):

        if 'image_url' in item and item['image_url']:
            try:
                # 解析URL，获取文件名 | Parse URL to get filename
                parsed_url = urlparse(item['image_url'])
                filename = os.path.basename(parsed_url.path)
                if not filename:
                    filename = f"image_{hash(item['image_url'])}.jpg"

                # 下载图片 | Download the image
                async with self.session.get(item['image_url']) as response:
                    if response.status == 200:
                        filepath = os.path.join(self.images_dir, filename)
                        with open(filepath, 'wb') as f:
                            f.write(await response.read())

                        # 将图片路径添加到项目中 | Add image path to the item
                        item['image_path'] = filepath
                        logger.info(f"Downloaded image: {filepath}")
                    else:
                        logger.warning(f"Failed to download image: {item['image_url']}, status: {response.status}")
            except Exception as e:
                logger.error(f"Error downloading image: {item['image_url']}, error: {e}")

        return item
```


### 完整的爬虫示例（使用内置管道）/ Complete Spider Example (Using Built-in Pipelines)

以下是一个使用内置CSV和MongoDB管道的完整爬虫示例：</br>
Here is a complete spider example using the built-in CSV and MongoDB pipelines:

```python
from aioscrapy import Spider, logger, Request

class DemoPipelineSpider(Spider):
    name = 'demo_pipeline'
    custom_settings = {
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36",
        "CLOSE_SPIDER_ON_IDLE": True,

        # 启用多个管道
        # Enable multiple pipelines
        "ITEM_PIPELINES": {
            'aioscrapy.libs.pipelines.csv.CsvPipeline': 100,
            'aioscrapy.libs.pipelines.mongo.MongoPipeline': 200,
        },

        # MongoDB设置
        # MongoDB settings
        "MONGO_ARGS": {
            'default': {
                'host': 'mongodb://localhost:27017',
                'db': 'aioscrapy',
            }
        },

        # 批量存储设置
        # Batch storage settings
        "SAVE_CACHE_NUM": 100,  # 每次存储的最大数量 | Maximum number of items to store at once
        "SAVE_CACHE_INTERVAL": 10,  # 存储间隔（秒）/ Storage interval (seconds)
    }

    start_urls = ['https://quotes.toscrape.com']

    async def parse(self, response):
        for quote in response.css('div.quote'):
            # 创建包含多个导出目标的项目
            # Create an item with multiple export targets
            yield {
                'author': quote.xpath('span/small/text()').get(),
                'text': quote.css('span.text::text').get(),
                'tags': quote.css('div.tags a.tag::text').getall(),

                # CSV导出设置
                # CSV export settings
                '__csv__': {
                    'filename': 'quotes',  # 导出为quotes.csv | Export to quotes.csv
                },

                # MongoDB存储设置
                # MongoDB storage settings
                '__mongo__': {
                    'db_alias': 'default',
                    'table_name': 'quotes',  # 存储到quotes集合 | Store in quotes collection
                }
            }

        # 跟随下一页链接
        # Follow link to next page
        next_page = response.css('li.next a::attr("href")').get()
        if next_page is not None:
            yield Request(response.urljoin(next_page), callback=self.parse)

    async def process_item(self, item):
        # 这个方法会在管道处理之后被调用
        # This method will be called after pipeline processing
        logger.info(f"Processed item: {item}")

if __name__ == '__main__':
    DemoPipelineSpider.start()
```

## 最佳实践 | Best Practices

1. **保持管道简单**：每个管道应该只关注一个功能
2. **正确处理异常**：确保在管道中正确处理异常，避免中断整个处理链
3. **注意管道顺序**：管道的执行顺序很重要，确保它们按照预期的顺序执行
4. **使用`from_crawler`方法**：使用`from_crawler`方法从爬虫获取设置
5. **异步处理**：所有管道方法都应该是异步的，避免阻塞操作
6. **批量处理**：对于数据库操作，考虑批量处理以提高性能
7. **资源管理**：在`open_spider`和`close_spider`方法中正确管理资源

</br>

1. **Keep Pipelines Simple**: Each pipeline should focus on a single functionality
2. **Handle Exceptions Properly**: Make sure to handle exceptions correctly in pipelines to avoid interrupting the entire processing chain
3. **Pay Attention to Pipeline Order**: The execution order of pipelines is important, ensure they execute in the expected order
4. **Use the `from_crawler` Method**: Use the `from_crawler` method to get settings from the crawler
5. **Asynchronous Processing**: All pipeline methods should be asynchronous, avoid blocking operations
6. **Batch Processing**: For database operations, consider batch processing to improve performance
7. **Resource Management**: Properly manage resources in the `open_spider` and `close_spider` methods
