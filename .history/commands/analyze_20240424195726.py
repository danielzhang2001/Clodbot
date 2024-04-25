"""
The functions to analyze a Pokemon Showdown replay link and display stats.
"""

# pylint: disable=import-error
# pylint: disable=wildcard-import,unused-wildcard-import
import requests  # type: ignore
import json
from showdown.replay import *
from errors import *


class Analyze:
    @staticmethod
    async def analyze_replay(replay_link: str) -> str:
        # Analyzes a replay link to display all necessary stats and sends it in a message.
        try:
            response = requests.get(replay_link + ".json")
            response.raise_for_status()
            json_data = json.loads(response.text)
        except requests.exceptions.RequestException:
            raise InvalidReplay(replay_link)
        players = get_replay_players(json_data)
        pokemon = get_pokemon(json_data)
        revives = get_revives(json_data)
        winner = get_winner(json_data)
        loser = get_loser(json_data)
        initialize_stats(pokemon)
        process_stats(json_data)
        difference = get_difference(players, winner, revives)
        message = create_message(players, winner, loser, difference)
        return message
