import random
from typing import Dict, List, Optional, Set, Tuple

Tile = Tuple[int, int]

# Board is GRID_TILES x GRID_TILES
GRID_TILES = 10

# (server letter, display name, size)
SHIP_SPECS = [
    ('B', 'Battleship', 5),
    ('C', 'Cruiser', 4),
    ('D', 'Destroyer', 4),
    ('R', 'Rescue ship', 3),
    ('S', 'Submarine', 2),
]

SHIP_INFO: Dict[str, Tuple[str, int]] = {
    name: (label, size) for name, label, size in SHIP_SPECS}


class ShipModel:
    """ A ship is just a straight line of tiles on the grid. """

    def __init__(self, name: str, label: str, size: int) -> None:
        self.name = name
        self.label = label
        self.size = size

        self.x: Optional[int] = None
        self.y: Optional[int] = None
        self.horizontal = True
        self.placed = False

        # Tiles of this ship that were hit by the enemy
        self.hit_cells: Set[Tile] = set()

    def cells(
            self,
            x: Optional[int] = None,
            y: Optional[int] = None,
            horizontal: Optional[bool] = None) -> List[Tile]:
        """ Tiles covered by this ship (optionally at a hypothetical spot). """

        x = self.x if x is None else x
        y = self.y if y is None else y
        horizontal = self.horizontal if horizontal is None else horizontal

        if x is None or y is None:
            return []

        if horizontal:
            return [(x + i, y) for i in range(self.size)]
        return [(x, y + i) for i in range(self.size)]

    @property
    def is_destroyed(self) -> bool:
        return len(self.hit_cells) >= self.size


class Fleet:
    """ The five ships of one player and the rules to place them. """

    def __init__(self) -> None:
        self.ships = [ShipModel(*spec) for spec in SHIP_SPECS]
        self.by_name = {ship.name: ship for ship in self.ships}

    def occupied(self, ignore: Optional[ShipModel] = None) -> Set[Tile]:
        tiles: Set[Tile] = set()
        for ship in self.ships:
            if ship.placed and ship is not ignore:
                tiles.update(ship.cells())
        return tiles

    def can_place(self, ship: ShipModel, x: int, y: int, horizontal: bool) -> bool:
        """ Inside the grid and not overlapping any other placed ship. """

        taken = self.occupied(ignore=ship)
        for cx, cy in ship.cells(x, y, horizontal):
            if not (0 <= cx < GRID_TILES and 0 <= cy < GRID_TILES):
                return False
            if (cx, cy) in taken:
                return False
        return True

    def place(self, ship: ShipModel, x: int, y: int, horizontal: bool) -> None:
        ship.x, ship.y, ship.horizontal, ship.placed = x, y, horizontal, True

    def unplace(self, ship: ShipModel) -> None:
        ship.x, ship.y, ship.horizontal, ship.placed = None, None, True, False

    def ship_at(self, tile: Tile) -> Optional[ShipModel]:
        for ship in self.ships:
            if ship.placed and tile in ship.cells():
                return ship
        return None

    @property
    def placed_count(self) -> int:
        return sum(1 for ship in self.ships if ship.placed)

    @property
    def all_placed(self) -> bool:
        return self.placed_count == len(self.ships)

    @property
    def destroyed_count(self) -> int:
        return sum(1 for ship in self.ships if ship.is_destroyed)

    def randomize(self, rng: random.Random = random) -> None:
        """ Place every ship at a random valid spot. """

        while True:
            for ship in self.ships:
                self.unplace(ship)

            ok = True
            for ship in sorted(self.ships, key=lambda s: -s.size):
                for _ in range(200):
                    horizontal = rng.choice([True, False])
                    max_x = GRID_TILES - (ship.size if horizontal else 1)
                    max_y = GRID_TILES - (1 if horizontal else ship.size)
                    x, y = rng.randint(0, max_x), rng.randint(0, max_y)
                    if self.can_place(ship, x, y, horizontal):
                        self.place(ship, x, y, horizontal)
                        break
                else:
                    ok = False
                    break

            if ok:
                return

    def to_grid(self) -> List[list]:
        """ Grid sent to the server: ship letter on its tiles, 0 elsewhere. """

        grid = [[0 for _ in range(GRID_TILES)] for _ in range(GRID_TILES)]
        for ship in self.ships:
            for x, y in ship.cells():
                grid[y][x] = ship.name
        return grid