"""
General functions in analyzing Pokemon Showdown replay links.
"""

import re
import json
from typing import Dict, List, Tuple

stats = {}


def get_replay_players(json_data: Dict[str, List[str]]) -> Dict[str, str]:
    # Retrieves player names.
    players_list = json_data.get("players", [])
    players_dict = {}
    players_dict["p1"] = players_list[0]
    players_dict["p2"] = players_list[1]
    return players_dict


def get_replay_pokemon(json_data: Dict[str, List[str]]) -> Dict[str, Dict[str, str]]:
    # Retrieves Pokemon names and groups them in terms of player. Each entry is a mapping from nickname to actual name.
    log = json_data.get("log", "")
    all_pokemon = {"p1": {}, "p2": {}}
    if "|poke|" in log:
        pokemon_regex = re.compile(r"\|poke\|(p\d)\|([^,|]+)")
        for match in pokemon_regex.finditer(log):
            player, pokemon = match.groups()
            pokemon = pokemon.strip().replace("-*", "")
            all_pokemon[player][pokemon] = pokemon
    event_regex = re.compile(r"\|(switch|replace)\|(p\d)a: (.+?)\|([^,|]+)")
    for match in event_regex.finditer(log):
        event_type, player, nickname, pokemon = match.groups()
        pokemon = pokemon.strip()
        nickname = nickname.strip()
        all_pokemon[player][pokemon] = nickname
    transform_regex = re.compile(
        r"\|detailschange\|(p\d)a: (.+?)\|([^,|]+)-(Mega|Terastal|Hero)"
    )
    for match in transform_regex.finditer(log):
        player, nickname, base_pokemon, form = match.groups()
        transform_pokemon = base_pokemon + "-" + form
        if (
            base_pokemon in all_pokemon[player]
            and all_pokemon[player][base_pokemon] == nickname
        ):
            del all_pokemon[player][base_pokemon]
        all_pokemon[player][transform_pokemon] = nickname
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
    players = get_replay_players(json_data)
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


def process_sandstorm(actions: List[str], stats: Dict[str, Dict[str, Dict[str, int]]]):
    # Processes kills from sandstorm.
    sandstorm_starter = None
    sandstorm_player = None
    for action in actions:
        sandstorm_match = re.search(
            r"\|-weather\|Sandstorm\|\[from\] ability: ([^\|]+)\|\[of\] (p\d)a: ([^\|]+)",
            action,
        )
        if sandstorm_match:
            _, sandstorm_player, sandstorm_pokemon = sandstorm_match.groups()
            sandstorm_starter = sandstorm_pokemon.strip()
            break

    if sandstorm_starter:
        for pokemon, data in stats[sandstorm_player].items():
            if data["nickname"] == sandstorm_starter:
                data["kills"] += 1
                break


def process_poison(
    fainted_pokemon: str,
    actions: List[str],
    stats: Dict[str, Dict[str, Dict[str, int]]],
):
    # Processes kills from toxic or poison.
    print("processing poison!")
    print(f"fainted pokemon: {fainted_pokemon}")
    poison_starter = None
    poison_player = None
    toxic_found = False
    for action in actions:
        print(f"Processing action: {action}")

        # Check for Toxic Chain ability
        regex_pattern = (
            r"\|-status\|p(\d)a: "
            + re.escape(fainted_pokemon)
            + r"\|tox\|[from] ability: Toxic Chain\|[of] p(\d)a: ([^\|\n]+)",
            action,
        )
        print(f"Regex pattern: {regex_pattern}")
        print(f"action: {action}")
        if re.search(
            r"\|p(\d)a: ([^\|\n]+)\|Toxic\|p(\d)a: " + re.escape(fainted_pokemon),
            action,
        ):
            if "|-status|" in actions[actions.index(action) - 1]:
                poison_match = re.search(
                    r"\|p(\d)a: ([^\|\n]+)\|Toxic\|p(\d)a: ([^\|\n]+)", action
                )
                if poison_match:
                    poison_player, poison_pokemon, _, poisoned_pokemon = (
                        poison_match.groups()
                    )
                    if poisoned_pokemon.strip() == fainted_pokemon:
                        poison_starter = poison_pokemon.strip()
                        poison_player = f"p{poison_player}"
                        toxic_found = True
                        break
            elif "|-fail|" in actions[actions.index(action) + 1]:
                continue
        elif re.search(
            r"\|p(\d)a: ([^\|\n]+)\|Malignant Chain\|p(\d)a: "
            + re.escape(fainted_pokemon),
            action,
        ):
            if (
                "-status" in actions[actions.index(action) - 2]
                and "tox" in actions[actions.index(action) - 2]
            ):
                malignant_match = re.search(
                    r"\|p(\d)a: ([^\|\n]+)\|Malignant Chain\|p(\d)a: ([^\|\n]+)", action
                )
                if malignant_match:
                    malignant_player, malignant_pokemon, _, target_pokemon = (
                        malignant_match.groups()
                    )
                    if target_pokemon.strip() == fainted_pokemon:
                        poison_starter = malignant_pokemon.strip()
                        poison_player = f"p{malignant_player}"
                        toxic_found = True
                        break
        elif re.search(r"\|p(\d)a: ([^\|\n]+)\|Toxic Spikes\|", action):
            tspikes_match = re.search(r"\|p(\d)a: ([^\|\n]+)\|Toxic Spikes\|", action)
            if tspikes_match:
                tspikes_player, tspikes_pokemon = tspikes_match.groups()
                poison_starter = tspikes_pokemon.strip()
                poison_player = f"p{tspikes_player}"
                toxic_found = True
                break
        elif re.search(
            r"\|-status\|p(\d)a: "
            + re.escape(fainted_pokemon)
            + r"\|tox\|[from] ability: Toxic Chain\|[of] p(\d)a: ([^\|\n]+)",
            action,
        ):
            print("in chain!")
            chain_match = re.search(
                r"\|-status\|p(\d)a: "
                + re.escape(fainted_pokemon)
                + r"\|tox\|[from] ability: Toxic Chain\|[of] p(\d)a: ([^\|\n]+)",
                action,
            )
            if chain_match:
                _, poison_player, poison_starter = chain_match.groups()
                poison_starter = poison_starter.strip()
                poison_player = f"p{poison_player}"
                toxic_found = True
                break
    if toxic_found and poison_starter:
        for pokemon, data in stats[poison_player].items():
            if data["nickname"] == poison_starter:
                data["kills"] += 1
                break


