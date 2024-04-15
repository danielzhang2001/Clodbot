"""
The function to analyze a Pokemon Showdown replay link and display stats.
"""

# pylint: disable=import-error
# pylint: disable=wildcard-import,unused-wildcard-import
import requests  # type: ignore
from showdown.replay import *


class Analyze:
    @staticmethod
    async def analyze_replay(replay_link):
        # Analyzes a replay link to display all necessary stats and send it in a message.
        try:
            response = requests.get(replay_link + ".log")
            response.raise_for_status()
            raw_data = response.text
        except requests.exceptions.RequestException:
            return f"**{replay_link}** is an invalid replay link."
        players = get_player_names(raw_data)
        pokes = get_pokes(raw_data)
        p1_count = get_p1_count(raw_data)
        nickname_mapping_player1, nickname_mapping_player2 = get_nickname_mappings(
            raw_data
        )
        stats = get_stats(
            raw_data,
            pokes,
            p1_count,
            nickname_mapping_player1,
            nickname_mapping_player2,
        )
        stats = process_revives(raw_data, stats)
        winner = get_winner(raw_data)
        loser = get_loser(raw_data)
        difference = get_difference(raw_data, players)
        message = create_message(winner, loser, difference, stats, players)
        return message
