import asyncio

from aioscrapy import Request
from aioscrapy.db import db_manager


async def push_redis_task():
    from aioscrapy.queue.redis import SpiderPriorityQueue

    try:
        await db_manager.from_dict({
            'redis': {
                'queue': {
                    'url': 'redis://192.168.234.128:6379/0',
                    'max_connections': 2,
                }
            }
        })
        q = SpiderPriorityQueue.from_dict({
            'alias': 'queue',
            'spider_name': 'DemoRedisSpider',
            'serializer': 'aioscrapy.serializer.JsonSerializer'
        })
        for page in range(1, 10):
            r = Request(
                f'https://quotes.toscrape.com/page/{page}/',
                priority=page
            )
            await q.push(r)
    finally:
        await db_manager.close_all()


async def push_rabbitmq_task():
    from aioscrapy.queue.rabbitmq import SpiderPriorityQueue

    try:
        await db_manager.from_dict({
            'rabbitmq': {
                'queue': {
                    'url': "amqp://guest:guest@192.168.234.128:5673",
                    'connection_max_size': 2,
                    'channel_max_size': 10,
                }
            }
        })
        q = SpiderPriorityQueue.from_dict({
            'alias': 'queue',
            'spider_name': 'DemoRabbitmqSpider',
            'serializer': 'aioscrapy.serializer.JsonSerializer'
        })
        for page in range(1, 10):
            r = Request(
                f'https://quotes.toscrape.com/page/{page}/',
                priority=page
            )
            await q.push(r)
    finally:
        await db_manager.close_all()


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(push_redis_task())
    # asyncio.get_event_loop().run_until_complete(push_rabbitmq_task())
