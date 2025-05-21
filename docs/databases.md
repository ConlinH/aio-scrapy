# 数据库连接 | Database Connections

AioScrapy提供了一个统一的数据库连接管理系统，支持多种数据库类型，包括Redis、MySQL、MongoDB、PostgreSQL和RabbitMQ。这个系统使得在爬虫中使用数据库变得简单高效。</br>
AioScrapy provides a unified database connection management system that supports multiple database types, including Redis, MySQL, MongoDB, PostgreSQL, and RabbitMQ. This system makes using databases in spiders simple and efficient.

## 数据库管理架构 | Database Management Architecture

AioScrapy的数据库管理系统基于以下组件：</br>
AioScrapy's database management system is based on the following components:

1. **DBManager**：中央数据库管理器，提供统一的接口来访问不同类型的数据库连接
2. **AbsDBPoolManager**：数据库连接池管理器的抽象基类，所有具体的连接池管理器都继承自这个类
3. **具体连接池管理器**：如AioRedisPoolManager、AioMysqlPoolManager等，负责管理特定类型数据库的连接池

</br>

1. **DBManager**: Central database manager, providing a unified interface to access different types of database connections
2. **AbsDBPoolManager**: Abstract base class for database connection pool managers, all concrete pool managers inherit from this class
3. **Concrete Pool Managers**: Such as AioRedisPoolManager, AioMysqlPoolManager, etc., responsible for managing connection pools for specific database types

## 支持的数据库 | Supported Databases

AioScrapy支持以下数据库类型：</br>
AioScrapy supports the following database types:

### Redis

基于redis.asyncio库的异步Redis客户端。</br>
Asynchronous Redis client based on the redis.asyncio library.

```python
# 在settings.py中设置 | Set in settings.py
REDIS_ARGS = {
    'queue': {
        'url': 'redis://localhost:6379/0',
        'max_connections': 10,
        'timeout': 30,
    },
    'proxy': {
        'url': 'redis://localhost:6379/1',
    }
}
```

### MySQL

基于aiomysql库的异步MySQL客户端。</br>
Asynchronous MySQL client based on the aiomysql library.

```python
# 在settings.py中设置 | Set in settings.py
MYSQL_ARGS = {
    'default': {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': 'password',
        'db': 'test1',
        'charset': 'utf8mb4',
    },
    'default2': {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': 'password',
        'db': 'test2',
        'charset': 'utf8mb4',
    },

}
```

### MongoDB

基于motor库的异步MongoDB客户端。</br>
Asynchronous MongoDB client based on the motor library.

```python
# 在settings.py中设置 | Set in settings.py
MONGO_ARGS = {
    'default': {
        'host': 'localhost',
        'port': 27017,
        'db': 'test1',
        'connecttimeoutms': 30,
    },
    'default2': {
        'host': 'localhost2',
        'port': 27017,
        'db': 'test1',
        'connecttimeoutms': 30,
    }
}
```

### PostgreSQL

基于asyncpg库的异步PostgreSQL客户端。</br>
Asynchronous PostgreSQL client based on the asyncpg library.

```python
# 在settings.py中设置 | Set in settings.py
PG_ARGS = {
    'default': {
        'user': 'postgres',
        'password': 'password',
        'database': 'test1',
        'host': 'localhost',
        'port': 5432,
    },
    'default2': {
        'user': 'postgres',
        'password': 'password',
        'database': 'test2',
        'host': 'localhost',
        'port': 5432,
    }
}
```

### RabbitMQ

基于aio_pika库的异步RabbitMQ客户端。</br>
Asynchronous RabbitMQ client based on the aio_pika library.

```python
# 在settings.py中设置 | Set in settings.py
RABBITMQ_ARGS = {
    'queue': {
        'url': 'amqp://guest:guest@localhost:5672/',
    },
    'queue2': {
        'url': 'amqp://guest:guest@localhost:5672/',
    }
}
```

## 使用数据库连接 | Using Database Connections

AioScrapy提供了多种方式来使用数据库连接：</br>
AioScrapy provides multiple ways to use database connections:

