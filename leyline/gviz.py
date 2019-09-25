from io import StringIO
from itertools import chain


class Digraph:
    def __init__(self):
        self.nodes = []
        self.edges = []
        self.additional_attributes = {}

    @property
    def title(self):
        return self.additional_attributes.get('label')

    @title.setter
    def title(self, v):
        if v is None:
            del self.additional_attributes['label']
            del self.additional_attributes['labelloc']
        else:
            self.additional_attributes['label'] = '"' + v + '"'
            self.additional_attributes['labelloc'] = '"t"'

    def text(self):
        ret = StringIO()
        ret.write('digraph {\n')
        for k, v in self.additional_attributes.items():
            ret.write(f'\t{k}={v};\n')
        for n in chain(self.nodes, self.edges):
            ret.write('\t')
            ret.write(n.text())
            ret.write(';\n')
        ret.write('}')
        return ret.getvalue()


class GraphNode:
    def __init__(self, name):
        self.name = name

        self.border_color = None
        self.border_style = None
        self._fill_colors = set()
        self.additional_attributes = {}

    def add_fill_color(self, color):
        if not color:
            return
        self._fill_colors.add(color)

    def _attrs(self):
        ret = dict(self.additional_attributes)
        styles = []
        if self.border_style:
            styles.append(self.border_style)

        if len(self._fill_colors) == 1:
            ret['fillcolor'] = '"' + next(iter(self._fill_colors)) + '"'
            styles.append('filled')
        elif self._fill_colors:
            ret['fillcolor'] = '"' + ':'.join(self._fill_colors) + '"'
            styles.append('wedged,striped')

        if styles:
            ret['style'] = '"' + ','.join(styles) + '"'

        if self.border_color:
            ret['color'] = '"' + self.border_color + '"'

        return ret

    def text(self):
        attrs = self._attrs()
        if attrs:
            attrs = ' '.join(f'{k}={f}' for k, f in attrs.items())
            return f'{self.name} [{attrs}]'
        return self.name


class GraphEdge:
    def __init__(self, origin, goal):
        self.origin = origin
        self.goal = goal

        self.origin_direction = None
        self.goal_direction = None
        self.styles = []
        self._colors = set()
        self.additional_attributes = {}

    def add_color(self, color):
        if color:
            self._colors.add(color)

    def _attrs(self):
        ret = dict(self.additional_attributes)

        if self._colors:
            ret['color'] = '"' + ':'.join(self._colors) + '"'

        if self.styles:
            ret['style'] = '"' + ':'.join(self.styles) + '"'

        return ret

    def text(self):
        attrs = self._attrs()
        o_d = g_d = ""
        if self.origin_direction:
            o_d = ":"+self.origin_direction
        if self.goal_direction:
            g_d = ":"+self.goal_direction

        if attrs:
            attrs = ' ['+' '.join(f'{k}={f}' for k, f in attrs.items())+']'
        else:
            attrs = ''
        return f'{self.origin}{o_d}->{self.goal}{g_d}{attrs}'
