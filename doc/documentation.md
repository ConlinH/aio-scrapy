
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

##### MysqlPipeline
Mysql Bulk Storage Middleware
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
SAVE_CACHE_NUM = 1000   # Trigger mysql storage every 1000 item.
SAVE_CACHE_INTERVAL = 10    # Trigger mysql storage every 10 seconds.
"""
# Format requirements for item
item = {
            'save_table_name': 'baidu',  # table name of mysql
            'save_insert_type': 'insert',   # Save type for mysql
            'save_db_alias': ['default'],     # Alias of mysql to save

            # Below are the item fields
            'title': "title",
        }
"""

```
