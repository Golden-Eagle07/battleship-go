import pygame
from typing import Dict, Optional, Set, Tuple

from gui.fleet import Fleet, ShipModel, GRID_TILES, SHIP_INFO, SHIP_SPECS

Tile = Tuple[int, int]

# ---------- layout ----------
TILE = 50
GRID_PX = TILE * GRID_TILES

MARGIN = 30
GAP = 40
HEADER = 40
FOOTER = 110

BOARD_WIDTH = MARGIN * 2 + GRID_PX * 2 + GAP
BOARD_HEIGHT = HEADER + GRID_PX + FOOTER

LEFT_ORIGIN = (MARGIN, HEADER)
RIGHT_ORIGIN = (MARGIN + GRID_PX + GAP, HEADER)

# ---------- colors ----------
BLACK = (0, 0, 0)
LINE = (55, 55, 55)
SHIP = (45, 65, 90)
SHIP_EDGE = (110, 140, 180)
HIT = (220, 30, 30)
MISS = (140, 140, 140)
HOVER = (255, 255, 255)
TITLE = (200, 200, 200)
DESTROYED_FILL = (80, 12, 12)
DESTROYED_EDGE = (255, 70, 70)
GOOD = (80, 220, 120)
BAD = (255, 90, 90)

BANNER_SECONDS = 3.5

_fonts: Dict[int, pygame.font.Font] = {}


def get_font(size: int) -> pygame.font.Font:
    if size not in _fonts:
        _fonts[size] = pygame.font.Font(
            'assets/fonts/CascadiaCode-SemiBold.ttf', size)
    return _fonts[size]


