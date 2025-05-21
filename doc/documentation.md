
English | [中文](./documentation_zh.md)
### Scheduler Queue
`SCHEDULER_QUEUE_CLASS`: gets the queue type of the request task, The default type is `memory`.
##### memory
```python
SCHEDULER_QUEUE_CLASS = 'aioscrapy.queue.memory.SpiderPriorityQueue'
```
##### reids
```python
SCHEDULER_QUEUE_CLASS = 'aioscrapy.queue.redis.SpiderPriorityQueue'

# redis parameter
REDIS_ARGS = {
    'queue': {
        'url': 'redis://192.168.234.128:6379/1',
        'max_connections': 2,
        'timeout': None,
        'retry_on_timeout': True,
        'health_check_interval': 30,
    }
}
```
##### rabbitMq
```python
SCHEDULER_QUEUE_CLASS = 'aioscrapy.queue.rabbitmq.SpiderPriorityQueue'
# RabbitMq parameter
RABBITMQ_ARGS = {
    'queue': {
        'url': "amqp://guest:guest@192.168.234.128:5673/",
        'connection_max_size': 2,
        'channel_max_size': 10,
    }
}
```

### Dupefilters
`DUPEFILTER_CLASS`: filter duplicate urls, No default configuration.

##### disk
Save URL fingerprint information to disk.
```python
DUPEFILTER_CLASS = 'aioscrapy.dupefilters.disk.RFPDupeFilter'
```
##### redis with hash
Save URL fingerprint information to redis, Hash the URL.
```python
DUPEFILTER_CLASS = 'aioscrapy.dupefilters.redis.RFPDupeFilter'
```
##### redis with Bloom filter
Save URL fingerprint information to redis, use Bloom filter.

```python
DUPEFILTER_CLASS = 'aioscrapy.dupefilters.redis.BloomDupeFilter'
```

### Close Sipder
`CLOSE_SPIDER_ON_IDLE`: Whether to close crawler when queue has no work, Default `False`.

### Scrapyd
How to deploy distributed crawler of aio-scrapy with scrapyd

Install scrapyd
```shell
pip install scrapyd
```
Modify scrapyd configuration

default_scrapyd.conf
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
bind_address = 127.0.0.1
http_port   = 6800
debug       = off
# runner      = scrapyd.runner    # The original configuration
runner      = aioscrapy.scrapyd.runner  # Replace runner with aio-scrapy runner
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
Start scrapyd
```shell
scrapyd &
```
Please refer to scrapyd's documentation for more details.

### Other

##### CsvPipeline
Csv Bulk Storage Middleware

```python
ITEM_PIPELINES = {
    'aioscrapy.libs.pipelines.csv.CsvPipeline': 100,
}
"""
# Format requirements for item
item = {
    '__csv__': {
        'filename': 'article',  # 文件名 或 存储的路径及文件名 如：D:\article.xlsx
    },

    # Below are the item fields
    'title': "title",
}
"""
```

##### ExcelPipeline
Execl Bulk Storage Middleware

```python
ITEM_PIPELINES = {
    'aioscrapy.libs.pipelines.execl.ExcelPipeline': 100,
}

"""
# Format requirements for item
item = {
    '__excel__': {
        'filename': 'article',  # File name to store, eg：D:\article.xlsx
        'sheet': 'sheet1',  # sheet name,  default: sheet1

        # 'img_fields': ['img'],    # Specify the image fields when you want to download
        # 'img_size': (100, 100)    # the size of image
    },

    # Below are the item fields
    'title': "title",
    'img': "https://domain/test.png",
}
"""
```

##### MysqlPipeline
Mysql Bulk Storage Middleware
```python
ITEM_PIPELINES = {
    'aioscrapy.libs.pipelines.mysql.MysqlPipeline': 100,
}

# mysql parameter
MYSQL_ARGS = {
    # "default" is alias of the mysql pool
    # Use:
    #       from aioscrapy.db import db_manager
    #       async with db_manager.get('default') as (conn, cur):
    #             print(await cur.execute('select 1'))
    'default': {
        'db': 'test',
        'user': 'root',
        'password': '123456',
        'host': '192.168.234.128',
        'port': 3306,
        'charset': 'utf8mb4',
    },

    # # "dev" is alias of the mysql pool
    # 'dev': {
    #     'db': 'test2',
    #     'user': 'root',
    #     'password': 'root',
    #     'host': '127.0.0.1',
    #     'port': 3306,
    #     'charset': 'utf8mb4',
    # }
}
SAVE_CACHE_NUM = 1000   # Trigger mysql storage every 1000 item.
SAVE_CACHE_INTERVAL = 10    # Trigger mysql storage every 10 seconds.
"""
# Format requirements for item
item = {
    '__mysql__': {
        'table_name': 'baidu',  # table name of mysql
        'insert_type': 'insert',   # Save type for mysql
        'db_alias': ['default'],     # Alias of mysql to save
    },
    
    # Below are the item fields
    'title': "title",
}
"""

```

##### MongoPipeline

Mongo Bulk Storage Middleware

```python
ITEM_PIPELINES = {
    'aioscrapy.libs.pipelines.mongo.MongoPipeline': 100,
}

MONGO_ARGS = {
    'default': {
        'host': 'mongodb://root:root@192.168.234.128:27017',
        'db': 'test',
    }
}
SAVE_CACHE_NUM = 1000   # Trigger mysql storage every 1000 item.
SAVE_CACHE_INTERVAL = 10    # Trigger mysql storage every 10 seconds.
"""
# Format requirements for item
item = {
    '__mongo__': {
        'db_alias': 'default',     # Alias of mongo to save
        'table_name': 'article',   # table name of mongo
        # 'db_name': 'xxx',     # db name of mongo， If not specified, the default value is "MONGO_ARGS" in "db"
      
    },
    # Below are the item fields
    'title': "title",
}
"""
```


##### PGPipeline
PostpreSQL批量存储中间件

```python
ITEM_PIPELINES = {
    'aioscrapy.libs.pipelines.pg.PGPipeline': 100,
}
PG_ARGS = {
    'default': {
        'user': 'user',
        'password': 'password',
        'database': 'spider_db',
        'host': '127.0.0.1'
    }
}
SAVE_CACHE_NUM = 1000  # 每1000个item触发一次存储
SAVE_CACHE_INTERVAL = 10  # 每10s触发一次存储
"""
# Format requirements for item
item = {
    '__pg__': {
        'db_alias': 'default',  # # Alias of PostgreSQL to save
        'table_name': 'spider_db.article',  # schema and table_name, Separate with "."

        'insert_type': 'insert', # Save type for PostgreSQL
        # 'on_conflict': 'id',  
    }

    # Below are the item fields
    'title': "title",
}
"""
```