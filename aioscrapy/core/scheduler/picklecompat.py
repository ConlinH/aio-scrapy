import pickle
import json


class PickleCompat:
    @staticmethod
    def loads(s):
        return pickle.loads(s)

    @staticmethod
    def dumps(obj):
        return pickle.dumps(obj, protocol=-1)


class JsonPickleCompat(PickleCompat):
    @staticmethod
    def loads(s):
        try:
            return pickle.loads(s)
        except pickle.UnpicklingError:
            j = json.loads(s)
            return j
