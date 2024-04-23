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
        pokemon = testget_pokes(json_data)
        winner = testget_winner(json_data)
        loser = testget_loser(json_data)
        testinitialize_stats(pokes)
        testprocess_stats(json_data)
        revives = testget_revives(json_data)
        difference = testget_difference(players, winner, revives)
        message = testcreate_message(players, winner, loser, difference)
        return message
