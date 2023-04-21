import requests
import re
from showdown.showdown import *


class Analyze:
    @staticmethod
    async def analyze_replay(replay_link):
        # Scrape battle data from the log file of the replay link
        try:
            raw_data = requests.get(replay_link + '.log').text
        except requests.exceptions.RequestException as e:
            return f"An error occurred while fetching the replay data: {e}"

        # Find player names
        players = get_player_names(raw_data)

        # Find all Pokemon in the battle
        pokes = get_pokes(raw_data)

        # Iterate through all Pokemon and count p1 Pokemon
        p1_count = get_p1_count(raw_data)

        # Create two dictionaries for each player to store the mapping between nicknames and actual Pokémon names
        nickname_mapping_player1, nickname_mapping_player2 = get_nickname_mappings(
            raw_data)

        # Call the initialize_stats function
        stats = initialize_stats(
            pokes, p1_count, nickname_mapping_player1, nickname_mapping_player2)

        # Process faints
        stats, player1_fainted, player2_fainted = process_faints(
            raw_data, stats, nickname_mapping_player1, nickname_mapping_player2)

        # Process kills
        stats = process_kills(
            raw_data, stats, nickname_mapping_player1, nickname_mapping_player2)

        # Process revives
        stats, player1_fainted, player2_fainted = process_revives(
            raw_data, stats, player1_fainted, player2_fainted)

        # Find the winner
        winner = get_winner(raw_data)

        # Calculate the point difference
        difference = get_difference(raw_data, players)

        # Format and send the kill/death numbers
        message = format_results(winner, difference, stats, players)
        
        return message
