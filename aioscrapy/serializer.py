import ujson
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
        return ujson.loads(s)

    @staticmethod
    def dumps(obj):
        return ujson.dumps(obj)

