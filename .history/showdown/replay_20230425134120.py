"""
General functions in analyzing Pokemon Showdown replay links.
"""

import re


def get_player_names(raw_data):
    """Retrieves player names."""
    player_info = re.findall(r"\|player\|(p\d)\|(.+?)\|", raw_data)
    players = {player[0]: player[1] for player in player_info}
    return players


def get_pokes(raw_data):
    """Retrieves Pokemon names."""
    poke_lines = [line for line in raw_data.split('\n') if '|poke|' in line]
    pokes = [re.search(r"\|poke\|\w+\|([^,|\r\n]+)", line).group(1) for line in poke_lines]
    return pokes


def get_p1_count(raw_data):
    """Retrieves the number of Pokemon player 1 has."""
    poke_lines = [line for line in raw_data.split('\n') if '|poke|' in line]
    p1_count = sum(1 for line in poke_lines if '|poke|p1|' in line)
    return p1_count


def get_nickname_mappings(raw_data):
    """Retrieves the mappings from nickname/form name to actual Pokemon name for each player."""
    nickname_mapping_player1 = {}
    nickname_mapping_player2 = {}
    switches = re.findall(r"\|switch\|(p\d)a: (.*?)(?:\||, )(.+?)\|", raw_data)
    replaces = re.findall(r"\|replace\|(p\d)a: (.*?)(?=\||$)(?:\|)(.*[^|\n])", raw_data)
    for player, nickname, pokemon in switches + replaces:
        if player == 'p1':
            nickname_mapping = nickname_mapping_player1
        elif player == 'p2':
            nickname_mapping = nickname_mapping_player2
        else:
            continue
        actual_name = re.sub(r',.*$', '', pokemon.strip())
        nickname_mapping[nickname.strip()] = actual_name
    print("Player 1 nickname mappings:")
    for nickname, actual_name in nickname_mapping_player1.items():
        print(f"{nickname} -> {actual_name}")

    print("\nPlayer 2 nickname mappings:")
    for nickname, actual_name in nickname_mapping_player2.items():
        print(f"{nickname} -> {actual_name}")
    return nickname_mapping_player1, nickname_mapping_player2


def initialize_stats(pokes, p1_count, nickname_mapping_player1, nickname_mapping_player2):
    """Initializes stats for each Pokemon, consisting of the player each Pokemon belongs to, the Pokemon itself, and its kills and deaths."""
    mapped_pokes_player1 = [nickname_mapping_player1.get(poke, poke) for poke in pokes[:p1_count]]
    mapped_pokes_player2 = [nickname_mapping_player2.get(poke, poke) for poke in pokes[p1_count:]]
    print("Mapped Pokes:")
    for key in mapped_pokes_player1:
        print(f"{key}")
    for key in mapped_pokes_player2:
        print(f"{key}")
    stats = {}
    for player, poke_list in enumerate([mapped_pokes_player1, mapped_pokes_player2], start=1):
        for poke in poke_list:
            player_poke = f"p{player}: {poke}"
            if player_poke not in stats:
                stats[player_poke] = {'player': f"p{player}", 'poke': poke, 'kills': 0, 'deaths': 0}
    return stats


def process_faints(raw_data, stats, nickname_mapping_player1, nickname_mapping_player2):
    """Populates the death values for all Pokemon based on the faints in the log."""
    player1_fainted = 0
    player2_fainted = 0
    faints = [line for line in raw_data.split('\n') if re.match(r"^\|faint\|", line)]
    for faint in faints:
        if faint:
            match = re.search(r'\|faint\|(p\d)a: (.*[^|])', faint)
            player = match.group(1)
            fainted_pokemon = match.group(2)
            fainted_key = (
                f"{player}: {nickname_mapping_player1.get(fainted_pokemon.strip(), fainted_pokemon.strip())}"
                if player == 'p1'
                else
                f"{player}: {nickname_mapping_player2.get(fainted_pokemon.strip(), fainted_pokemon.strip())}"
            )
            if fainted_key in stats:
                stats[fainted_key]['deaths'] += 1
            else:
                stats[fainted_key] = {
                    'player': player, 'poke': fainted_pokemon, 'kills': 0, 'deaths': 1}
            if player == 'p1':
                player1_fainted += 1
            else:
                player2_fainted += 1
    return stats, player1_fainted, player2_fainted


def process_kills(raw_data, stats, nickname_mapping_player1, nickname_mapping_player2):
    """Populates the kill values for all Pokemon based on the Pokemon on the opposing side when a Pokemon faints in the log."""
    faints = [line for line in raw_data.split('\n') if re.match(r"^\|faint\|", line)]
    for faint in faints:
        if faint:
            match = re.search(r'\|faint\|(p\d)a: (.*[^|])', faint)
            player = match.group(1)
            fainted_pokemon = match.group(2)
            fainted_key = (
                f"{player}: {nickname_mapping_player1.get(fainted_pokemon.strip(), fainted_pokemon.strip())}"
                if player == 'p1'
                else
                f"{player}: {nickname_mapping_player2.get(fainted_pokemon.strip(), fainted_pokemon.strip())}"
            )
            index = raw_data.find(faint)
            above_lines = raw_data[:index].split('\n')[::-1]
            for line in above_lines:
                if "|switch|" in line:
                    if (fainted_key.startswith("p1") and "p2a" in line) or (fainted_key.startswith("p2") and "p1a" in line):
                        killer_pokemon = re.search(
                            r'\|(p\d)a:(.*?)\|', line).groups()
                        if player == 'p1':
                            player = 'p2'
                        else:
                            player = 'p1'
                        killer_key = (
                            f"{player}: {nickname_mapping_player1.get(killer_pokemon[1].strip(), killer_pokemon[1].strip())}"
                            if player == 'p1'
                            else
                            f"{player}: {nickname_mapping_player2.get(killer_pokemon[1].strip(), killer_pokemon[1].strip())}"
                        )
                        if killer_key in stats:
                            stats[killer_key]['kills'] += 1
                        else:
                            stats[killer_key] = {
                                'player': killer_pokemon[0], 'poke': killer_pokemon[1], 'kills': 1, 'deaths': 0}
                        break
    return stats


def process_revives(raw_data, stats, player1_fainted, player2_fainted):
    """Repopulates the death values for Pokemon that have been revived by Revival Blessing. If revived, take away one death."""
    revives = re.findall(r"\|-heal\|(p\d): (\w+)\|", raw_data)
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


def get_winner(raw_data):
    """Retrieves the winning player."""
    winner = re.search(r"\|win\|(.+)", raw_data).group(1)
    return winner


def get_difference(raw_data, players):
    """Retrieves the point difference from winning player to losing player based on the opposing player's faints."""
    player1_fainted = len(re.findall(r"\|faint\|p1", raw_data))
    player2_fainted = len(re.findall(r"\|faint\|p2", raw_data))
    winner = get_winner(raw_data)
    if winner == players['p1']:
        difference = f"({player2_fainted}-{player1_fainted})"
    else:
        difference = f"({player1_fainted}-{player2_fainted})"
    return difference


def create_message(winner, difference, stats, players):
    """Creates and returns final message."""
    message = ""
    message = f"**Winner: ||{winner} {difference}||**\n\n" + message
    for player_num, player_name in players.items():
        message += f"{player_name}'s Pokemon:\n"
        player_pokes = {key: value for key, value in stats.items() if value['player'] == player_num}
        poke_message = ""
        for _, stat in player_pokes.items():
            poke_message += f"{stat['poke']} (Kills: {stat['kills']}, Deaths: {stat['deaths']})\n"
        message += f"||```\n{poke_message.strip()}\n```||\n"
    return message
