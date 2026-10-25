import pygame

# Import stages
from stages.intro import Intro
from stages.battle import Battle
from stages.ship_location import ShipLocation
from stages.podium import Podium
from gui.battle_board import BOARD_WIDTH, BOARD_HEIGHT
from stages.replay import Replay


FPS = 30
WIDTH, HEIGHT = 500, 500
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Battleship')


def set_window_size(width: int, height: int) -> None:
    """ Resize the window: ship location, battle and replay use the wide black board. """
    global WIN
    WIN = pygame.display.set_mode((width, height))


class GameState:
    """
    This class manages game states in a way to modularize
    stages and keep codebase organized.

    Resource: https://www.youtube.com/watch?v=j9yMFG3D7fg
    """

    def __init__(self) -> None:
        self.client = None
        self.state = 'intro'
        self.intro_stage = Intro()
        self.ship_location_stage: ShipLocation = None
        self.battle_stage: Battle = None
        self.podium_stage: Podium = Podium()
        self.replay_stage: Replay = None

    def intro(self) -> None:
        """ Intro stage state handler. """
        try:
            states = self.intro_stage.process_events()
            self.intro_stage.draw(WIN)

            if states['open_replay']:
                self.state = 'replay'
                set_window_size(BOARD_WIDTH, BOARD_HEIGHT)  # before Replay()
                self.replay_stage = Replay(states['username'])
            elif states['players_connected']:
                self.state = 'ship_location'
                set_window_size(BOARD_WIDTH, BOARD_HEIGHT)
                self.client = states['client']
                self.ship_location_stage = ShipLocation()
                self.ship_location_stage.load_client(self.client)
                self.intro_stage = None
        except ConnectionRefusedError:
            print("Could not connect to server.")
            if self.intro_stage:
                self.intro_stage.status_message = "Connection failed. Please check server."

    def replay(self) -> None:
        """ Replay stage state handler. """

        states = self.replay_stage.process_events()
        self.replay_stage.draw(WIN)

        if states['exit']:
            self.intro_stage.states['open_replay'] = False
            self.replay_stage = None
            self.state = 'intro'
            set_window_size(WIDTH, HEIGHT)

    def ship_location(self) -> None:
        """ Ship location stage state handler. """

        states = self.ship_location_stage.process_events()
        self.ship_location_stage.draw(WIN)

        if states['ship_locked']:
            self.state = 'battle'

            self.battle_stage = Battle()
            self.battle_stage.load_client(self.client)
            self.battle_stage.load_fleet(self.ship_location_stage.get_fleet())
            self.ship_location_stage = None

    def battle(self) -> None:
        """ Battle stage state handler. """

        states = self.battle_stage.process_events()
        self.battle_stage.draw(WIN)

        if states['game_finished']:
            self.state = 'podium'
            set_window_size(WIDTH, HEIGHT)

            self.podium_stage = Podium()
            self.podium_stage.load_client(self.client)
            self.podium_stage.load_winner_name(states['winner_name'])
            self.battle_stage = None

    def podium(self) -> None:
        """ Podium stage state handler. """

        states = self.podium_stage.process_events()
        self.podium_stage.draw(WIN)

        if states['reset_game']:
            self.state = 'ship_location'

            set_window_size(BOARD_WIDTH, BOARD_HEIGHT)
            self.ship_location_stage = ShipLocation()
            self.ship_location_stage.load_client(self.client)
            self.podium_stage = None

    def state_manager(self) -> None:
        """ This function keeps tracking of current game state. """

        if self.state == 'intro':
            self.intro()
        elif self.state == 'ship_location':
            self.ship_location()
        elif self.state == 'battle':
            self.battle()
        elif self.state == 'podium':
            self.podium()
        elif self.state == 'replay':
            self.replay()


def main() -> None:
    game_state = GameState()
    clock = pygame.time.Clock()

    while True:
        clock.tick(FPS)  # Force game loop to run at FPS limit
        game_state.state_manager()


if __name__ == '__main__':
    main()