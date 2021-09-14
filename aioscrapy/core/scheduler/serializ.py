import pickle
import json

__all__ = ['PickleCompat', 'JsonCompat']


def _request_body_byte2str(obj):
    obj['body'] = obj['body'].decode(obj['_encoding'])
    return obj


def _request_body_str2byte(obj):
    obj['body'] = obj['body'].encode(obj['_encoding'])
    return obj


class PickleCompat:
    @staticmethod
    def loads(s):
        return pickle.loads(s)

    @staticmethod
    def dumps(obj):
        return pickle.dumps(obj, protocol=-1)


class JsonCompat:
    @staticmethod
    def loads(s):
        return _request_body_str2byte(json.loads(s))

    @staticmethod
    def dumps(obj):
        print(obj)
        return json.dumps(_request_body_byte2str(obj))
