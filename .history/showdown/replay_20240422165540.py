"""
General functions in analyzing Pokemon Showdown replay links.
"""

import re
import json
from typing import Dict, List, Tuple

stats = {}


def get_player_names(raw_data: str) -> Dict[str, str]:
    # Retrieves player names.
    player_info = re.findall(r"\|player\|(p\d)\|(.+?)\|", raw_data)
    players = {player[0]: player[1] for player in player_info}
    return players


def get_pokes(raw_data: str) -> List[str]:
    # Retrieves Pokemon names. If a Pokemon has a nickname, gets their nickname instead.
    nickname_mapping = {}
    switches = re.findall(r"\|switch\|.*?: (.*?)(?:\||, )(.+?)\|", raw_data)
    for nickname, pokemon in switches:
        actual_name = re.sub(r",.*$", "", pokemon.strip())
        nickname_mapping[actual_name] = nickname.strip()
    poke_lines = [line for line in raw_data.split("\n") if "|poke|" in line]
    pokes = [
        re.search(r"\|poke\|\w+\|([^,|\r\n]+)", line).group(1) for line in poke_lines
    ]
    nicknamed_pokes = [nickname_mapping.get(pokemon, pokemon) for pokemon in pokes]
    nicknamed_pokes = [re.sub(r"-\*$", "", poke) for poke in nicknamed_pokes]
    print(f"ACTUAL POKES: {nicknamed_pokes}")
    return nicknamed_pokes


def get_p1_count(raw_data: str) -> int:
    # Retrieves the number of Pokemon player 1 has.
    poke_lines = [line for line in raw_data.split("\n") if "|poke|" in line]
    p1_count = sum(1 for line in poke_lines if "|poke|p1|" in line)
    return p1_count


