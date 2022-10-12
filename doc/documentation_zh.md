
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
`CLOSE_SPIDER_ON_IDLE`: 当没有队列任务的时候是否关闭爬虫, 默认 `True`.


### Scrapyd
如可使用scrapyd部署aio-scrapy的分布式爬虫

安装scrapyd
```shell
pip install scrapyd
```
修改scrapyd配置如下
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
# runner      = scrapyd.runner    # 原配置
runner      = aioscrapy.scrapyd.runner  # 将runner替换为aio-scrapy提供的runner
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
启动scrapyd
```shell
scrapyd &
```
更多具体操作请参考scrapyd的文档

### 其它

##### MysqlPipeline
Mysql批量存储中间件
```python
ITEM_PIPELINES = {
    'aioscrapy.libs.pipelines.db.MysqlPipeline': 100,
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
SAVE_CACHE_NUM = 1000   # 每1000个item触发一次存储
SAVE_CACHE_INTERVAL = 10    # 每10s触发一次存储
"""
# item的格式要求如下
item = {
            'save_table_name': 'baidu',  # 要存储的表名字
            'save_insert_type': 'insert',   # 存储的方式
            'save_db_alias': ['default'],     # 要存储的mysql的库, mysql的alias

            # 下面为存储的字段
            'title': "title",
        }
"""
```
