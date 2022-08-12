"""
Helper functions for serializing (and deserializing) requests.
"""
from typing import Optional

import aioscrapy
from aioscrapy.utils.request import request_from_dict as _from_dict


def request_to_dict(request: "aioscrapy.Request", spider: Optional["aioscrapy.Spider"] = None) -> dict:
    return request.to_dict(spider=spider)


def request_from_dict(d: dict, spider: Optional["aioscrapy.Spider"] = None) -> "aioscrapy.Request":
    return _from_dict(d, spider=spider)
