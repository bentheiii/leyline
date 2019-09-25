from abc import ABC, abstractmethod
from typing import Generator

from leyline.node import Node, BoundNode, PartialBoundNode
from leyline.tree_drawer import SimpleDrawer, GeneratorDrawer


class Ley(ABC):
    @abstractmethod
    def __start__(self, *args, **kwargs):
        pass

    def _is_node(self, n):
        return isinstance(n, (Node, BoundNode, PartialBoundNode))

    def _is_return_value(self, v):
        return v is None

    def __call__(self, *args, **kwargs):
        current = self.__start__
        while True:
            if self._is_node(current):
                current = current(*args, **kwargs)
            elif self._is_return_value(current):
                return current
            else:
                raise ValueError(f'value {current} is neither a node nor an acceptable return value')

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not getattr(cls.__start__, "__isabstractmethod__", False) and not isinstance(cls.__start__, Node):
            n = Node(cls.__start__)
            n.__set_name__(cls, '__start__')

            cls.__start__ = n

    @classmethod
    def graph(cls, *args, **kwargs):
        return cls.DefaultDrawerCls(*args, **kwargs).draw_ley(cls)

    DefaultDrawerCls = SimpleDrawer


class LeyGenerating(Ley, ABC):
    def __call__(self, *args, state_change_callback=None, **kwargs):
        current = self.__start__
        while True:
            if self._is_node(current):
                if state_change_callback:
                    state_change_callback(current)
                gen = current(*args, **kwargs)
                if isinstance(gen, Generator):
                    current = (yield from gen)
                else:
                    current = gen
            elif self._is_return_value(current):
                return current
            else:
                raise ValueError(f'value {current} is neither a node nor an acceptable return value')

    DefaultDrawerCls = GeneratorDrawer

# todo async ley
# todo async generator ley
