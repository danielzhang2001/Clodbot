import requests
import re


class Analyzer:
    @staticmethod
    async def analyze_replay(replay_link):
        # Scrape battle data from the log file of the replay link
        try:
            raw_data = requests.get(replay_link + '.log').text
        except requests.exceptions.RequestException as e:
            return f"An error occurred while fetching the replay data: {e}"
            # Find player names
        player_names = re.findall(r"\|j\|☆(.+)", raw_data)

        # Initialize dictionary to store kill/death numbers
        stats = {}

        # Find all Pokemon in the battle
        pokes = re.findall(r"\|poke\|\w+\|(.*?)(?=\||$)", raw_data)

        # Initialize stats dictionary
        for player, poke_list in enumerate([pokes[:6], pokes[6:]], start=1):
            for poke in poke_list:
                player_poke = f"p{player}: {poke}"
                if player_poke not in stats:
                    stats[player_poke] = {'player': f"p{player}",
                                          'poke': poke, 'kills': 0, 'deaths': 0}

        # Create two dictionaries for each player to store the mapping between nicknames and actual Pokémon names
        nickname_mapping_player1 = {}
        nickname_mapping_player2 = {}

        # Initialize fainted counters for each player
        player1_fainted = 0
        player2_fainted = 0

       # Find all lines when a Pokemon is switched in
        switches = re.findall(
            r"\|switch\|(p\d)a: (.*?)(?:\||, )(.+?)\|", raw_data)

        # Replace all nicknames with the actual Pokemon names for both players
        for player, nickname, pokemon in re.findall(r"\|switch\|(p\d)a: (.*?)(?:\||, )(.+?)\|", raw_data):
            if player == 'p1':
                nickname_mapping = nickname_mapping_player1
            elif player == 'p2':
                nickname_mapping = nickname_mapping_player2
            else:
                continue

            # Update nickname mapping
            nickname_mapping[nickname.strip()] = pokemon.strip()

        # Print out all nickname mappings for both players
        print("Player 1 nickname mappings:")
        for nickname, pokemon in nickname_mapping_player1.items():
            print(f"{nickname}: {pokemon}")

        print("Player 2 nickname mappings:")
        for nickname, pokemon in nickname_mapping_player2.items():
            print(f"{nickname}: {pokemon}")

        # Find all lines when a Pokemon has fainted
        faints = [line for line in raw_data.split('\n') if 'fnt' in line]

        # Iterate through each fainted line
        for faint in faints:
            if faint:
                # Grab the fainted Pokemon
                fainted_pokemon = re.search(
                    r'\|(p\d)a:(.*?)\|', faint).groups()
                player = fainted_pokemon[0]
                fainted_key = f"{player}: {nickname_mapping_player1.get(fainted_pokemon[1].strip(), fainted_pokemon[1].strip())}" if player == 'p1' else f"{player}: {nickname_mapping_player2.get(fainted_pokemon[1].strip(), fainted_pokemon[1].strip())}"

                # Increment the death counter
                if fainted_key in stats:
                    stats[fainted_key]['deaths'] += 1
                else:
                    stats[fainted_key] = {'player': fainted_pokemon[0],
                                          'poke': fainted_pokemon[1], 'kills': 0, 'deaths': 1}

                # Count fainted Pokémon for each player
                if fainted_pokemon[0] == 'p1':
                    player1_fainted += 1
                else:
                    player2_fainted += 1

                # Find the lines above the faint line
                index = raw_data.find(faint)
                above_lines = raw_data[:index].split('\n')[::-1]

                # Look at the lines above to find killer Pokemon and update its kills
                for line in above_lines:
                    if "|switch|" in line:
                        if (fainted_key.startswith("p1") and "p2a" in line) or (fainted_key.startswith("p2") and "p1a" in line):
                            killer_pokemon = re.search(
                                r'\|(p\d)a:(.*?)\|', line).groups()
                            killer_key = f"{player}: {nickname_mapping_player1.get(killer_pokemon[1].strip(), killer_pokemon[1].strip())}" if player == 'p1' else f"{player}: {nickname_mapping_player2.get(killer_pokemon[1].strip(), killer_pokemon[1].strip())}"
                            if killer_key in stats:
                                stats[killer_key]['kills'] += 1
                            else:
                                stats[killer_key] = {
                                    'player': killer_pokemon[0], 'poke': killer_pokemon[1], 'kills': 1, 'deaths': 0}
                            break

        # Find the winner
        winner = re.search(r"\|win\|(.+)", raw_data).group(1)

        # Calculate the difference
        if winner == player_names[0]:
            difference = f"({player2_fainted}-{player1_fainted})"
        else:
            difference = f"({player1_fainted}-{player2_fainted})"

        # Format and send the kill/death numbers
        message = ""
        message = f"Winner: {winner} {difference}\n\n" + message

        for idx, player_name in enumerate(player_names):
            message += f"{player_name}'s Pokemon:\n\n"
            player_pokes = {k: v for k,
                            v in stats.items() if v['player'] == f"p{idx + 1}"}

            for idx, (key, stat) in enumerate(player_pokes.items(), start=1):
                message += f"Pokemon {idx}: {stat['poke']}\nKills: {stat['kills']}, Deaths: {stat['deaths']}\n\n"

        return message