def process_spikes(
    fainted_pokemon: str,
    actions: List[str],
    stats: Dict[str, Dict[str, Dict[str, int]]],
):
    # Processes kills from spikes.
    spikes_starter = None
    spikes_player = None
    spikes_found = False
    for action in actions:
        spikes_match = re.search(
            r"\|p(\d)a: ([^\|\n]+)\|(Spikes|Ceaseless Edge)\|", action
        )
        if spikes_match:
            spikes_player, spikes_pokemon = spikes_match.groups()
            spikes_starter = spikes_pokemon.strip()
            spikes_player = f"p{spikes_player}"
            spikes_found = True
            break

    if spikes_found and spikes_starter:
        for pokemon, data in stats[spikes_player].items():
            if data["nickname"] == spikes_starter:
                data["kills"] += 1
                break


def process_rocks(
    fainted_pokemon: str,
    actions: List[str],
    stats: Dict[str, Dict[str, Dict[str, int]]],
):
    # Processes kills from Stealth Rocks.
    rocks_starter = None
    rocks_player = None
    rocks_found = False
    for action in actions:
        rocks_match = re.search(r"\|p(\d)a: ([^\|\n]+)\|Stealth Rock\|", action)
        if rocks_match:
            rocks_player, rocks_pokemon = rocks_match.groups()
            rocks_starter = rocks_pokemon.strip()
            rocks_player = f"p{rocks_player}"
            rocks_found = True
            break

    if rocks_found and rocks_starter:
        for pokemon, data in stats[rocks_player].items():
            if data["nickname"] == rocks_starter:
                data["kills"] += 1
                break


def process_seed(
    fainted_pokemon: str,
    actions: List[str],
    stats: Dict[str, Dict[str, Dict[str, int]]],
):
    leech_starter = None
    leech_player = None
    for action in actions:
        leech_match = re.search(
            r"\|[^\|]+\|\[from\] Leech Seed\|\[of\] (p\d)a: ([^\|\n]+)",
            action,
        )
        if leech_match:
            leech_player, leech_pokemon = leech_match.groups()
            leech_starter = leech_pokemon.strip()
            leech_player = f"p{leech_player}"
            break

    if leech_starter and leech_player:
        for pokemon, data in stats[leech_player].items():
            if data["nickname"] == leech_starter:
                data["kills"] += 1
                break


def process_direct(
    fainted_player: str,
    fainted_pokemon: str,
    actions: List[str],
    stats: Dict[str, Dict[str, Dict[str, int]]],
):
    # Processes normal kills that result in one Pokemon directly killing another.
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


def process_stats(json_data: Dict[str, List[str]]) -> None:
    # Updates the kill and death values for each Pokemon.
    log = json_data.get("log", "")
    faint_regex = re.compile(r"\|faint\|p(\d)a: ([^\|\n]+)")
    sandstorm_regex = re.compile(r"\[from\] Sandstorm\n\|faint\|")
    poison_regex = re.compile(r"\[from\] psn\n\|faint\|")
    spikes_regex = re.compile(r"\[from\] Spikes\n\|faint\|")
    rocks_regex = re.compile(r"\[from\] Stealth Rock\n\|faint\|")
    seed_regex = re.compile(r"\[from\] Leech Seed\|\[of\]")
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
        segment = log[event - 80 : event + 30]
        if sandstorm_regex.search(segment):
            process_sandstorm(actions, stats)
        elif poison_regex.search(segment):
            process_poison(fainted_pokemon, actions, stats)
        elif spikes_regex.search(segment):
            process_spikes(fainted_pokemon, actions, stats)
        elif rocks_regex.search(segment):
            process_rocks(fainted_pokemon, actions, stats)
        elif seed_regex.search(segment):
            process_seed(fainted_pokemon, actions, stats)
        else:
            process_direct(fainted_player, fainted_pokemon, actions, stats)


def get_stats(json_data: Dict[str, List[str]]) -> Dict[str, Dict[str, Dict[str, int]]]:
    # Returns the updated stats.
    pokemon = get_replay_pokemon(json_data)
    initialize_stats(pokemon)
    process_stats(json_data)
    return stats


def create_message(
    players: Dict[str, str], winner: str, loser: str, difference: str
) -> str:
    # Creates and returns the final message.
    message = f"**OUTCOME: ||{winner} {difference} {loser}||**\n\n"
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
