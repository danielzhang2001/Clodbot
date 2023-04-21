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
        player_info = re.findall(r"\|player\|(p\d)\|(.+?)\|", raw_data)
        players = {player[0]: player[1] for player in player_info}

        # Initialize dictionary to store kill/death numbers
        stats = {}

        # Initialize counter for p1 Pokemon
        p1_count = 0

        # Find all Pokemon in the battle
        poke_lines = [line for line in raw_data.split(
            '\n') if '|poke|' in line]
        pokes = [re.search(r"\|poke\|\w+\|([^,|\r\n]+)", line).group(1)
                 for line in poke_lines]

        # Iterate through all Pokemon and count p1 Pokemon
        p1_count = sum(1 for line in poke_lines if '|poke|p1|' in line)

        # Create two dictionaries for each player to store the mapping between nicknames and actual Pokémon names
        nickname_mapping_player1, nickname_mapping_player2 = get_nickname_mappings(
            raw_data)

        # Call the initialize_stats function
        stats = initialize_stats(
            pokes, p1_count, nickname_mapping_player1, nickname_mapping_player2)

        stats, player1_fainted, player2_fainted = process_faints(
            raw_data, stats, nickname_mapping_player1, nickname_mapping_player2)

        # Process kills
        stats = process_kills(
            raw_data, stats, nickname_mapping_player1, nickname_mapping_player2)

        stats, player1_fainted, player2_fainted = process_revives(
            raw_data, stats, player1_fainted, player2_fainted)

        # Find the winner
        winner = re.search(r"\|win\|(.+)", raw_data).group(1)

        # Calculate the point difference
        if winner == players['p1']:
            difference = f"({player2_fainted}-{player1_fainted})"
        else:
            difference = f"({player1_fainted}-{player2_fainted})"

        # Format and send the kill/death numbers
        message = format_results(winner, difference, stats, players)
        return message
