# 启用随机ciphers过ja3反爬
# RANDOM_TLS_CIPHERS = True

# redis参数配置
REDIS_ARGS = {
    # "default"为该链接池别名 (只从该redis获取任务队列)
    'default': {
        'url': 'redis://192.168.234.128:6379/1',
        'max_connections': 2,
    },

    # "redis2"为该链接池别名
    # 'redis2': {
    #     'url': 'redis://:password@192.168.234.128:6379/2',
    #     'max_connections': 2,
    # }
}

# mysql参数配置 (支持一个item写入多个数据库)
MYSQL_ARGS = {
    # "default"为该链接池别名
    'default': {
        'db': 'test',
        'user': 'root',
        'password': '123456',
        'host': '192.168.234.128',
        'port': 3306,
        'charset': 'utf8mb4',
    },

    # # "mysql2"为该链接池别名
    # 'mysql2': {
    #     'db': 'test2',
    #     'user': 'root',
    #     'password': 'root',
    #     'host': '127.0.0.1',
    #     'port': 3306,
    #     'charset': 'utf8mb4',
    # }
}
# 存储item中间件
ITEM_PIPELINES = {
    'aioscrapy.pipelines.db.MysqlPipeline': 100,
}
SAVE_CACHE_NUM = 500        # 每500个item触发一次数据库写入， 将所有缓存的数据写入
SAVE_CACHE_INTERVAL = 10    # 每10秒触发一次数据库写入， 将所有缓存的数据写入

# ================================================================================================
# 下面按照scrapy/scrapy-redis的方式配置参数即可
# 下面按照scrapy/scrapy-redis的方式配置参数即可
# 下面按照scrapy/scrapy-redis的方式配置参数即可
# ================================================================================================

BOT_NAME = 'demo1'

SPIDER_MODULES = ['demo1.spiders']
NEWSPIDER_MODULE = 'demo1.spiders'

DOWNLOAD_DELAY = 3
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS = 1
