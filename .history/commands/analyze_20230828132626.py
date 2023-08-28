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
        """Analyzes a replay link to display all necessary stats and send it in a message."""
        try:
            raw_data = requests.get(replay_link + '.log').text
        except requests.exceptions.RequestException as exception:
            return f"An error occurred while fetching the replay data: {exception}"
        players = get_player_names(raw_data)
        pokes = get_pokes(raw_data)
        p1_count = get_p1_count(raw_data)
        nickname_mapping_player1, nickname_mapping_player2 = get_nickname_mappings(raw_data)
        print("Nickname mappings for player 1:")
        for nickname, pokemon in nickname_mapping_player1.items():
            print(f"{nickname}: {pokemon}")
        print("\nNickname mappings for player 2:")
        for nickname, pokemon in nickname_mapping_player2.items():
            print(f"{nickname}: {pokemon}")
        stats = initialize_stats(pokes, p1_count, nickname_mapping_player1, nickname_mapping_player2)
        stats, player1_fainted, player2_fainted = process_faints(raw_data, stats, nickname_mapping_player1, nickname_mapping_player2)
        stats = process_kills(raw_data, stats, nickname_mapping_player1, nickname_mapping_player2)
        stats, player1_fainted, player2_fainted = process_revives(raw_data, stats, player1_fainted, player2_fainted)
        winner = get_winner(raw_data)
        difference = get_difference(raw_data, players)
        message = create_message(winner, difference, stats, players)
        return message
