import requests
import re
from showdown.showdown import get_nickname_mappings


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

        # Update nickname mapping
        mapped_pokes_player1 = [nickname_mapping_player1.get(
            poke, poke) for poke in pokes[:p1_count]]
        mapped_pokes_player2 = [nickname_mapping_player2.get(
            poke, poke) for poke in pokes[p1_count:]]

        # Initialize stats dictionary
        for player, poke_list in enumerate([mapped_pokes_player1, mapped_pokes_player2], start=1):
            for poke in poke_list:
                player_poke = f"p{player}: {poke}"
                if player_poke not in stats:
                    stats[player_poke] = {'player': f"p{player}",
                                          'poke': poke, 'kills': 0, 'deaths': 0}

        # Initialize fainted counters for each player
        player1_fainted = 0
        player2_fainted = 0

        # Find all lines when a Pokemon has fainted
        faints = [line for line in raw_data.split(
            '\n') if re.match(r"^\|faint\|", line)]

        # Find all lines when a Pokemon is revived
        revives = re.findall(r"\|-heal\|(p\d): (\w+)\|", raw_data)

        # Iterate through each fainted line
        for faint in faints:
            if faint:
                # Grab the fainted Pokemon
                match = re.search(
                    r'\|faint\|(p\d)a: (.*[^|])', faint)
                player = match.group(1)
                fainted_pokemon = match.group(2)
                fainted_key = f"{player}: {nickname_mapping_player1.get(fainted_pokemon.strip(), fainted_pokemon.strip())}" if player == 'p1' else f"{player}: {nickname_mapping_player2.get(fainted_pokemon.strip(), fainted_pokemon.strip())}"
                # Increment the death counter
                if fainted_key in stats:
                    stats[fainted_key]['deaths'] += 1
                else:
                    stats[fainted_key] = {'player': player,
                                          'poke': fainted_pokemon, 'kills': 0, 'deaths': 1}
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
                        if killer_key in stats:
                            stats[killer_key]['kills'] += 1
                        else:
                            stats[killer_key] = {
                                'player': killer_pokemon[0], 'poke': killer_pokemon[1], 'kills': 1, 'deaths': 0}
                        break

        # Check if the Pokemon has been revived and update deaths accordingly
        for revive in revives:
            player, revived_pokemon = revive
            for _, value in stats.items():
                if value['poke'] == revived_pokemon and value['player'] == player:
                    value['deaths'] -= 1
                    if player == 'p1':
                        player1_fainted -= 1
                    else:
                        player2_fainted -= 1
                    break

        # Find the winner
        winner = re.search(r"\|win\|(.+)", raw_data).group(1)

        # Calculate the point difference
        if winner == players['p1']:
            difference = f"({player2_fainted}-{player1_fainted})"
        else:
            difference = f"({player1_fainted}-{player2_fainted})"

        # Format and send the kill/death numbers
        message = ""
        message = f"Winner: {winner} {difference}\n\n" + message

        for player_num, player_name in players.items():
            message += f"{player_name}'s Pokemon:\n\n"
            player_pokes = {k: v for k,
                            v in stats.items() if v['player'] == player_num}

            for idx, (_, stat) in enumerate(player_pokes.items(), start=1):
                message += f"Pokemon {idx}: {stat['poke']}\nKills: {stat['kills']}, Deaths: {stat['deaths']}\n\n"

        return message
