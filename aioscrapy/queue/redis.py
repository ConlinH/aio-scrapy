from abc import ABC
from typing import List, Sequence
from uuid import uuid4

import aioscrapy

from aioscrapy.db import db_manager
from aioscrapy.queue import AbsQueue, QueueDelivery
from aioscrapy.serializer import AbsSerializer
from aioscrapy.utils.misc import load_object


PUSH_SCRIPT = r"""
local mode = ARGV[1]
local count = tonumber(ARGV[2])

for i = 0, count - 1 do
    local offset = 3 + i * 4
    if redis.call('HEXISTS', KEYS[2], ARGV[offset]) == 1 then
        return redis.error_reply('duplicate task id')
    end
end

for i = 0, count - 1 do
    local offset = 3 + i * 4
    local task_id = ARGV[offset]
    local ready_member = ARGV[offset + 1]
    local payload = ARGV[offset + 2]
    local score = tonumber(ARGV[offset + 3])
    redis.call('HSET', KEYS[2], task_id, payload)
    if mode == 'priority' then
        redis.call('ZADD', KEYS[1], score, ready_member)
    else
        redis.call('LPUSH', KEYS[1], ready_member)
    end
end

return count
"""


RESERVE_SCRIPT = r"""
local mode = ARGV[1]
local count = tonumber(ARGV[2])
local visibility_timeout = tonumber(ARGV[3])
local recovery_limit = tonumber(ARGV[4])
local time = redis.call('TIME')
local now = tonumber(time[1]) + tonumber(time[2]) / 1000000
local deadline = now + visibility_timeout

local function parse_ready(member)
    return string.match(member, '^([^|]+)|([01])$')
end

local function parse_receipt(receipt)
    return string.match(receipt, '^([^|]+)|([^|]+)|([^|]+)|([01])$')
end

local function requeue(task_id, score)
    local member = task_id .. '|1'
    if mode == 'priority' then
        redis.call('ZADD', KEYS[1], tonumber(score), member)
    elseif mode == 'fifo' then
        redis.call('RPUSH', KEYS[1], member)
    else
        redis.call('LPUSH', KEYS[1], member)
    end
end

local expired = redis.call(
    'ZRANGEBYSCORE', KEYS[2], '-inf', now, 'LIMIT', 0, recovery_limit
)
local recovered = 0
for _, receipt in ipairs(expired) do
    local task_id, token, score = parse_receipt(receipt)
    if task_id and redis.call('ZREM', KEYS[2], receipt) == 1 then
        if redis.call('HEXISTS', KEYS[3], task_id) == 1 then
            requeue(task_id, score)
            recovered = recovered + 1
        end
    end
end

local result = {}
local claimed = 0
while claimed < count do
    local member = nil
    local score = 0
    if mode == 'priority' then
        local values = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
        if #values == 0 then break end
        member = values[1]
        score = tonumber(values[2])
        redis.call('ZREM', KEYS[1], member)
    elseif mode == 'fifo' then
        member = redis.call('RPOP', KEYS[1])
        if not member then break end
    else
        member = redis.call('LPOP', KEYS[1])
        if not member then break end
    end

    local task_id, redelivered = parse_ready(member)
    local payload = task_id and redis.call('HGET', KEYS[3], task_id) or nil
    if payload then
        local token = ARGV[5 + claimed]
        local receipt = task_id .. '|' .. token .. '|' .. tostring(score) .. '|' .. redelivered
        redis.call('ZADD', KEYS[2], deadline, receipt)
        table.insert(result, task_id)
        table.insert(result, receipt)
        table.insert(result, redelivered)
        table.insert(result, payload)
        claimed = claimed + 1
    end
end

local ready_count
if mode == 'priority' then
    ready_count = redis.call('ZCARD', KEYS[1])
else
    ready_count = redis.call('LLEN', KEYS[1])
end
local processing_count = redis.call('ZCARD', KEYS[2])

local response = {ready_count, processing_count, recovered}
for _, value in ipairs(result) do table.insert(response, value) end
return response
"""


ACK_SCRIPT = r"""
local count = tonumber(ARGV[1])
local result = {}
for i = 0, count - 1 do
    local task_id = ARGV[2 + i * 2]
    local receipt = ARGV[3 + i * 2]
    local removed = redis.call('ZREM', KEYS[1], receipt)
    if removed == 1 then
        redis.call('HDEL', KEYS[2], task_id)
    end
    table.insert(result, removed)
end
return result
"""


NACK_SCRIPT = r"""
local mode = ARGV[1]
local count = tonumber(ARGV[2])
local result = {}

local function parse_receipt(receipt)
    return string.match(receipt, '^([^|]+)|([^|]+)|([^|]+)|([01])$')
end

for i = 0, count - 1 do
    local receipt = ARGV[3 + i]
    local task_id, token, score = parse_receipt(receipt)
    local removed = 0
    if task_id then
        removed = redis.call('ZREM', KEYS[2], receipt)
        if removed == 1 and redis.call('HEXISTS', KEYS[3], task_id) == 1 then
            local member = task_id .. '|1'
            if mode == 'priority' then
                redis.call('ZADD', KEYS[1], tonumber(score), member)
            elseif mode == 'fifo' then
                redis.call('RPUSH', KEYS[1], member)
            else
                redis.call('LPUSH', KEYS[1], member)
            end
        end
    end
    table.insert(result, removed)
end
return result
"""


