[英文](./documentation.md)| 中文

### 调度的队列

`SCHEDULER_QUEUE_CLASS`：获取请求任务的队列类型，默认为`memory`

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

### 过滤重复请求

`DUPEFILTER_CLASS`：配置url的去重类， 默认不配

##### disk

将url指纹信息存放在磁盘

```python
DUPEFILTER_CLASS = 'aioscrapy.dupefilters.disk.RFPDupeFilter'
```

##### redis with hash

将url指纹信息放到redis， 对url进行hash

```python
DUPEFILTER_CLASS = 'aioscrapy.dupefilters.redis.RFPDupeFilter'
```

##### redis with Bloom filter

将url指纹信息放到redis，使用布隆过滤

```python
DUPEFILTER_CLASS = 'aioscrapy.dupefilters.redis.BloomDupeFilter'
```

### 关闭爬虫

`CLOSE_SPIDER_ON_IDLE`: 当没有队列任务的时候是否关闭爬虫, 默认 `False`.

### Scrapyd

如可使用scrapyd部署aio-scrapy的分布式爬虫

安装scrapyd

```shell
pip install scrapyd
```

修改scrapyd配置如下 default_scrapyd.conf

```ini
[scrapyd]
eggs_dir = eggs
logs_dir = logs
items_dir =
jobs_to_keep = 5
dbs_dir = dbs
max_proc = 0
max_proc_per_cpu = 4
finished_to_keep = 100
poll_interval = 5.0
bind_address = 127.0.0.1
http_port = 6800
debug = off
# runner      = scrapyd.runner    # 原配置
runner = aioscrapy.scrapyd.runner  # 将runner替换为aio-scrapy提供的runner
application = scrapyd.app.application
launcher = scrapyd.launcher.Launcher
webroot = scrapyd.website.Root

[services]
schedule.json = scrapyd.webservice.Schedule
cancel.json = scrapyd.webservice.Cancel
addversion.json = scrapyd.webservice.AddVersion
listprojects.json = scrapyd.webservice.ListProjects
listversions.json = scrapyd.webservice.ListVersions
listspiders.json = scrapyd.webservice.ListSpiders
delproject.json = scrapyd.webservice.DeleteProject
delversion.json = scrapyd.webservice.DeleteVersion
listjobs.json = scrapyd.webservice.ListJobs
daemonstatus.json = scrapyd.webservice.DaemonStatus

```

启动scrapyd

```shell
scrapyd &
```

更多具体操作请参考scrapyd的文档

### 其它

##### CsvPipeline
csv存储中间件

```python
ITEM_PIPELINES = {
    'aioscrapy.libs.pipelines.csv.CsvPipeline': 100,
}
"""
# item的格式要求如下
item = {
    '__csv__': {
        'filename': 'article',  # 文件名 或 存储的路径及文件名 如：D:\article.xlsx
    },

    # 下面为存储的字段
    'title': "title",
}
"""
```

##### ExcelPipeline
execl存储中间件

```python
ITEM_PIPELINES = {
    'aioscrapy.libs.pipelines.execl.ExcelPipeline': 100,
}

"""
# item的格式要求如下
item = {
    '__execl__': {
        'filename': 'article',  # 文件名 或 存储的路径及文件名 如：D:\article.xlsx
        'sheet': 'sheet1',  # 表格的sheet名字 不指定默认为sheet1

        # 'img_fields': ['img'],    # 图片字段 当指定图片字段时 自行下载图片 并保存到表格里
        # 'img_size': (100, 100)    # 指定图片大小时 自动将图片转换为指定大小
    },

    # 下面为存储的字段
    'title': "title",
    'img': "https://domain/test.png",
}
"""
```

##### MysqlPipeline

Mysql批量存储中间件

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
SAVE_CACHE_NUM = 1000  # 每1000个item触发一次存储
SAVE_CACHE_INTERVAL = 10  # 每10s触发一次存储
"""
# item的格式要求如下
item = {
    '__mysql__': {
        'db_alias': 'default',      # 要存储的mysql, 参数“MYSQL_ARGS”的key
        'table_name': 'article',  # 要存储的表名字

        # 写入数据库的方式： 默认insert方式
        # insert：普通写入 出现主键或唯一键冲突时抛出异常
        # update_insert：更新插入 出现主键或唯一键冲突时，更新写入
        # ignore_insert：忽略写入 写入时出现冲突 丢掉该条数据 不抛出异常
        'insert_type': 'update_insert',
    }

    # 下面为存储的字段
    'title': "title",
}
"""
```

##### MongoPipeline

Mongo批量存储中间件

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
SAVE_CACHE_NUM = 1000  # 每1000个item触发一次存储
SAVE_CACHE_INTERVAL = 10  # 每10s触发一次存储
"""
# item的格式要求如下
item = {
    '__mongo__': {
        'db_alias': 'default',  # 要存储的mongo, 参数“MONGO_ARGS”的key
        'table_name': 'article',  # 要存储的表名字
        # 'db_name': 'xxx',     # 要存储的mongo的库名， 不指定则默认为“MONGO_ARGS”中的“db”值
    }

    # 下面为存储的字段
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
# item的格式要求如下
item = {
    '__pg__': {
        'db_alias': 'default',  # 要存储的PostgreSQL, 参数“PG_ARGS”的key
        'table_name': 'spider_db.article',  # 要存储的schema和表名字，用.隔开

        # 写入数据库的方式：
        # insert：普通写入 出现主键或唯一键冲突时抛出异常
        # update_insert：更新插入 出现on_conflict指定的冲突时，更新写入
        # ignore_insert：忽略写入 写入时出现冲突 丢掉该条数据 不抛出异常
        'insert_type': 'update_insert',
        'on_conflict': 'id',     # update_insert方式下的约束
    }

    # 下面为存储的字段
    'title': "title",
}
"""
```
