import sys
import pygame
from typing import Optional

from replay_store import get_games

# Import GUI items (same look as the battle board)
from gui.fleet import SHIP_INFO
from gui.battle_board import (
    BLACK, SHIP, SHIP_EDGE, TITLE, GOOD, BAD, LINE, HOVER,
    DESTROYED_FILL, DESTROYED_EDGE,
    GRID_PX, HEADER, LEFT_ORIGIN, RIGHT_ORIGIN,
    draw_text, draw_grid, fill_tile, outline_ship,
    draw_dot, draw_cross, tile_rect)

ROWS_PER_PAGE = 8
ROW_H = 40


class Replay:
    """
      This class manages Replay stage.

      Mode 'list': games played by the username (time + opponent).
      Mode 'view': step through one game move by move, like a chess replay.
    """

    def __init__(self, username: str) -> None:
        self.username = username
        self.states = {'exit': False}
        self.games = get_games(username)

        self.mode = 'list'
        self.scroll = 0
        self.game: Optional[dict] = None
        self.step = 0

        self.x0 = LEFT_ORIGIN[0]
        self.width = RIGHT_ORIGIN[0] + GRID_PX - LEFT_ORIGIN[0]

        # Keep the controls inside the window: the footer needs ~90px
        # (buttons + move text + winner line).
        win_h = pygame.display.get_surface().get_height()
        self.footer_y = min(HEADER + GRID_PX + 10, win_h - 96)

        self.back_btn = pygame.Rect(self.x0, self.footer_y, 110, 36)
        self.prev_btn = pygame.Rect(self.x0, self.footer_y, 90, 36)
        self.next_btn = pygame.Rect(self.x0 + 100, self.footer_y, 90, 36)
        self.games_btn = pygame.Rect(
            self.x0 + self.width - 130, self.footer_y, 130, 36)

    # ---------- events ----------

    def process_events(self) -> dict:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if self.mode == 'list':
                self.__list_event(event)
            else:
                self.__view_event(event)

        return self.states

    def __row_rect(self, i: int) -> pygame.Rect:
        return pygame.Rect(self.x0, HEADER + 10 + i * ROW_H,
                           self.width, ROW_H - 6)

    def __list_event(self, event: pygame.event.Event) -> None:
        max_scroll = max(0, len(self.games) - ROWS_PER_PAGE)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.states['exit'] = True
            elif event.key == pygame.K_UP:
                self.scroll = max(0, self.scroll - 1)
            elif event.key == pygame.K_DOWN:
                self.scroll = min(max_scroll, self.scroll + 1)
            return

        if event.type != pygame.MOUSEBUTTONDOWN:
            return

        if event.button == 4:
            self.scroll = max(0, self.scroll - 1)
        elif event.button == 5:
            self.scroll = min(max_scroll, self.scroll + 1)
        elif event.button == 1:
            if self.back_btn.collidepoint(event.pos):
                self.states['exit'] = True
                return

            visible = self.games[self.scroll:self.scroll + ROWS_PER_PAGE]
            for i, game in enumerate(visible):
                if self.__row_rect(i).collidepoint(event.pos):
                    self.game = game
                    self.step = 0
                    self.mode = 'view'
                    return

    def __view_event(self, event: pygame.event.Event) -> None:
        moves = self.game.get('moves', [])

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RIGHT:
                self.step = min(len(moves), self.step + 1)
            elif event.key == pygame.K_LEFT:
                self.step = max(0, self.step - 1)
            elif event.key == pygame.K_ESCAPE:
                self.mode = 'list'
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.next_btn.collidepoint(event.pos):
                self.step = min(len(moves), self.step + 1)
            elif self.prev_btn.collidepoint(event.pos):
                self.step = max(0, self.step - 1)
            elif self.games_btn.collidepoint(event.pos):
                self.mode = 'list'

    # ---------- drawing ----------

    def draw(self, window: pygame.display) -> None:
        window.fill(BLACK)

        if self.mode == 'list':
            self.__draw_list(window)
        else:
            self.__draw_view(window)

        pygame.display.update()

    def __draw_button(self, window, rect, text, enabled=True) -> None:
        color = TITLE if enabled else (80, 80, 80)
        pygame.draw.rect(window, color, rect, 2, border_radius=4)
        draw_text(window, text, (0, rect.y + 10), size=16, color=color,
                  center_x=rect.centerx)

    def __draw_list(self, window) -> None:
        draw_text(window, f'REPLAYS - {self.username}', (self.x0, HEADER - 24))

        if not self.games:
            draw_text(window, 'No saved games for this username.',
                      (self.x0, HEADER + 14))

        visible = self.games[self.scroll:self.scroll + ROWS_PER_PAGE]
        for i, game in enumerate(visible):
            rect = self.__row_rect(i)
            pygame.draw.rect(window, LINE, rect, 1, border_radius=4)

            won = (game.get('winner', '').strip().lower()
                   == game.get('player', '').strip().lower())
            draw_text(window,
                      f"{game.get('time', '?')}    vs {game.get('opponent', '?')}",
                      (rect.x + 12, rect.y + 9), size=16, color=TITLE)
            draw_text(window, 'Won' if won else 'Lost', (0, rect.y + 9),
                      size=16, color=GOOD if won else BAD,
                      center_x=rect.right - 40)

        if len(self.games) > ROWS_PER_PAGE:
            end = min(len(self.games), self.scroll + ROWS_PER_PAGE)
            draw_text(window,
                      f'{self.scroll + 1}-{end} of {len(self.games)} '
                      '(scroll wheel / arrow keys)',
                      (self.x0 + 130, self.footer_y + 10), size=16)

        self.__draw_button(window, self.back_btn, 'Back')

    @staticmethod
    def __coord(pos) -> str:
        return f'{chr(65 + pos[0])}{pos[1] + 1}'

    def __describe(self, move: dict) -> str:
        who = 'You' if move['by'] == 'me' else self.game.get('opponent', 'Enemy')
        ship = move.get('ship')
        if ship:
            ship = SHIP_INFO.get(ship, (ship, 0))[0]
        result = f'hit {ship}' if ship else 'missed'
        return f"{who} {result} at {self.__coord(move['pos'])}"

    def __draw_view(self, window) -> None:
        game = self.game
        moves = game.get('moves', [])

        # Rebuild both boards from the first `step` moves
        my_marks, enemy_marks = {}, {}      # tile -> ship letter or None
        enemy_hits_by_ship = {}
        for move in moves[:self.step]:
            tile = tuple(move['pos'])
            ship = move.get('ship')
            if move['by'] == 'me':
                enemy_marks[tile] = ship
                if ship:
                    enemy_hits_by_ship.setdefault(ship, set()).add(tile)
            else:
                my_marks[tile] = ship

        last = moves[self.step - 1] if self.step else None

        draw_text(window, 'YOUR FLEET', (LEFT_ORIGIN[0], HEADER - 24))
        draw_text(window, f"VS {str(game.get('opponent', 'ENEMY')).upper()}",
                  (RIGHT_ORIGIN[0], HEADER - 24))

        draw_grid(window, LEFT_ORIGIN)
        draw_grid(window, RIGHT_ORIGIN)

        # My ships (red outline once completely destroyed)
        my_hit_tiles = {t for t, ship in my_marks.items() if ship}
        for ship in game.get('my_fleet', []):
            cells = [tuple(c) for c in ship['cells']]
            destroyed = all(c in my_hit_tiles for c in cells)
            for cell in cells:
                fill_tile(window, LEFT_ORIGIN, cell,
                          DESTROYED_FILL if destroyed else SHIP)
            outline_ship(window, LEFT_ORIGIN, cells,
                         DESTROYED_EDGE if destroyed else SHIP_EDGE,
                         3 if destroyed else 2)

        # Enemy ships are revealed once completely destroyed
        for name, cells in enemy_hits_by_ship.items():
            if name in SHIP_INFO and len(cells) >= SHIP_INFO[name][1]:
                cells = sorted(cells)
                for cell in cells:
                    fill_tile(window, RIGHT_ORIGIN, cell, DESTROYED_FILL)
                outline_ship(window, RIGHT_ORIGIN, cells, DESTROYED_EDGE)

        # Shots: red dot = hit, gray cross = miss (same as battle screen)
        for origin, marks in ((LEFT_ORIGIN, my_marks),
                              (RIGHT_ORIGIN, enemy_marks)):
            for tile, ship in marks.items():
                if ship:
                    draw_dot(window, origin, tile)
                else:
                    draw_cross(window, origin, tile)

        # White frame around the latest move
        if last:
            origin = RIGHT_ORIGIN if last['by'] == 'me' else LEFT_ORIGIN
            pygame.draw.rect(window, HOVER,
                             tile_rect(origin, tuple(last['pos'])), 3)

        # Controls
        self.__draw_button(window, self.prev_btn, '< Prev', self.step > 0)
        self.__draw_button(window, self.next_btn, 'Next >',
                           self.step < len(moves))
        self.__draw_button(window, self.games_btn, 'All games')

        if self.step == 0:
            text = f'Start of game ({len(moves)} moves). Press Next.'
        else:
            text = f'Move {self.step}/{len(moves)}: {self.__describe(last)}'
        draw_text(window, text, (self.x0, self.footer_y + 44), size=16)

        if self.step == len(moves):
            draw_text(window, f"Winner: {game.get('winner', '?')}",
                      (self.x0, self.footer_y + 68), size=16, color=GOOD)