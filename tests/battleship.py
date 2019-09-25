from collections import Counter
from io import StringIO
from itertools import product
from typing import List, Union

import numpy as np

from randombag import RandomBag

from leyline import LeyGenerating, Node


class BattleshipTemplate:
    def __init__(self, width, height):
        self.width = width
        self.height = height

    def transpose(self) -> 'BattleshipTemplate':
        return type(self)(self.height, self.width)

    def size(self):
        return self.width * self.height


class BattleShip:
    def __init__(self, spots):
        self.spots = {s: True for s in spots}
        self.health = len(self.spots)

    def hit(self, x, y):
        prev_value = self.spots[(x, y)]
        self.spots[(x, y)] = False
        if prev_value:
            self.health -= 1
            if not self.health:
                return BattleshipBoard.Sunk
        return BattleshipBoard.Hit


class BattleshipBoard:
    Miss = 0
    Hit = 1
    Sunk = 2
    Win = 3

    def __init__(self, width, height, ships: List[Union[BattleshipTemplate, int]], seed=None):
        self.ships = []
        self.misses = set()
        self.width = width
        self.height = height

        if seed:
            np.random.seed(seed)

        def is_empty(x, y):
            for ship in self.ships:
                if (x, y) in ship.spots:
                    return False
            return True

        def is_clear(ship: BattleshipTemplate, x, y):
            left = x
            right = x + ship.width
            up = y
            down = y + ship.height
            if left > 0:
                left -= 1
            if up > 0:
                up -= 1
            if right > width:
                return False
            elif right < width:
                right += 1
            if down > height:
                return False
            elif down < height:
                down += 1
            for row in range(up, down):
                for col in range(left, right):
                    if not is_empty(col, row):
                        return False
            return True

        ships = [
            BattleshipTemplate(s, 1) if isinstance(s, int) else s
            for s in ships
        ]
        trans = np.random.choice([False, True], len(ships))
        ships = [(s.transpose() if t else s) for (s, t) in zip(ships, trans)]
        for bst in ships:
            while True:
                x = np.random.randint(0, width)
                y = np.random.randint(0, height)
                if is_clear(bst, x, y):
                    coords = []
                    for row in range(y, y + bst.height):
                        for col in range(x, x + bst.width):
                            coords.append((col, row))
                    self.ships.append(BattleShip(coords))
                    break

    def multiline(self):
        ret = StringIO()
        first = True
        for row in range(self.height):
            if first:
                first = False
            else:
                ret.write('\n')
            for col in range(self.width):
                v = self.occupier(col, row)
                if v is None:
                    if (col, row) in self.misses:
                        c = '%'
                    else:
                        c = '.'
                else:
                    if v.spots[(col, row)]:
                        c = 'O'
                    else:
                        c = 'X'
                ret.write(c)

        return ret.getvalue()

    def occupier(self, x, y):
        for ship in self.ships:
            if (x, y) in ship.spots:
                return ship
        return None

    def strike(self, x, y):
        v = self.occupier(x, y)
        if not v:
            self.misses.add((x, y))
            return self.Miss
        else:
            if v.hit(x, y) == self.Sunk:
                if all(ship.health == 0 for ship in self.ships):
                    return self.Win
                return v
            return self.Hit

    def struck(self, x, y):
        v = self.occupier(x, y)
        if not v:
            return (x, y) in self.misses
        else:
            return not v.spots[(x, y)]


class Player(LeyGenerating):
    def __init__(self, seed=None):
        self.whitelist = RandomBag(seed=seed)

    def mark_sunk(self, ship):
        for (x, y) in ship.spots:
            for (o_x, o_y) in product((-1, 0, 1), repeat=2):
                self.whitelist.discard((x + o_x, y + o_y))

    def __start__(self):
        for y in range(board.height):
            for x in range(y % 2, board.width, 2):
                self.whitelist.add((x, y))
        return self.random_hit()

    @Node
    def random_hit(self):
        target = self.whitelist.pop()
        hit = (yield target, 'wild')
        if hit == BattleshipBoard.Hit:
            "begin seek"
            return self.seek_start(target)
        elif hit == BattleshipBoard.Win:
            return None

        if isinstance(hit, BattleShip):
            self.mark_sunk(hit)

        return self.random_hit()

    @staticmethod
    def cw_random_start():
        ret = [(0, -1), (1, 0), (0, 1), (-1, 0)]  # ULDR
        start = np.random.randint(0, 4)
        ret.extend(ret[:start])
        del ret[:start]
        return ret

    @Node
    def seek_start(self, first_hit):
        return self.seek_roll(first_hit, self.cw_random_start())

    @Node
    def seek_roll(self, first_hit, direction_stack):
        direction = direction_stack.pop()
        target = (first_hit[0] + direction[0], first_hit[1] + direction[1])
        if target[0] < 0 or target[1] < 0 or target[0] >= board.width or target[1] >= board.height or board.struck(
                *target):
            "invalid target"
            return self.seek_roll(first_hit, direction_stack)

        hit = (yield target, 'roll')
        if hit == BattleshipBoard.Hit:
            "hit"
            return self.seek(direction, target, first_hit)
        elif hit == BattleshipBoard.Win:
            return None

        if isinstance(hit, BattleShip):
            self.mark_sunk(hit)
            "sunk"
            return self.random_hit()

        "miss"
        return self.seek_roll(first_hit, direction_stack)

    @Node
    def seek(self, direction, last_hit, first_hit):
        target = (last_hit[0] + direction[0], last_hit[1] + direction[1])
        if target[0] < 0 or target[1] < 0 or target[0] >= board.width or target[1] >= board.height or board.struck(
                *target):
            "invalid target"
            return self.reverse_seek(direction, first_hit)

        hit = (yield target, 'seek')
        if hit == BattleshipBoard.Hit:
            "hit"
            return self.seek(direction, target, first_hit)
        elif hit == BattleshipBoard.Win:
            return None

        if isinstance(hit, BattleShip):
            self.mark_sunk(hit)
            "sunk"
            return self.random_hit()

        "miss"
        return self.reverse_seek(direction, first_hit)

    @Node
    def reverse_seek(self, direction, first_hit):
        """
        reverse direction and continue seeking
        """
        direction = (-direction[0], -direction[1])
        return self.seek(direction, first_hit, first_hit)

if True:
    print(Player.graph())
    exit()

board = BattleshipBoard(10, 10, [5, 4, 3, 3, 2])
play = Player()()
answer = None
shoots = Counter()
while True:
    print(board.multiline())
    try:
        target, kind = play.send(answer)
    except StopIteration:
        break
    print(f'player shoots at {target}')
    shoots[kind] += 1
    answer = board.strike(*target)
print(f'victory in {shoots} shots')
