from aioscrapy.queue.redis import ACK_SCRIPT, LEN_SCRIPT, NACK_SCRIPT, PUSH_SCRIPT, RESERVE_SCRIPT


class FakeReliableRedis:
    """Protocol-level fake for the reliable queue Lua scripts."""

    def __init__(self, now=1000.0):
        self.now = now
        self.ready = {}
        self.ready_list = []
        self.processing = {}
        self.payload = {}
        self.calls = []

    async def eval(self, script, numkeys, *params):
        keys = params[:numkeys]
        args = list(params[numkeys:])
        self.calls.append((script, keys, args))
        if script == PUSH_SCRIPT:
            return self._push(args)
        if script == RESERVE_SCRIPT:
            return self._reserve(args)
        if script == ACK_SCRIPT:
            return self._ack(args)
        if script == NACK_SCRIPT:
            return self._nack(args)
        if script == LEN_SCRIPT:
            self.mode = args[0]
            return self._ready_count() + len(self.processing)
        raise AssertionError('unexpected script')

    async def delete(self, *keys):
        self.ready.clear()
        self.ready_list.clear()
        self.processing.clear()
        self.payload.clear()

    def advance(self, seconds):
        self.now += seconds

    def _push(self, args):
        mode, count = args[0], int(args[1])
        self.mode = mode
        for index in range(count):
            offset = 2 + index * 4
            task_id, member, payload, score = args[offset:offset + 4]
            assert task_id not in self.payload
            self.payload[task_id] = payload
            self._put_ready(member, float(score), new=True)
        return count

    def _reserve(self, args):
        mode, count, timeout, recovery_limit = args[:4]
        self.mode = mode
        count = int(count)
        tokens = args[4:]
        recovered = 0
        for receipt, deadline in sorted(list(self.processing.items()), key=lambda item: item[1]):
            if recovered >= int(recovery_limit) or deadline > self.now:
                continue
            del self.processing[receipt]
            task_id, _token, score, _flag = receipt.split('|')
            if task_id in self.payload:
                self._put_ready(task_id + '|1', float(score), new=False)
                recovered += 1

        deliveries = []
        for index in range(count):
            popped = self._pop_ready()
            if popped is None:
                break
            member, score = popped
            task_id, redelivered = member.split('|')
            payload = self.payload.get(task_id)
            if payload is None:
                continue
            receipt = f'{task_id}|{tokens[index]}|{score:g}|{redelivered}'
            self.processing[receipt] = self.now + float(timeout)
            deliveries.extend((task_id, receipt, int(redelivered), payload))
        return [self._ready_count(), len(self.processing), recovered, *deliveries]

    def _ack(self, args):
        count = int(args[0])
        result = []
        for index in range(count):
            task_id, receipt = args[1 + index * 2:3 + index * 2]
            if receipt in self.processing:
                del self.processing[receipt]
                self.payload.pop(task_id, None)
                result.append(1)
            else:
                result.append(0)
        return result

    def _nack(self, args):
        self.mode, count = args[0], int(args[1])
        result = []
        for receipt in args[2:2 + count]:
            if receipt not in self.processing:
                result.append(0)
                continue
            del self.processing[receipt]
            task_id, _token, score, _flag = receipt.split('|')
            if task_id in self.payload:
                self._put_ready(task_id + '|1', float(score), new=False)
            result.append(1)
        return result

    def _put_ready(self, member, score, *, new):
        if self.mode == 'priority':
            self.ready[member] = score
        elif new or self.mode == 'lifo':
            self.ready_list.insert(0, member)
        else:
            self.ready_list.append(member)

    def _pop_ready(self):
        if self.mode == 'priority':
            if not self.ready:
                return None
            member = min(self.ready, key=lambda value: (self.ready[value], value))
            return member, self.ready.pop(member)
        if not self.ready_list:
            return None
        member = self.ready_list.pop() if self.mode == 'fifo' else self.ready_list.pop(0)
        return member, 0.0

    def _ready_count(self):
        return len(self.ready) if self.mode == 'priority' else len(self.ready_list)
