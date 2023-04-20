# showdown.py
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