def draw_text(window, text, pos, size=14, color=TITLE, center_x=None) -> None:
    surf = get_font(size).render(text, True, color)
    if center_x is not None:
        pos = (center_x - surf.get_width() // 2, pos[1])
    window.blit(surf, pos)


def tile_rect(origin, tile, size=TILE) -> pygame.Rect:
    return pygame.Rect(origin[0] + tile[0] * size,
                       origin[1] + tile[1] * size, size, size)


def tile_at(origin, pos) -> Optional[Tile]:
    """ Translate a mouse position into a tile of the grid at origin. """
    x = (pos[0] - origin[0]) // TILE
    y = (pos[1] - origin[1]) // TILE
    if 0 <= x < GRID_TILES and 0 <= y < GRID_TILES:
        return int(x), int(y)
    return None


def draw_grid(window, origin) -> None:
    ox, oy = origin
    for i in range(GRID_TILES + 1):
        pygame.draw.line(window, LINE, (ox + i * TILE, oy),
                         (ox + i * TILE, oy + GRID_PX))
        pygame.draw.line(window, LINE, (ox, oy + i * TILE),
                         (ox + GRID_PX, oy + i * TILE))


def fill_tile(window, origin, tile, color) -> None:
    pygame.draw.rect(window, color, tile_rect(origin, tile).inflate(-6, -6))


def outline_ship(window, origin, cells, color, width=3) -> None:
    """ Rectangle around all tiles of one ship. """
    rects = [tile_rect(origin, c) for c in cells]
    box = rects[0].unionall(rects[1:]).inflate(-2, -2)
    pygame.draw.rect(window, color, box, width, border_radius=4)


def draw_dot(window, origin, tile) -> None:
    pygame.draw.circle(window, HIT, tile_rect(origin, tile).center, TILE // 4)


def draw_cross(window, origin, tile) -> None:
    rect = tile_rect(origin, tile).inflate(-26, -26)
    pygame.draw.line(window, MISS, rect.topleft, rect.bottomright, 3)
    pygame.draw.line(window, MISS, rect.topright, rect.bottomleft, 3)


class BattleBoard:
    """
      Single black screen that shows both maps side by side:
      your fleet on the left, enemy waters on the right.

      Markers (same on both grids):
        - red dot    -> hit
        - gray cross -> miss
      A completely destroyed ship gets a red outline, a banner is shown
      and the counters under each grid go up.
    """

    def __init__(self) -> None:
        self.fleet: Optional[Fleet] = None

        self.ally_hits: Set[Tile] = set()
        self.ally_misses: Set[Tile] = set()

        self.enemy_hits: Set[Tile] = set()
        self.enemy_misses: Set[Tile] = set()
        self.enemy_hits_by_ship: Dict[str, Set[Tile]] = {}
        self.enemy_destroyed: Set[str] = set()

        self.banner: Optional[Tuple[str, Tuple[int, int, int], int]] = None

    # ---------- state ----------

    def load_fleet(self, fleet: Fleet) -> None:
        self.fleet = fleet

    def enemy_tile_at(self, pos) -> Optional[Tile]:
        return tile_at(RIGHT_ORIGIN, pos)

    def already_attacked(self, tile: Tile) -> bool:
        return tile in self.enemy_hits or tile in self.enemy_misses

    def register_my_attack(self, tile: Tile, ship_name: Optional[str]) -> bool:
        """ Returns True if this attack completely destroyed an enemy ship. """

        if not ship_name:
            self.enemy_misses.add(tile)
            return False

        self.enemy_hits.add(tile)
        cells = self.enemy_hits_by_ship.setdefault(ship_name, set())
        cells.add(tile)

        label, size = SHIP_INFO[ship_name]
        if len(cells) >= size and ship_name not in self.enemy_destroyed:
            self.enemy_destroyed.add(ship_name)
            self.__show_banner(f'You destroyed the {label}!', GOOD)
            return True
        return False

    def register_enemy_attack(
            self,
            tile: Tile,
            ship_name: Optional[str]) -> Optional[ShipModel]:
        """ Returns the ship if this attack completely destroyed it. """

        if not ship_name:
            self.ally_misses.add(tile)
            return None

        if tile in self.ally_hits:
            return None
        self.ally_hits.add(tile)

        ship = self.fleet.by_name[ship_name]
        ship.hit_cells.add(tile)
        if ship.is_destroyed:
            self.__show_banner(f'Enemy destroyed your {ship.label}!', BAD)
            return ship
        return None

    def __show_banner(self, text, color) -> None:
        until = pygame.time.get_ticks() + int(BANNER_SECONDS * 1000)
        self.banner = (text, color, until)

    # ---------- drawing ----------

    def draw(self, window: pygame.Surface, can_attack: bool, turn_text: str) -> None:
        window.fill(BLACK)

        draw_text(window, 'YOUR FLEET', (LEFT_ORIGIN[0], HEADER - 24))
        draw_text(window, 'ENEMY WATERS', (RIGHT_ORIGIN[0], HEADER - 24))

        draw_grid(window, LEFT_ORIGIN)
        draw_grid(window, RIGHT_ORIGIN)

        # Your ships (+ red outline when completely destroyed)
        for ship in self.fleet.ships:
            fill = DESTROYED_FILL if ship.is_destroyed else SHIP
            for cell in ship.cells():
                fill_tile(window, LEFT_ORIGIN, cell, fill)
            outline_ship(window, LEFT_ORIGIN, ship.cells(),
                         DESTROYED_EDGE if ship.is_destroyed else SHIP_EDGE,
                         3 if ship.is_destroyed else 2)

        # Enemy ships that are completely destroyed are revealed
        for name in self.enemy_destroyed:
            cells = sorted(self.enemy_hits_by_ship[name])
            for cell in cells:
                fill_tile(window, RIGHT_ORIGIN, cell, DESTROYED_FILL)
            outline_ship(window, RIGHT_ORIGIN, cells, DESTROYED_EDGE)

        for tile in self.ally_hits:
            draw_dot(window, LEFT_ORIGIN, tile)
        for tile in self.ally_misses:
            draw_cross(window, LEFT_ORIGIN, tile)
        for tile in self.enemy_hits:
            draw_dot(window, RIGHT_ORIGIN, tile)
        for tile in self.enemy_misses:
            draw_cross(window, RIGHT_ORIGIN, tile)

        if can_attack:
            tile = tile_at(RIGHT_ORIGIN, pygame.mouse.get_pos())
            if tile and not self.already_attacked(tile):
                pygame.draw.rect(window, HOVER, tile_rect(RIGHT_ORIGIN, tile), 3)

        self.__draw_footer(window, turn_text)

    def __draw_footer(self, window, turn_text) -> None:
        total = len(SHIP_SPECS)
        y = HEADER + GRID_PX + 10

        draw_text(window, f'Ships lost: {self.fleet.destroyed_count}/{total}',
                  (LEFT_ORIGIN[0], y))
        draw_text(window,
                  f'Enemy ships destroyed: {len(self.enemy_destroyed)}/{total}',
                  (RIGHT_ORIGIN[0], y))

        draw_text(window, turn_text, (MARGIN, y + 30), size=16,
                  color=(221, 221, 221))

        if self.banner:
            text, color, until = self.banner
            if pygame.time.get_ticks() < until:
                draw_text(window, text, (0, y + 62), size=20, color=color,
                          center_x=BOARD_WIDTH // 2)
            else:
                self.banner = None