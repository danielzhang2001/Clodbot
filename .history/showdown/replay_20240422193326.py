"""
General functions in analyzing Pokemon Showdown replay links.
"""

import re
import json
from typing import Dict, List, Tuple

stats = {}


def get_players(json_data: Dict[str, List[str]]) -> Dict[str, str]:
    # Retrieves player names.
    print("START!")
    players_list = json_data.get("players", [])
    players_dict = {}
    players_dict["p1"] = players_list[0]
    players_dict["p2"] = players_list[1]
    return players_dict


def get_pokemon(json_data: Dict[str, List[str]]) -> Dict[str, Dict[str, str]]:
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
    event_regex = re.compile(r"\|(switch|replace)\|(p\d)a: (.+?)\|([^,|]+)")
    for match in event_regex.finditer(log):
        event_type, player, nickname, pokemon = match.groups()
        pokemon = pokemon.strip()
        all_pokemon[player][pokemon] = nickname
    return all_pokemon


def get_revives(json_data: Dict[str, List[str]]) -> List[Tuple[str, str]]:
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


def get_winner(json_data: Dict[str, List[str]]) -> str:
    # Retrieves the winner.
    log_data = json_data.get("log", "")
    winner = re.search(r"\|win\|(.+?)\n", log_data).group(1).strip()
    return winner


def get_loser(json_data: Dict[str, List[str]]) -> str:
    # Retrieves the losing player.
    winner = get_winner(json_data)
    players = get_players(json_data)
    for id, name in players.items():
        if name != winner:
            return name


def get_difference(
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


def initialize_stats(pokemon_data: Dict[str, Dict[str, str]]) -> None:
    # Initializes stats (player, nickname, kills, deaths) for each Pokemon.
    for player, pokemon in pokemon_data.items():
        stats[player] = {}
        for actual_pokemon, nickname in pokemon.items():
            stats[player][actual_pokemon] = {
                "nickname": nickname,
                "kills": 0,
                "deaths": 0,
            }


def process_stats(json_data: Dict[str, List[str]]) -> None:
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


def get_stats(json_data: Dict[str, List[str]]) -> Dict[str, Dict[str, Dict[str, int]]]:
    # Returns the updated stats.
    pokemon = get_pokemon(json_data)
    initialize_stats(pokemon)
    process_stats(json_data)
    return stats


def create_message(
    players: Dict[str, str], winner: str, loser: str, difference: str
) -> str:
    # Creates and returns the final message.
    message = f"**Outcome: ||{winner} {difference} {loser}||**\n\n"
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
