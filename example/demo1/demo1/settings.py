

# 启用随机ciphers过ja3反爬
# RANDOM_TLS_CIPHERS = True

# redis参数配置
REDIS_ARGS = {
    'alias': 'xxx',  # 为改链接池取个别名(非必要参数, 参考模块aioscrapy/connection/_aioredis.py)
    'url': 'redis://:passworld@127.0.0.1:6379/1',
    'max_connections': 2,   # redis连接池数量限制
}

# # mysql参数配置
# MYSQL_ARGS = {
#     'alias': 'xxx',  # 为改链接池取个别名(非必要参数, 参考模块aioscrapy/connection/_aiomysql.py)
#     'db': 'test',
#     'user': 'root',
#     'password': 'root',
#     'host': '127.0.0.1',
#     'port': 3306,
#     'charset': 'utf8mb4',
# }


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