def get_nickname_mappings(raw_data: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    # Retrieves the mappings from nickname/form name to actual Pokemon name for each player.
    nickname_mapping1 = {}
    nickname_mapping2 = {}
    switches = re.findall(r"\|switch\|(p\d)a: (.*?)(?:\||, )(.+?)\|", raw_data)
    replaces = re.findall(r"\|replace\|(p\d)a: (.*?)(?=\||$)(?:\|)(.*[^|\n])", raw_data)
    for player, nickname, pokemon in switches + replaces:
        if player == "p1":
            nickname_mapping = nickname_mapping1
        elif player == "p2":
            nickname_mapping = nickname_mapping2
        else:
            continue
        actual_name = re.sub(r",.*$", "", pokemon.strip())
        nickname_mapping[nickname.strip()] = actual_name
    print(f"actual nickname mapping 1: {nickname_mapping1}")
    print(f"actual nickname mapping 2: {nickname_mapping2}")
    return nickname_mapping1, nickname_mapping2


def get_winner(raw_data: str) -> str:
    # Retrieves the winning player.
    winner = re.search(r"\|win\|(.+)", raw_data).group(1)
    return winner


def get_loser(raw_data: str) -> str:
    # Retrieves the losing player.
    winner = get_winner(raw_data)
    players = get_player_names(raw_data)
    for id, name in players.items():
        if name != winner:
            return name


def get_difference(raw_data: str, players: Dict[str, str]) -> str:
    # Retrieves the point difference from winning player to losing player based on the opposing player's faints.
    player1_fainted = len(re.findall(r"\|faint\|p1", raw_data))
    player2_fainted = len(re.findall(r"\|faint\|p2", raw_data))
    winner = get_winner(raw_data)
    if winner == players["p1"]:
        difference = (
            f"({player2_fainted - player1_fainted}-{player1_fainted - player1_fainted})"
        )
    else:
        difference = (
            f"({player1_fainted - player2_fainted}-{player2_fainted - player2_fainted})"
        )
    return difference


def get_stats(
    raw_data: str,
    pokes: List[str],
    p1_count: int,
    nickname_mapping1: Dict[str, str],
    nickname_mapping2: Dict[str, str],
) -> Dict[str, Dict[str, Dict[str, int]]]:
    # Processes and returns the final stats.
    stats = initialize_stats(pokes, p1_count, nickname_mapping1, nickname_mapping2)
    stats = process_faints(raw_data, stats, nickname_mapping1, nickname_mapping2)
    stats = process_kills(raw_data, stats, nickname_mapping1, nickname_mapping2)
    return stats


def initialize_stats(
    pokes: List[str],
    p1_count: int,
    nickname_mapping1: Dict[str, str],
    nickname_mapping2: Dict[str, str],
) -> Dict[str, Dict[str, int]]:
    # Initializes stats for each Pokemon, consisting of the player each Pokemon belongs to, the Pokemon itself, and its kills and deaths.
    mapped_pokes_player1 = [
        nickname_mapping1.get(poke, poke) for poke in pokes[:p1_count]
    ]
    mapped_pokes_player2 = [
        nickname_mapping2.get(poke, poke) for poke in pokes[p1_count:]
    ]
    stats = {}
    for player, poke_list in enumerate(
        [mapped_pokes_player1, mapped_pokes_player2], start=1
    ):
        for poke in poke_list:
            player_poke = f"p{player}: {poke}"
            if player_poke not in stats:
                stats[player_poke] = {
                    "player": f"p{player}",
                    "poke": poke,
                    "kills": 0,
                    "deaths": 0,
                }
    return stats


def process_faints(
    raw_data: str,
    stats: Dict[str, Dict[str, int]],
    nickname_mapping1: Dict[str, str],
    nickname_mapping2: Dict[str, str],
) -> Dict[str, Dict[str, int]]:
    # Populates the death values for all Pokemon based on the faints in the log.
    faints = [line for line in raw_data.split("\n") if re.match(r"^\|faint\|", line)]
    for faint in faints:
        if faint:
            match = re.search(r"\|faint\|(p\d)a: (.*[^|])", faint)
            player = match.group(1)
            fainted_pokemon = match.group(2)
            fainted_key = (
                f"{player}: {nickname_mapping1.get(fainted_pokemon.strip(), fainted_pokemon.strip())}"
                if player == "p1"
                else f"{player}: {nickname_mapping2.get(fainted_pokemon.strip(), fainted_pokemon.strip())}"
            )
            if fainted_key in stats:
                stats[fainted_key]["deaths"] += 1
            else:
                stats[fainted_key] = {
                    "player": player,
                    "poke": fainted_pokemon,
                    "kills": 0,
                    "deaths": 1,
                }
    return stats


def process_kills(
    raw_data: str,
    stats: Dict[str, Dict[str, int]],
    nickname_mapping1: Dict[str, str],
    nickname_mapping2: Dict[str, str],
) -> Dict[str, Dict[str, int]]:
    # Populates the kill values for all Pokemon based on the Pokemon on the opposing side when a Pokemon faints in the log.
    faints = [line for line in raw_data.split("\n") if re.match(r"^\|faint\|", line)]
    for faint in faints:
        if faint:
            match = re.search(r"\|faint\|(p\d)a: (.*[^|])", faint)
            player = match.group(1)
            fainted_pokemon = match.group(2)
            fainted_key = (
                f"{player}: {nickname_mapping1.get(fainted_pokemon.strip(), fainted_pokemon.strip())}"
                if player == "p1"
                else f"{player}: {nickname_mapping2.get(fainted_pokemon.strip(), fainted_pokemon.strip())}"
            )
            index = raw_data.find(faint)
            above_lines = raw_data[:index].split("\n")[::-1]
            for line in above_lines:
                if "|switch|" in line:
                    if (fainted_key.startswith("p1") and "p2a" in line) or (
                        fainted_key.startswith("p2") and "p1a" in line
                    ):
                        killer_pokemon = re.search(r"\|(p\d)a:(.*?)\|", line).groups()
                        if player == "p1":
                            player = "p2"
                        else:
                            player = "p1"
                        killer_key = (
                            f"{player}: {nickname_mapping1.get(killer_pokemon[1].strip(), killer_pokemon[1].strip())}"
                            if player == "p1"
                            else f"{player}: {nickname_mapping2.get(killer_pokemon[1].strip(), killer_pokemon[1].strip())}"
                        )
                        if killer_key in stats:
                            stats[killer_key]["kills"] += 1
                        else:
                            stats[killer_key] = {
                                "player": killer_pokemon[0],
                                "poke": killer_pokemon[1],
                                "kills": 1,
                                "deaths": 0,
                            }
                        break
    return stats


def process_revives(
    raw_data: str, stats: Dict[str, Dict[str, int]]
) -> Dict[str, Dict[str, int]]:
    # Repopulates the death values for Pokemon that have been revived by Revival Blessing. If revived, take away one death.
    revives = re.findall(r"\|-heal\|(p\d): (\w+)\|", raw_data)
    for revive in revives:
        player, revived_pokemon = revive
        for _, value in stats.items():
            if value["poke"] == revived_pokemon and value["player"] == player:
                value["deaths"] -= 1
    return stats


def format_stats(
    players: Dict[str, str], stats: Dict[str, Dict[str, int]]
) -> List[Tuple[str, List[Tuple[str, List[int]]]]]:
    # Returns a list of players, their associated Pokemon and the kills and deaths that come with each Pokemon.
    formatted_stats = []
    for player_num, player_name in players.items():
        player_data = []
        player_pokes = {
            key: value for key, value in stats.items() if value["player"] == player_num
        }
        for poke_key, poke_stats in player_pokes.items():
            player_data.append(
                [poke_stats["poke"], [poke_stats["kills"], poke_stats["deaths"]]]
            )
        formatted_stats.append([player_name, player_data])
    return formatted_stats


def create_message(
    winner: str,
    loser: str,
    difference: str,
    stats: Dict[str, Dict[str, int]],
    players: Dict[str, str],
) -> str:
    # Creates and returns final message.
    formatted_stats = format_stats(players, stats)
    message = f"**Winner: ||{winner} {difference} {loser}||**\n\n"
    for player_data in formatted_stats:
        player_name = player_data[0]
        pokemons = player_data[1]
        message += f"{player_name}'s Pokemon:\n"
        poke_message = ""
        for pokemon_data in pokemons:
            poke_name = pokemon_data[0]
            kills, deaths = pokemon_data[1]
            poke_message += f"{poke_name} (Kills: {kills}, Deaths: {deaths})\n"
        message += f"||```\n{poke_message.strip()}\n```||\n"
    return message


def testget_player_names(json_data: Dict[str, List[str]]) -> Dict[str, str]:
    # Retrieves player names.
    players_list = json_data.get("players", [])
    players_dict = {}
    players_dict["p1"] = players_list[0]
    players_dict["p2"] = players_list[1]
    return players_dict


def testget_pokes(json_data: Dict[str, List[str]]) -> Dict[str, Dict[str, str]]:
    # Retrieves Pokemon names and groups them in terms of player. Each entry is a mapping from nickname to actual name.
    log = json_data.get("log", "")
    all_pokemon = {"p1": {}, "p2": {}}
    nickname_mapping = {}
    if "|poke|" in log:
        pokemon_regex = re.compile(r"\|poke\|(p\d)\|([^,|]+)")
        for match in pokemon_regex.finditer(log):
            player, pokemon = match.groups()
            pokemon = pokemon.strip()
            all_pokemon[player][pokemon] = pokemon
    print(f"all_pokemon before: {all_pokemon}")
    event_regex = re.compile(r"\|(switch|replace)\|(p\d)a: (.+?)\|([^,|]+)")
    for match in event_regex.finditer(log):
        event_type, player, nickname, pokemon = match.groups()
        pokemon = pokemon.strip()
        existing_entry = next(
            (k for k, v in all_pokemon[player].items() if v == pokemon), None
        )
        if existing_entry:
            all_pokemon[player][existing_entry] = nickname
        else:
            all_pokemon[player][nickname] = pokemon
    print(f"all_pokemon: {all_pokemon}")
    return all_pokemon


def testget_revives(json_data: Dict[str, List[str]]) -> List[Tuple[str, str]]:
    # Retrieves a list of player and Pokemon for each Pokemon that was revived.
    revives = []
    log = json_data.get("log", "")
    revive_regex = re.compile(
        r"\|p(\d)a: ([^\|]+)\|Revival Blessing[\s\S]*?\-heal\|p(\d): ([^\|\n]+)",
        re.DOTALL,
    )
    for match in revive_regex.finditer(log):
        player = f"p{match.group(3)}"
        pokemon = match.group(4).strip()
        revives.append((player, pokemon))
    return revives


def testget_winner(json_data: Dict[str, List[str]]) -> str:
    # Retrieves the winner.
    log_data = json_data.get("log", "")
    winner = re.search(r"\|win\|(.+?)\n", log_data).group(1).strip()
    return winner


def testget_loser(json_data: Dict[str, List[str]]) -> str:
    # Retrieves the losing player.
    winner = testget_winner(json_data)
    players = testget_player_names(json_data)
    for id, name in players.items():
        if name != winner:
            return name


def testget_difference(
    players: Dict[str, str], winner: str, revives: List[Tuple[str, str]]
) -> str:
    # Retrieves the point difference from winning player to losing player.
    p1_deaths = sum(pokemon["deaths"] for pokemon in stats["p1"].values())
    p2_deaths = sum(pokemon["deaths"] for pokemon in stats["p2"].values())
    for player, pokemon in revives:
        for nickname, pokemon_stats in stats[player].items():
            if pokemon_stats["nickname"] == pokemon:
                if player == "p1":
                    p1_deaths -= 1
                else:
                    p2_deaths -= 1
                break
    if winner == players["p1"]:
        difference = f"({p2_deaths - p1_deaths}-0)"
    else:
        difference = f"({p1_deaths - p2_deaths}-0)"
    return difference


def testinitialize_stats(pokemon_data: Dict[str, Dict[str, str]]) -> None:
    # Initializes stats (player, nickname, kills, deaths) for each Pokemon.
    for player, pokemon in pokemon_data.items():
        stats[player] = {}
        for nickname, actual_pokemon in pokemon.items():
            stats[player][actual_pokemon] = {
                "nickname": nickname,
                "kills": 0,
                "deaths": 0,
            }


def testprocess_stats(json_data: Dict[str, List[str]]) -> None:
    # Updates the kill and death values for each Pokemon.
    log = json_data.get("log", "")
    faint_regex = re.compile(r"\|faint\|p(\d)a: ([^\|\n]+)")
    for match in faint_regex.finditer(log):
        fainted_player, fainted_pokemon = match.groups()
        fainted_pokemon = fainted_pokemon.strip()
        event = match.start()
        player_key = f"p{fainted_player}"
        for pokemon, data in stats[player_key].items():
            if data["nickname"] == fainted_pokemon:
                data["deaths"] += 1
                break
        actions = log[:event].split("\n")[::-1]
        for action in actions:
            killer = re.search(r"\|p(\d)a: ([^\|\n]+)\|", action)
            if killer and killer.group(1) != fainted_player:
                killer_player, killer_pokemon = killer.groups()
                killer_pokemon = killer_pokemon.strip()
                player_key = f"p{killer_player}"
                kill_found = False
                for pokemon, data in stats[player_key].items():
                    if data["nickname"] == killer_pokemon:
                        data["kills"] += 1
                        kill_found = True
                        break
                if kill_found:
                    break


def testcreate_message(
    players: Dict[str, str], winner: str, loser: str, difference: str
) -> str:
    # Creates and returns final message.
    message = f"**Winner: ||{winner} {difference} {loser}||**\n\n"
    message += f"**{winner}'s Pokemon:**\n"
    winner_message = ""
    for pokemon, data in stats[
        next(key for key, value in players.items() if value == winner)
    ].items():
        kills = data["kills"]
        deaths = data["deaths"]
        winner_message += f"{pokemon} (Kills: {kills}, Deaths: {deaths})\n"
    message += f"||```\n{winner_message.strip()}\n```||\n"
    message += f"**{loser}'s Pokemon:**\n"
    loser_message = ""
    for pokemon, data in stats[
        next(key for key, value in players.items() if value == loser)
    ].items():
        kills = data["kills"]
        deaths = data["deaths"]
        loser_message += f"{pokemon} (Kills: {kills}, Deaths: {deaths})\n"
    message += f"||```\n{loser_message.strip()}\n```||\n"
    return message
