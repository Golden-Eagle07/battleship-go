import sys
import pygame

# Import client
from networking.client import Client

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

    def receive_enemy_attack(self) -> None:
        """ Check the enemy's last attack and update your side of the board. """

        response = self.states['client'].get_game_data()
        enemy_data = next(
            (
                value
                for key, value in response.items()
                if key != self.states['client'].client_name), None)

        attacked = enemy_data['attacked_tile']
        if attacked['position'] is None:
            return

        position = tuple(attacked['position'])
        destroyed = self.board.register_enemy_attack(
            position, attacked['ship_name'])

        # Tell the server a whole ship of ours is gone (counts towards defeat)
        if destroyed:
            self.states['client'].ship_sinked()

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

        return self.states