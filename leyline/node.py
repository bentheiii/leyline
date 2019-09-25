from functools import update_wrapper
from weakref import WeakKeyDictionary


class PartialBoundNode:
    def __init__(self, bound_func, args, kwargs):
        self.bound_func = bound_func
        self.args = args
        self.kwargs = kwargs

    def __call__(self, *args, **kwargs):
        return self.bound_func(*self.args, *args, **self.kwargs, **kwargs)


class BoundNode:
    def __init__(self, bound_func):
        self.bound_func = bound_func
        update_wrapper(self, bound_func)

    def __call__(self, *args, **kwargs):
        return PartialBoundNode(self.bound_func, args, kwargs)


class Node:
    def __init__(self, func):
        self.__func__ = func
        update_wrapper(self, func)
        self._cache = WeakKeyDictionary()
        self.owner = None

    def __call__(self, *args, **kwargs):
        return self.__func__(*args, **kwargs)

    def __get__(self, instance, owner):
        if not instance:
            return self
        return self._cache.get(instance, None) \
               or self._cache.setdefault(instance, BoundNode(self.__func__.__get__(instance, owner)))

    def __set_name__(self, owner, name):
        self.owner = owner

    def is_start(self):
        return self.owner.__start__ is self

    def __repr__(self):
        return 'Node('+repr(self.__func__)+')'
