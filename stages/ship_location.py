import sys
import random
import pygame
from typing import Optional, Tuple

# Import client
from networking.client import Client

# Import GUI items
from gui.fleet import Fleet, ShipModel, GRID_TILES, SHIP_SPECS
from gui.battle_board import (
    BLACK, SHIP, SHIP_EDGE, TITLE, GOOD, LINE,
    TILE, GRID_PX, HEADER, LEFT_ORIGIN, RIGHT_ORIGIN,
    draw_text, draw_grid, fill_tile, outline_ship, tile_at)

DOCK_TILE = 28
DOCK_ROW = 40


class ShipLocation:
    """
      This class manages Ship location stage.

      Same black look as the battle board: your grid on the left and a
      dock with the 5 ships on the right. Drag ships onto the grid.
    """

    def __init__(self) -> None:
        self.states = {
            'client': None,
            'ship_locked': False
        }

        self.fleet = Fleet()
        self.locked = False
        self.drag: Optional[dict] = None

        px, py = RIGHT_ORIGIN
        self.panel_rect = pygame.Rect(px, py, GRID_PX, GRID_PX)
        btn_y = py + GRID_PX - 44
        self.random_btn = pygame.Rect(px, btn_y, 165, 40)
        self.lock_btn = pygame.Rect(px + 185, btn_y, 165, 40)

    # ---------- stage api ----------

    def load_client(self, client: Client) -> None:
        """ This function loads connected client to current stage. """
        self.states['client'] = client

    def is_client_disconnected(self) -> bool:
        """ This function checks if client is disconnected. """
        return ((self.states['client'] and self.states['client'].is_disconnected)
                or not self.states['client'])

    def is_game_started(self) -> bool:
        """
          This function fetch game status from server
          and checks if all clients locked their ship.
        """

        if self.states['client']:
            game_status = self.states['client'].get_game_status()
            return game_status == 'battle'

        return False

    def get_fleet(self) -> Fleet:
        """ This function returns the locked fleet. """
        return self.fleet

    def lock_ships_position(self) -> None:
        """ This function notifies to server that a client locked ships. """

        if self.states['client'] and self.fleet.all_placed:
            self.states['client'].lock_ships(self.fleet.to_grid())
            self.locked = True

    def process_events(self) -> dict:
        """
          This function handles pygame events related
          to current stage.
        """

        if self.is_client_disconnected():
            pygame.quit()
            sys.exit()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if self.states['client']:
                    self.states['client'].disconnect()

                pygame.quit()
                sys.exit()

            if self.locked:
                continue

            if event.type == pygame.MOUSEBUTTONDOWN:
                self.__mouse_down(event)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.__mouse_up(event)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                self.__rotate_at(pygame.mouse.get_pos())

        if self.locked and self.is_game_started():
            self.states['ship_locked'] = True

        return self.states

    # ---------- mouse handling ----------

    def __mouse_down(self, event: pygame.event.Event) -> None:
        if event.button == 3:
            self.__rotate_at(event.pos)
            return
        if event.button != 1 or self.drag:
            return

        if self.random_btn.collidepoint(event.pos):
            self.fleet.randomize(random)
            return
        if self.lock_btn.collidepoint(event.pos) and self.fleet.all_placed:
            self.lock_ships_position()
            return

        ship, index = self.__pick(event.pos)
        if ship:
            self.drag = {
                'ship': ship,
                'index': index,
                'prev': (ship.x, ship.y, ship.horizontal, ship.placed),
            }
            ship.placed = False  # lifted from the grid while dragging

    def __mouse_up(self, event: pygame.event.Event) -> None:
        if not self.drag:
            return

        ship, index = self.drag['ship'], self.drag['index']
        tile = tile_at(LEFT_ORIGIN, event.pos)

        if tile:
            x, y = self.__anchor(tile, index, ship.horizontal)
            if self.fleet.can_place(ship, x, y, ship.horizontal):
                self.fleet.place(ship, x, y, ship.horizontal)
            else:
                self.__restore(ship)
        elif self.panel_rect.collidepoint(event.pos):
            self.fleet.unplace(ship)  # dropped back on the dock
        else:
            self.__restore(ship)

        self.drag = None

    def __restore(self, ship: ShipModel) -> None:
        ship.x, ship.y, ship.horizontal, ship.placed = self.drag['prev']

    def __pick(self, pos) -> Tuple[Optional[ShipModel], int]:
        """ Ship under the mouse, and which of its tiles was grabbed. """

        tile = tile_at(LEFT_ORIGIN, pos)
        if tile:
            ship = self.fleet.ship_at(tile)
            if ship:
                return ship, ship.cells().index(tile)

        for i, ship in enumerate(self.fleet.ships):
            rect = self.__dock_rect(i)
            if not ship.placed and rect.collidepoint(pos):
                return ship, min((pos[0] - rect.x) // DOCK_TILE, ship.size - 1)

        return None, 0

    def __anchor(self, tile, index, horizontal) -> Tuple[int, int]:
        """ Top-left tile of a ship grabbed at `index` and dropped on `tile`. """
        if horizontal:
            return tile[0] - index, tile[1]
        return tile[0], tile[1] - index

    def __rotate_at(self, pos) -> None:
        """ Rotate the dragged ship, or the placed ship under the mouse. """

        if self.drag:
            ship = self.drag['ship']
            ship.horizontal = not ship.horizontal
            return

        tile = tile_at(LEFT_ORIGIN, pos)
        ship = self.fleet.ship_at(tile) if tile else None
        if not ship:
            return

        horizontal = not ship.horizontal
        # Same origin first, then pulled back inside the grid
        candidates = [
            (ship.x, ship.y),
            (min(ship.x, GRID_TILES - ship.size) if horizontal else ship.x,
             ship.y if horizontal else min(ship.y, GRID_TILES - ship.size)),
        ]
        for x, y in candidates:
            if self.fleet.can_place(ship, x, y, horizontal):
                self.fleet.place(ship, x, y, horizontal)
                return

    # ---------- drawing ----------

    def __dock_rect(self, index: int) -> pygame.Rect:
        ship = self.fleet.ships[index]
        return pygame.Rect(RIGHT_ORIGIN[0] + 10,
                           HEADER + 12 + index * DOCK_ROW,
                           ship.size * DOCK_TILE, DOCK_TILE)

    def draw(self, window: pygame.display) -> None:
        """ This function draws the black ship location screen. """

        window.fill(BLACK)

        draw_text(window, 'YOUR FLEET', (LEFT_ORIGIN[0], HEADER - 24))
        draw_text(window, 'SHIPS', (RIGHT_ORIGIN[0], HEADER - 24))

        draw_grid(window, LEFT_ORIGIN)
        for ship in self.fleet.ships:
            if ship.placed:
                for cell in ship.cells():
                    fill_tile(window, LEFT_ORIGIN, cell, SHIP)
                outline_ship(window, LEFT_ORIGIN, ship.cells(), SHIP_EDGE, 2)

        if self.drag:
            self.__draw_drag(window)

        self.__draw_dock(window)
        self.__draw_footer(window)

        pygame.display.update()

    def __draw_drag(self, window) -> None:
        ship, index = self.drag['ship'], self.drag['index']
        mouse = pygame.mouse.get_pos()
        tile = tile_at(LEFT_ORIGIN, mouse)

        if tile:
            x, y = self.__anchor(tile, index, ship.horizontal)
            valid = self.fleet.can_place(ship, x, y, ship.horizontal)
            color = (40, 140, 70) if valid else (170, 40, 40)
            for cx, cy in ship.cells(x, y, ship.horizontal):
                if 0 <= cx < GRID_TILES and 0 <= cy < GRID_TILES:
                    fill_tile(window, LEFT_ORIGIN, (cx, cy), color)
        else:
            # Floating ship following the cursor
            for k in range(ship.size):
                offset = (k - index) * TILE
                cx = mouse[0] - TILE // 2 + (offset if ship.horizontal else 0)
                cy = mouse[1] - TILE // 2 + (0 if ship.horizontal else offset)
                pygame.draw.rect(window, SHIP_EDGE,
                                 (cx + 3, cy + 3, TILE - 6, TILE - 6))

    def __draw_dock(self, window) -> None:
        dragged = self.drag['ship'] if self.drag else None

        for i, ship in enumerate(self.fleet.ships):
            rect = self.__dock_rect(i)
            in_dock = not ship.placed and ship is not dragged

            for k in range(ship.size):
                cell = pygame.Rect(rect.x + k * DOCK_TILE, rect.y,
                                   DOCK_TILE, DOCK_TILE).inflate(-4, -4)
                if in_dock:
                    pygame.draw.rect(window, SHIP, cell)
                else:
                    pygame.draw.rect(window, LINE, cell, 1)

            label_color = TITLE if in_dock else (90, 90, 90)
            draw_text(window, f'{ship.label} ({ship.size})',
                      (RIGHT_ORIGIN[0] + 10 + 5 * DOCK_TILE + 14, rect.y + 5),
                      color=label_color)

        hint_y = HEADER + 12 + len(self.fleet.ships) * DOCK_ROW + 16
        if not self.locked:
            draw_text(window, 'Drag ships onto your grid', (RIGHT_ORIGIN[0], hint_y))
            draw_text(window, 'Right-click or R to rotate', (RIGHT_ORIGIN[0], hint_y + 24))

        self.__draw_button(window, self.random_btn, 'Random',
                           enabled=not self.locked)
        self.__draw_button(window, self.lock_btn, 'Lock ships',
                           enabled=self.fleet.all_placed and not self.locked,
                           highlight=True)

    def __draw_button(self, window, rect, text, enabled, highlight=False) -> None:
        color = (GOOD if highlight else TITLE) if enabled else (80, 80, 80)
        pygame.draw.rect(window, color, rect, 2, border_radius=4)
        draw_text(window, text, (0, rect.y + 10), size=16, color=color,
                  center_x=rect.centerx)

    def __draw_footer(self, window) -> None:
        y = HEADER + GRID_PX + 10
        if self.locked:
            draw_text(window, 'Ships locked. Waiting for opponent...',
                      (LEFT_ORIGIN[0], y), size=16, color=GOOD)
        else:
            count = self.fleet.placed_count
            draw_text(window, f'Ships placed: {count}/{len(SHIP_SPECS)}',
                      (LEFT_ORIGIN[0], y), size=16,
                      color=GOOD if self.fleet.all_placed else TITLE)
            if self.fleet.all_placed:
                draw_text(window, 'Press "Lock ships" when ready.',
                          (LEFT_ORIGIN[0], y + 28))