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
