"""
The function to analyze a Pokemon Showdown replay link and display stats.
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
        players = get_players(json_data)
        print(f"players: {players}")
        pokemon = get_pokemon(json_data)
        print(f"pokemon: {pokemon}")
        revives = get_revives(json_data)
        print(f"revives: {revives}")
        winner = get_winner(json_data)
        print(f"winner: {winner}")
        loser = get_loser(json_data)
        print(f"loser: {loser}")
        difference = get_difference(players, winner, revives)
        initialize_stats(pokes)
        process_stats(json_data)
        message = create_message(players, winner, loser, difference)
        return message
