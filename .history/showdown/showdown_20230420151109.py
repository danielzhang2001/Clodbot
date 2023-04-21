import re


def get_nickname_mappings(raw_data):
    nickname_mapping_player1 = {}
    nickname_mapping_player2 = {}

    switches = re.findall(r"\|switch\|(p\d)a: (.*?)(?:\||, )(.+?)\|", raw_data)
    replaces = re.findall(
        r"\|replace\|(p\d)a: (.*?)(?=\||$)(?:\|)(.*[^|\n])", raw_data)

    for player, nickname, pokemon in switches + replaces:
        if player == 'p1':
            nickname_mapping = nickname_mapping_player1
        elif player == 'p2':
            nickname_mapping = nickname_mapping_player2
        else:
            continue
        actual_name = re.sub(r',.*$', '', pokemon.strip())
        nickname_mapping[nickname.strip()] = actual_name

    return nickname_mapping_player1, nickname_mapping_player2


def initialize_stats(pokes, p1_count, nickname_mapping_player1, nickname_mapping_player2):
    mapped_pokes_player1 = [nickname_mapping_player1.get(
        poke, poke) for poke in pokes[:p1_count]]
    mapped_pokes_player2 = [nickname_mapping_player2.get(
        poke, poke) for poke in pokes[p1_count:]]

    stats = {}
    for player, poke_list in enumerate([mapped_pokes_player1, mapped_pokes_player2], start=1):
        for poke in poke_list:
            player_poke = f"p{player}: {poke}"
            if player_poke not in stats:
                stats[player_poke] = {'player': f"p{player}",
                                      'poke': poke, 'kills': 0, 'deaths': 0}

    return stats


def process_faints(raw_data, stats, nickname_mapping_player1, nickname_mapping_player2):
    # Initialize fainted counters for each player
    player1_fainted = 0
    player2_fainted = 0

    # Find all lines when a Pokemon has fainted
    faints = [line for line in raw_data.split(
        '\n') if re.match(r"^\|faint\|", line)]

    # Iterate through each fainted line
    for faint in faints:
        if faint:
            # Grab the fainted Pokemon
            match = re.search(r'\|faint\|(p\d)a: (.*[^|])', faint)
            player = match.group(1)
            fainted_pokemon = match.group(2)
            fainted_key = f"{player}: {nickname_mapping_player1.get(fainted_pokemon.strip(), fainted_pokemon.strip())}" if player == 'p1' else f"{player}: {nickname_mapping_player2.get(fainted_pokemon.strip(), fainted_pokemon.strip())}"

            # Increment the death counter
            if fainted_key in stats:
                stats[fainted_key]['deaths'] += 1
            else:
                stats[fainted_key] = {
                    'player': player, 'poke': fainted_pokemon, 'kills': 0, 'deaths': 1}

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

    return stats, player1_fainted, player2_fainted


def process_kills(raw_data, stats, nickname_mapping_player1, nickname_mapping_player2):
    # Find all lines when a Pokemon has fainted
    faints = [line for line in raw_data.split(
        '\n') if re.match(r"^\|faint\|", line)]

    # Iterate through each fainted line
    for faint in faints:
        if faint:
            # Grab the fainted Pokemon
            match = re.search(r'\|faint\|(p\d)a: (.*[^|])', faint)
            player = match.group(1)
            fainted_pokemon = match.group(2)
            fainted_key = f"{player}: {nickname_mapping_player1.get(fainted_pokemon.strip(), fainted_pokemon.strip())}" if player == 'p1' else f"{player}: {nickname_mapping_player2.get(fainted_pokemon.strip(), fainted_pokemon.strip())}"

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

    return stats


def process_revives(raw_data, stats, player1_fainted, player2_fainted):
    # Find all lines when a Pokemon is revived
    revives = re.findall(r"\|-heal\|(p\d): (\w+)\|", raw_data)

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

    return stats, player1_fainted, player2_fainted


def format_results(winner, difference, stats, players):
    message = ""
    message = f"Winner: {winner} {difference}\n\n" + message

    for player_num, player_name in players.items():
        message += f"{player_name}'s Pokemon:\n\n"
        player_pokes = {k: v for k,
                        v in stats.items() if v['player'] == player_num}

        for idx, (_, stat) in enumerate(player_pokes.items(), start=1):
            message += f"Pokemon {idx}: {stat['poke']}\nKills: {stat['kills']}, Deaths: {stat['deaths']}\n\n"

    return message
