"""Helper functions for working with signals"""
import asyncio
import logging

from pydispatch.dispatcher import Anonymous, Any, disconnect, getAllReceivers, liveReceivers
from pydispatch.robustapply import robustApply
from scrapy.exceptions import StopDownload

logger = logging.getLogger(__name__)


class _IgnoredException(Exception):
    pass


def send_catch_log(signal=Any, sender=Anonymous, *arguments, **named):
    """Like pydispatcher.robust.sendRobust but it also logs errors and returns
    Failures instead of exceptions.
    """
    dont_log = (named.pop('dont_log', _IgnoredException), StopDownload)
    spider = named.get('spider', None)
    responses = []
    for receiver in liveReceivers(getAllReceivers(sender, signal)):
        try:
            response = robustApply(receiver, signal=signal, sender=sender, *arguments, **named)
        except dont_log as exc:
            result = exc
        except Exception as exc:
            result = exc
            logger.error("Error caught on signal handler: %(receiver)s",
                         {'receiver': receiver},
                         exc_info=True, extra={'spider': spider})
        else:
            result = response
        responses.append((receiver, result))
    return responses


async def robustApplyWrap(f, recv, *args, **kw):
    dont_log = kw.pop('dont_log', None)
    spider = kw.get('spider', None)
    try:
        result = f(recv, *args, **kw)
        if asyncio.iscoroutine(result):
            await result
    except (Exception, BaseException) as exc:  # noqa: E722
        if dont_log is None or not isinstance(exc, dont_log):
            logger.error("Error caught on signal handler: %(receiver)s",
                         {'receiver': recv},
                         exc_info=exc,
                         extra={'spider': spider})


async def send_catch_log_deferred(signal=Any, sender=Anonymous, *arguments, **named):
    """Like send_catch_log but supports returning deferreds on signal handlers.
    Returns a deferred that gets fired once all signal handlers deferreds were
    fired.
    """
    dfds = []
    for receiver in liveReceivers(getAllReceivers(sender, signal)):
        dfds.append(asyncio.create_task(
            robustApplyWrap(robustApply, receiver, signal=signal, sender=sender, *arguments, **named)))
    res = await asyncio.gather(*dfds)
    return res


def disconnect_all(signal=Any, sender=Any):
    """Disconnect all signal handlers. Useful for cleaning up after running
    tests
    """
    for receiver in liveReceivers(getAllReceivers(sender, signal)):
        disconnect(receiver, signal=signal, sender=sender)

