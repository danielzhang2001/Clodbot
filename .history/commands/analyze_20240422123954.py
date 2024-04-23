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
        # Analyzes a replay link to display all necessary stats and send it in a message.
        try:
            response = requests.get(replay_link + ".log")
            response.raise_for_status()
            raw_data = response.text
        except requests.exceptions.RequestException:
            raise InvalidReplay(replay_link)
        players = get_player_names(raw_data)
        pokes = get_pokes(raw_data)
        p1_count = get_p1_count(raw_data)
        nickname_mapping1, nickname_mapping2 = get_nickname_mappings(raw_data)
        stats = get_stats(
            raw_data,
            pokes,
            p1_count,
            nickname_mapping1,
            nickname_mapping2,
        )
        stats = process_revives(raw_data, stats)
        winner = get_winner(raw_data)
        loser = get_loser(raw_data)
        difference = get_difference(raw_data, players)
        message = create_message(winner, loser, difference, stats, players)
        return message

    @staticmethod
    async def test_replay(replay_link: str) -> str:
        # Analyzes a replay link to display all necessary stats and send it in a message.
        try:
            response = requests.get(replay_link + ".json")
            response.raise_for_status()
            json_data = json.loads(response.text)
        except requests.exceptions.RequestException:
            raise InvalidReplay(replay_link)
        players = testget_player_names(json_data)
        pokes = testget_pokes(json_data)
        winner = testget_winner(json_data)
        loser = testget_loser(json_data)
        difference = testget_difference
        testinitialize_stats(pokes)
        testprocess_stats(json_data)
        revives = testget_revives(json_data)
        message = testcreate_message(winner, loser, difference)
        return message