### 通过db_manager访问 | Accessing via db_manager

```python
from aioscrapy.db import db_manager

# 获取Redis连接 | Get Redis connection
redis = db_manager.redis('proxy')
await redis.set('key', 'value')

# 获取MySQL连接 | Get MySQL connection
async with db_manager.mysql.get('default') as (conn, cur):
    await cur.execute('SELECT * FROM users')
    results = await cur.fetchall()

# 获取MongoDB连接 | Get MongoDB connection
mongo = db_manager.mongo('default')
users = mongo.users  # 访问users集合 | Access the users collection
await users.insert_one({'name': 'John', 'age': 30})

# 获取PostgreSQL连接 | Get PostgreSQL connection
async with db_manager.pg.get('default') as conn:
    results = await conn.fetch('SELECT * FROM users')

# 获取RabbitMQ连接 | Get RabbitMQ connection
rabbitmq = db_manager.rabbitmq('default')
await rabbitmq.channel.default_exchange.publish(
    aio_pika.Message(body='Hello World!'.encode()),
    routing_key='hello'
)
```

### 在爬虫中使用 | Using in Spiders

```python
from aioscrapy import Spider

class DatabaseSpider(Spider):
    name = 'database_spider'
    start_urls = ['https://example.com']
    
    custom_settings = {
        'SCHEDULER_QUEUE_ALIAS': 'default',
        'REDIS_ARGS': {
            'default': {
                'url': 'redis://localhost:6379/0',
            }
        },
        'MYSQL_ARGS': {
            'default': {
                'host': 'localhost',
                'port': 3306,
                'user': 'root',
                'password': 'password',
                'db': 'mydatabase',
                'charset': 'utf8mb4',
            }
        }
    }
    
    # 使用Redis | Using Redis
    async def parse(self, response):
        from aioscrapy.db import db_manager
        redis = db_manager.redis('default')
        await redis.set('last_url', response.url)
        
        # 使用MySQL | Using MySQL
        async with db_manager.mysql.get('default') as (conn, cur):
            await cur.execute(
                'INSERT INTO pages (url, title) VALUES (%s, %s)',
                (response.url, response.css('title::text').get())
            )
        
        yield {'url': response.url, 'title': response.css('title::text').get()}
```


## 自定义连接池管理器 | Custom Connection Pool Managers

您可以创建自己的连接池管理器，只需继承`AbsDBPoolManager`类并实现必要的方法：</br>
You can create your own connection pool manager by inheriting from the `AbsDBPoolManager` class and implementing the necessary methods:

```python
from aioscrapy.db.absmanager import AbsDBPoolManager
import aioscrapy

class MyCustomPoolManager(AbsDBPoolManager):
    _clients = {}
    
    # 创建连接池 | Create connection pool
    async def create(self, alias, params):
        if alias in self._clients:
            return self._clients[alias]
        
        # 创建自定义连接池 | Create custom connection pool
        pool = CustomConnectionPool(**params)
        return self._clients.setdefault(alias, pool)
    
    # 获取连接池 | Get connection pool
    def get_pool(self, alias='default'):
        if alias not in self._clients:
            raise KeyError(f"No connection pool with alias '{alias}'")
        return self._clients[alias]
    
    # 关闭所有连接池 | Close all connection pools
    async def close_all(self):
        for pool in self._clients.values():
            await pool.close()
        self._clients.clear()
    
    # 从字典创建连接池 | Create connection pools from dictionary
    async def from_dict(self, db_args):
        for alias, args in db_args.items():
            await self.create(alias, args)
    
    # 从设置创建连接池 | Create connection pools from settings
    async def from_settings(self, settings):
        for alias, args in settings.getdict('MY_CUSTOM_ARGS').items():
            await self.create(alias, args)
```

然后在项目中注册您的连接池管理器：
Then register your connection pool manager in your project:

```python
# 在项目初始化时 | During project initialization
from aioscrapy.db import db_manager_map
from myproject.db import MyCustomPoolManager

# 注册自定义连接池管理器 | Register custom connection pool manager
db_manager_map['custom'] = MyCustomPoolManager()
```
