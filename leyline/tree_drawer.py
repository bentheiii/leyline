from _ast import AST, Return, Expr, Str, Call, Attribute, Name, Yield, Raise
from abc import ABC
from ast import parse, iter_child_nodes
from functools import reduce
import inspect
from textwrap import dedent
from typing import Type, List, Tuple, Collection, Optional
import re

from leyline import Node
from leyline.gviz import Digraph, GraphNode, GraphEdge


class NodeData:
    def __init__(self, node: Node):
        self.node = node
        self.return_values: List[Tuple[AST, str]] = []
        self.yield_values: List[Tuple[AST, str]] = []
        self.next_nodes: List[Tuple[Node, str]] = []
        self.raise_values: List[Tuple[AST, str]] = []

    @classmethod
    def from_node(cls, node: Node):
        def extract_node_name(r_value: AST):
            if isinstance(r_value, Call) \
                    and isinstance(r_value.func, Attribute) \
                    and isinstance(r_value.func.value, Name) \
                    and r_value.func.value.id == 'self':
                return r_value.func.attr
            return None

        def get_of_type(ast: AST, t: Type[AST]):
            prev = None
            for c in iter_child_nodes(ast):
                if isinstance(c, t):
                    label = ''
                    if isinstance(prev, Expr):
                        prev = prev.value
                        if isinstance(prev, Str):
                            label = prev.s
                    yield (c, label)
                yield from get_of_type(c, t)
                prev = c

        ret = cls(node)
        source = inspect.getsource(node)
        source = dedent(source)
        ast = parse(source)
        for (r, label) in get_of_type(ast, Return):
            targ_node_name = extract_node_name(r.value)
            if targ_node_name is None:
                is_return = True
            else:
                targ_node = getattr(node.owner, targ_node_name, None)
                if not targ_node:
                    raise NameError(targ_node_name)
                is_return = not isinstance(targ_node, Node)

            if is_return:
                ret.return_values.append((r.value, label))
            else:
                ret.next_nodes.append((targ_node, label))

        for (y, label) in get_of_type(ast, Yield):
            ret.yield_values.append((y.value, label))

        for (r, label) in get_of_type(ast, Raise):
            ret.raise_values.append((r.exc, label))

        return ret


class GraphDrawer(ABC):
    def node(self, data: NodeData) -> GraphNode:
        return GraphNode(data.node.__name__)

    def edge(self, origin: NodeData, goal: Node, labels: Collection[str]) -> GraphEdge:
        return GraphEdge(origin.node.__name__, goal.__name__)

    def _graph(self, ley: Type['Ley']) -> Digraph:
        return Digraph()

    def draw_ley(self, ley: Type['Ley']):
        digraph = self._graph(ley)

        node_stack = [ley.__start__]
        known = {ley.__start__}
        while node_stack:
            node = node_stack.pop()
            data = NodeData.from_node(node)
            gnode = self.node(data)

            digraph.nodes.append(gnode)
            nexts = {}
            for next_, label in data.next_nodes:
                if next_ in nexts:
                    nexts[next_].append(label)
                else:
                    nexts[next_] = [label]

            for n, labels in nexts.items():
                if n not in known:
                    node_stack.append(n)
                    known.add(n)
                edge = self.edge(data, n, labels)
                digraph.edges.append(edge)
        return digraph.text()


ColorName = Optional[str]
StyleName = Optional[str]


class SimpleDrawer(GraphDrawer):
    def __init__(self, start_title=None, title=...,
                 start_node_color: ColorName = 'green', dead_end_color: ColorName = 'red',
                 may_return_color: ColorName = 'yellow', may_raise_color: ColorName = 'lightblue',
                 may_yield_color: ColorName = 'greenyellow',
                 only_next_color: ColorName = 'firebrick', loop_style: StyleName = 'dashed'):
        self.start_title = start_title
        self.title = title

        self.start_node_color = start_node_color
        self.dead_end_color = dead_end_color
        self.may_return_color = may_return_color
        self.may_raise_color = may_raise_color
        self.may_yield_color = may_yield_color

        self.only_next_color = only_next_color
        self.loop_style = loop_style

    def node(self, data: NodeData) -> GraphNode:
        ret = super().node(data)
        if data.node.is_start():
            ret.border_color = self.start_node_color
            if self.start_title:
                ret.additional_attributes['label'] = f'"{self.start_title}"'

        if all(n == data.node for (n, _) in data.next_nodes):
            ret.add_fill_color(self.dead_end_color)
        elif data.return_values:
            ret.add_fill_color(self.may_return_color)

        if data.raise_values:
            ret.add_fill_color(self.may_raise_color)
        if data.yield_values:
            ret.add_fill_color(self.may_yield_color)

        if data.node.__doc__:
            ret.additional_attributes['tooltip'] = f'"{data.node.__doc__.strip()}"'

        return ret

    num_pattern = re.compile(r'^(?P<prefix>.)*?(?P<num>[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)(?P<postfix>.)*?$')

    @classmethod
    def combine_labels(cls, a: str, b: str):
        if not b:
            return a
        if not a:
            return b

        a_num_match = cls.num_pattern.fullmatch(a)
        b_num_match = cls.num_pattern.fullmatch(b)
        if a_num_match and b_num_match \
                and a_num_match['prefix'] == b_num_match['prefix'] \
                and a_num_match['postfix'] == b_num_match['postfix']:
            return a_num_match['prefix'] \
                   + str(float(a_num_match['num']) + float(b_num_match['num'])) \
                   + a_num_match['postfix']
        return a + ', ' + b

    def edge(self, origin: NodeData, goal: Node, labels: Collection[str]) -> GraphEdge:
        ret = super().edge(origin, goal, labels)

        label = reduce(self.combine_labels, labels)
        if label:
            ret.additional_attributes['label'] = '"' + label + '"'

        if origin.node == goal:
            ret.styles.append('dashed')
            ret.additional_attributes['dir'] = 'back'
        elif not origin.return_values \
                and all((n in (goal, origin.node)) for (n, _) in origin.next_nodes):
            ret.add_color(self.only_next_color)

        return ret

    def _graph(self, ley: Type['Ley']):
        ret = super()._graph(ley)
        if self.title:
            title = self.title
            if title is ...:
                title = ley.__name__
            ret.title = title
        return ret


class GeneratorDrawer(SimpleDrawer):
    def __init__(self, *args, wont_yield_style='dashed', **kwargs):
        super().__init__(*args, may_yield_color=None, **kwargs)
        self.wont_yield_style = wont_yield_style

    def node(self, data: NodeData):
        ret = super().node(data)
        if not data.yield_values:
            ret.border_style = self.wont_yield_style
        return ret
