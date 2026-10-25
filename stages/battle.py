import sys
from datetime import datetime
import pygame

# Import client
from networking.client import Client

# Import replay storage
from replay_store import save_game

# Import GUI items
from gui.battle_board import BattleBoard
from gui.fleet import Fleet


class Battle:
    """ This class manages Battle stage. """

    def __init__(self) -> None:
        self.states = {
            'client': None,
            'winner_name': None,
            'game_finished': False,
            'maps_ships_loaded': False
        }

        self.board = BattleBoard()
        self.is_my_turn = False
        self.fleet = None

        # Replay recording
        self.moves = []
        self.seen_enemy_tiles = set()
        self.opponent_name = None
        self.replay_saved = False

    def draw(self, window: pygame.display) -> None:
        """ This function draws the black battle board on window. """

        turn_text = ('My turn! Click on the enemy grid.' if self.is_my_turn
                     else 'Waiting for enemy turn...')
        self.board.draw(window, self.is_my_turn, turn_text)
        pygame.display.update()

    def load_client(self, client: Client) -> None:
        """ This function loads connected client to current stage. """
        self.states['client'] = client

    def is_client_disconnected(self) -> bool:
        """ This function checks if client is disconnected. """
        return ((self.states['client'] and self.states['client'].is_disconnected)
                or not self.states['client'])

    def load_fleet(self, fleet: Fleet) -> None:
        """ This function loads the fleet placed in ship location stage. """

        self.fleet = fleet
        self.board.load_fleet(fleet)
        self.states['maps_ships_loaded'] = True

    def attack_enemy_ship(self, event: pygame.event.Event) -> None:
        """ Click on the enemy grid -> attack that tile. """

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return

        tile = self.board.enemy_tile_at(event.pos)
        if tile is None or self.board.already_attacked(tile):
            return

        ship_name = self.states['client'].attack_enemy_tile(tile)
        self.board.register_my_attack(tile, ship_name)

        # Replay: remember my move
        self.moves.append({
            'by': 'me',
            'pos': [tile[0], tile[1]],
            'ship': ship_name if ship_name else None
        })

    def receive_enemy_attack(self) -> None:
        """ Check the enemy's last attack and update your side of the board. """

        client = self.states['client']
        response = client.get_game_data()
        enemy_name, enemy_data = next(
            (
                (key, value)
                for key, value in response.items()
                if key != client.client_name), (None, None))

        if enemy_data is None:
            return

        self.opponent_name = enemy_name

        attacked = enemy_data['attacked_tile']
        if attacked['position'] is None:
            return

        position = tuple(attacked['position'])

        # Replay: this function runs every frame, so only record new tiles
        if position not in self.seen_enemy_tiles:
            self.seen_enemy_tiles.add(position)
            self.moves.append({
                'by': 'enemy',
                'pos': [position[0], position[1]],
                'ship': attacked['ship_name'] if attacked['ship_name'] else None
            })

        destroyed = self.board.register_enemy_attack(
            position, attacked['ship_name'])

        # Tell the server a whole ship of ours is gone (counts towards defeat)
        if destroyed:
            client.ship_sinked()

    def save_replay(self, winner_name: str) -> None:
        """ Saves the finished game so it can be replayed from the menu. """

        if self.replay_saved or not self.fleet:
            return
        self.replay_saved = True

        try:
            save_game({
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'player': self.states['client'].client_name,
                'opponent': self.opponent_name or 'Unknown',
                'winner': winner_name,
                'my_fleet': [
                    {
                        'label': ship.label,
                        'cells': [list(cell) for cell in ship.cells()]
                    }
                    for ship in self.fleet.ships
                ],
                'moves': self.moves
            })
        except Exception as error:  # Never crash the game over a replay
            print('Could not save replay:', error)

    def process_events(self) -> dict:
        """
          This function handles pygame events related
          to current stage.
        """

        if self.is_client_disconnected():
            pygame.quit()
            sys.exit()

        is_my_turn = self.states['client'].is_my_turn()
        self.is_my_turn = is_my_turn

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if self.states['client']:
                    self.states['client'].disconnect()

                pygame.quit()
                sys.exit()

            if self.states['maps_ships_loaded'] and is_my_turn:
                self.attack_enemy_ship(event)

        if self.states['maps_ships_loaded']:
            self.receive_enemy_attack()

        winner_name = self.states['client'].get_winner()
        if winner_name:
            self.states['winner_name'] = winner_name
            self.states['game_finished'] = True
            self.save_replay(winner_name)

        return self.states