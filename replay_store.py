"""
Local storage for finished games so they can be replayed later.

Games are saved in `replays.json` next to this file. Each game is stored
from the point of view of the player who played it, so a username only sees
its own games.
"""

import json
import os
from typing import List

REPLAY_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'replays.json')


def _norm(name) -> str:
    return (name or '').strip().lower()


def _load_all() -> List[dict]:
    try:
        with open(REPLAY_FILE, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def save_game(record: dict) -> None:
    """ Append one finished game to the replay file. """

    games = _load_all()
    games.append(record)

    tmp_file = REPLAY_FILE + '.tmp'
    with open(tmp_file, 'w', encoding='utf-8') as file:
        json.dump(games, file, indent=2)
    os.replace(tmp_file, REPLAY_FILE)


def get_games(username: str) -> List[dict]:
    """ Games played by `username`, newest first. """

    key = _norm(username)
    games = [g for g in _load_all() if _norm(g.get('player')) == key]
    games.sort(key=lambda g: g.get('time', ''), reverse=True)
    return games


def has_games(username: str) -> bool:
    return bool(get_games(username))