LEN_SCRIPT = r"""
local ready
if ARGV[1] == 'priority' then
    ready = redis.call('ZCARD', KEYS[1])
else
    ready = redis.call('LLEN', KEYS[1])
end
return ready + redis.call('ZCARD', KEYS[2])
"""


class RedisQueueBase(AbsQueue, ABC):
    inc_key = 'scheduler/enqueued/redis'
    queue_mode = 'fifo'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.key:
            self.key = 'requests'
        prefix = self.key if self._has_hash_tag(self.key) else '{%s}' % self.key
        self.ready_key = prefix + ':ready'
        self.processing_key = prefix + ':processing'
        self.payload_key = prefix + ':payload'
        self.last_ready_count = 0
        self.last_processing_count = 0

    @staticmethod
    def _has_hash_tag(key: str) -> bool:
        start = key.find('{')
        end = key.find('}', start + 1)
        return start >= 0 and end > start + 1

    @classmethod
    def from_dict(cls, data: dict) -> "RedisQueueBase":
        alias = data.get('alias', 'queue')
        server = db_manager.redis(alias)
        serializer = load_object(data.get('serializer', 'aioscrapy.serializer.JsonSerializer'))
        return cls(
            server,
            key=data.get('key', '%(spider)s:requests') % {'spider': data['spider_name']},
            serializer=serializer,
        )

    @classmethod
    async def from_spider(cls, spider: aioscrapy.Spider) -> "RedisQueueBase":
        alias = spider.settings.get('SCHEDULER_QUEUE_ALIAS', 'queue')
        server = db_manager.redis(alias)
        queue_key = spider.settings.get('SCHEDULER_QUEUE_KEY', '%(spider)s:requests')
        serializer: AbsSerializer = load_object(
            spider.settings.get('SCHEDULER_SERIALIZER', 'aioscrapy.serializer.JsonSerializer')
        )
        return cls(
            server,
            spider,
            queue_key % {'spider': spider.name},
            serializer=serializer,
        )

    async def _eval(self, script, keys, args):
        return await self.container.eval(script, len(keys), *keys, *args)

    async def len(self) -> int:
        return int(await self._eval(
            LEN_SCRIPT,
            [self.ready_key, self.processing_key],
            [self.queue_mode],
        ))

    async def push(self, request: aioscrapy.Request) -> None:
        await self.push_batch([request])

    async def push_batch(self, requests) -> None:
        if not requests:
            return
        args = [self.queue_mode, len(requests)]
        for request in requests:
            task_id = uuid4().hex
            args.extend((
                task_id,
                task_id + '|0',
                self._encode_request(request),
                -request.priority if self.queue_mode == 'priority' else 0,
            ))
        await self._eval(PUSH_SCRIPT, [self.ready_key, self.payload_key], args)

    async def reserve(self, count: int = 1, visibility_timeout: float = 600) -> List[QueueDelivery]:
        if count <= 0:
            return []
        tokens = [uuid4().hex for _ in range(count)]
        raw = await self._eval(
            RESERVE_SCRIPT,
            [self.ready_key, self.processing_key, self.payload_key],
            [self.queue_mode, count, visibility_timeout, max(100, count), *tokens],
        )
        self.last_ready_count = int(raw[0])
        self.last_processing_count = int(raw[1])
        deliveries = []
        for index in range(3, len(raw), 4):
            task_id = self._as_text(raw[index])
            receipt = self._as_text(raw[index + 1])
            redelivered = bool(int(raw[index + 2]))
            request = await self._decode_request(raw[index + 3])
            parts = receipt.split('|')
            deliveries.append(QueueDelivery(
                request=request,
                task_id=task_id,
                token=parts[1],
                receipt=receipt,
                redelivered=redelivered,
                score=float(parts[2]),
            ))
        return deliveries

    async def ack_batch(self, deliveries: Sequence[QueueDelivery]) -> List[bool]:
        if not deliveries:
            return []
        args = [len(deliveries)]
        for delivery in deliveries:
            args.extend((delivery.task_id, delivery.receipt))
        result = await self._eval(
            ACK_SCRIPT,
            [self.processing_key, self.payload_key],
            args,
        )
        return [bool(value) for value in result]

    async def nack_batch(self, deliveries: Sequence[QueueDelivery]) -> List[bool]:
        if not deliveries:
            return []
        result = await self._eval(
            NACK_SCRIPT,
            [self.ready_key, self.processing_key, self.payload_key],
            [self.queue_mode, len(deliveries), *(delivery.receipt for delivery in deliveries)],
        )
        return [bool(value) for value in result]

    async def clear(self) -> None:
        await self.container.delete(self.ready_key, self.processing_key, self.payload_key)

    @staticmethod
    def _as_text(value) -> str:
        return value.decode() if isinstance(value, bytes) else str(value)


class RedisFifoQueue(RedisQueueBase):
    """Reliable FIFO queue."""

    queue_mode = 'fifo'


class RedisPriorityQueue(RedisQueueBase):
    """Reliable priority queue."""

    queue_mode = 'priority'


class RedisLifoQueue(RedisQueueBase):
    """Reliable LIFO queue."""

    queue_mode = 'lifo'


SpiderQueue = RedisFifoQueue
SpiderStack = RedisLifoQueue
SpiderPriorityQueue = RedisPriorityQueue
