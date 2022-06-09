
# SCHEDULER_QUEUE_CLASS = 'aioscrapy.queue.redis.SpiderPriorityQueue'
# SCHEDULER_QUEUE_CLASS = 'aioscrapy.queue.rabbitmq.SpiderPriorityQueue'

# DUPEFILTER_CLASS = 'aioscrapy.dupefilters.disk.RFPDupeFilter'
# DUPEFILTER_CLASS = 'aioscrapy.dupefilters.redis.RFPDupeFilter'
# DUPEFILTER_CLASS = 'aioscrapy.dupefilters.redis.BloomDupeFilter'

# SCHEDULER_SERIALIZER = 'aioscrapy.serializer.JsonSerializer'
# SCHEDULER_SERIALIZER = 'aioscrapy.serializer.PickleSerializer'

# ITEM_PIPELINES = {
#     'aioscrapy.libs.pipelines.sink.MysqlPipeline': 100,
# }

BOT_NAME = 'redisdemo'

SPIDER_MODULES = ['redisdemo.spiders']
NEWSPIDER_MODULE = 'redisdemo.spiders'

DOWNLOAD_DELAY = 3
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS = 1

# SCHEDULER_FLUSH_ON_START = True

RABBITMQ_ARGS = {
    'queue': {
        'url': "amqp://guest:guest@192.168.234.128:5673/",
        'connection_max_size': 2,
        'channel_max_size': 10,
    }
}

# redis parameter
REDIS_ARGS = {
    # "queue" is alias of the redis pool, Put the Request inside
    # Use:
    #       from aioscrapy.db import db_manager
    #       await db_manager.redis.queue.set('test', 1)
    'queue': {
        'url': 'redis://192.168.234.128:6379/1',
        'max_connections': 2,
        'timeout': None,
        'retry_on_timeout': True,
        'health_check_interval': 30,
    },

    # "proxy" is alias of the redis pool
    # 'proxy': {
    #     'url': 'redis://username:password@192.168.234.128:6379/2',
    #     'max_connections': 2,
    #     'timeout': None,
    #     'retry_on_timeout': True,
    #     'health_check_interval': 30,
    # }
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

    # # "mysql2" is alias of the mysql pool
    # 'mysql2': {
    #     'db': 'test2',
    #     'user': 'root',
    #     'password': 'root',
    #     'host': '127.0.0.1',
    #     'port': 3306,
    #     'charset': 'utf8mb4',
    # }
}

# LOG_FILE = 'test.log'
