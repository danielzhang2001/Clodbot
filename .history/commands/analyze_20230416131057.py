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
        player_info = re.findall(r"\|player\|(p\d)\|(.+?)\|", raw_data)
        players = {player[0]: player[1] for player in player_info}

        print(players)

        # Initialize dictionary to store kill/death numbers
        stats = {}

        # Find all Pokemon in the battle
        pokes = re.findall(r"\|poke\|\w+\|([^,|\r\n]+)", raw_data)

        # Create two dictionaries for each player to store the mapping between nicknames and actual Pokémon names
        nickname_mapping_player1 = {}
        nickname_mapping_player2 = {}

        # Find all lines when a Pokemon is switched in
        switches = re.findall(
            r"\|switch\|(p\d)a: (.*?)(?:\||, )(.+?)\|", raw_data)

        replaces = re.findall(
            r"\|replace\|(p\d)a: (.*?)(?=\||$)(?:\|)(.*[^|\n])", raw_data)

       # Replace all nicknames with the actual Pokemon names for both players
        for player, nickname, pokemon in switches + replaces:
            if player == 'p1':
                nickname_mapping = nickname_mapping_player1
            elif player == 'p2':
                nickname_mapping = nickname_mapping_player2
            else:
                continue

            # Update nickname mapping
            actual_name = re.sub(r',.*$', '', pokemon.strip())
            nickname_mapping[nickname.strip()] = actual_name

        mapped_pokes_player1 = [nickname_mapping_player1.get(
            poke, poke) for poke in pokes[:6]]
        mapped_pokes_player2 = [nickname_mapping_player2.get(
            poke, poke) for poke in pokes[6:]]

        # Print out all nickname mappings for both players
        print("Player 1 nickname mappings:")
        for nickname, pokemon in nickname_mapping_player1.items():
            print(f"{nickname}: {pokemon}")

        print("Player 2 nickname mappings:")
        for nickname, pokemon in nickname_mapping_player2.items():
            print(f"{nickname}: {pokemon}")

        # Initialize stats dictionary
        for player, poke_list in enumerate([mapped_pokes_player1, mapped_pokes_player2], start=1):
            for poke in poke_list:
                player_poke = f"p{player}: {poke}"
                print(f"{player}")
                if player_poke not in stats:
                    stats[player_poke] = {'player': f"p{player}",
                                          'poke': poke, 'kills': 0, 'deaths': 0}

        for item in stats.items():
            print(item)

        # Initialize fainted counters for each player
        player1_fainted = 0
        player2_fainted = 0

        # Find all lines when a Pokemon has fainted
        faints = [line for line in raw_data.split('\n') if 'faint' in line]

        # Iterate through each fainted line
        for faint in faints:
            if faint:
                # Grab the fainted Pokemon
                match = re.search(
                    r'\|faint\|(p\d)a: (.*[^|])', faint)
                player = match.group(1)
                fainted_pokemon = match.group(2)
                fainted_key = f"{player}: {nickname_mapping_player1.get(fainted_pokemon.strip(), fainted_pokemon.strip())}" if player == 'p1' else f"{player}: {nickname_mapping_player2.get(fainted_pokemon.strip(), fainted_pokemon.strip())}"
                print(f"Fainted: {fainted_key}")
                # Increment the death counter
                if fainted_key in stats:
                    stats[fainted_key]['deaths'] += 1
                else:
                    stats[fainted_key] = {'player': fainted_pokemon[0],
                                          'poke': fainted_pokemon[1], 'kills': 0, 'deaths': 1}

                # Count fainted Pokémon for each player
                if player == 'p1':
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
                            if player == 'p1':
                                player = 'p2'
                            else:
                                player = 'p1'
                            killer_key = f"{player}: {nickname_mapping_player1.get(killer_pokemon[1].strip(), killer_pokemon[1].strip())}" if player == 'p1' else f"{player}: {nickname_mapping_player2.get(killer_pokemon[1].strip(), killer_pokemon[1].strip())}"
                            print(f"Killer: {killer_key}")
                            if killer_key in stats:
                                stats[killer_key]['kills'] += 1
                            else:
                                stats[killer_key] = {
                                    'player': killer_pokemon[0], 'poke': killer_pokemon[1], 'kills': 1, 'deaths': 0}
                            break

        # Find the winner
        winner = re.search(r"\|win\|(.+)", raw_data).group(1)

        # Calculate the difference
        if winner == players['p2']:
            difference = f"({player2_fainted}-{player1_fainted})"
        else:
            difference = f"({player1_fainted}-{player2_fainted})"

        for item in stats.items():
            print(item)

        # Format and send the kill/death numbers
        message = ""
        message = f"Winner: {winner} {difference}\n\n" + message

        for player_num, player_name in players.items():
            message += f"{player_name}'s Pokemon:\n\n"
            player_pokes = {k: v for k,
                            v in stats.items() if v['player'] == player_num}

            for idx, (key, stat) in enumerate(player_pokes.items(), start=1):
                message += f"Pokemon {idx}: {stat['poke']}\nKills: {stat['kills']}, Deaths: {stat['deaths']}\n\n"

        return message
