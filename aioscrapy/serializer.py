import json
import pickle
from abc import ABCMeta, abstractmethod

__all__ = ['PickleSerializer', 'JsonSerializer', 'AbsSerializer']


class AbsSerializer(object, metaclass=ABCMeta):

    @staticmethod
    @abstractmethod
    def loads(s):
        """Serializer object"""

    @staticmethod
    @abstractmethod
    def dumps(obj):
        """Serializer object"""


class PickleSerializer(AbsSerializer):
    @staticmethod
    def loads(s):
        return pickle.loads(s)

    @staticmethod
    def dumps(obj):
        return pickle.dumps(obj, protocol=-1)


class JsonSerializer(AbsSerializer):
    @staticmethod
    def loads(s):
        return json.loads(s)

    @staticmethod
    def dumps(obj):
        return json.dumps(_request_byte2str(obj))


def _request_byte2str(obj):
    _encoding = obj.get('_encoding', 'utf-8')
    obj.update({
        'body': obj['body'].decode(_encoding),
        # 'headers': {
        #     to_unicode(k, encoding=_encoding): to_unicode(b','.join(v), encoding=_encoding)
        #     for k, v in obj['headers'].items()
        # }
    })
    return obj
