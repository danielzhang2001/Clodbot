"""
General functions in analyzing Pokemon Showdown replay links.
"""

import re
from typing import Optional, Dict, List, Tuple


def get_original_pokemon (stats: Dict[str, Dict[str, Dict[str, int]]], player_key: str, nickname: str) -> str:
    # Given a player's stats mapping and a nickname, return the original pokemon name
    for original, data in stats.get(player_key, {}).items():
        if data.get("nickname") == nickname:
            return original
    return nickname

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
        pokemon_regex = re.compile(r"\|poke\|(p\d)[ab]?\|([^,|]+)")
        for match in pokemon_regex.finditer(log):
            player, pokemon = match.groups()
            pokemon = pokemon.strip().replace("-*", "")
            all_pokemon[player][pokemon] = pokemon
    event_regex = re.compile(r"\|(switch|replace)\|(p\d)[ab]: (.+?)\|([^,|]+)")
    for match in event_regex.finditer(log):
        event_type, player, nickname, pokemon = match.groups()
        pokemon = pokemon.strip()
        nickname = nickname.strip()
        all_pokemon[player][pokemon] = nickname
        base_pokemon = re.sub(r"-.*", "", pokemon)
        if base_pokemon in all_pokemon[player] and all_pokemon[player][base_pokemon] == nickname:
            if base_pokemon != pokemon:
                del all_pokemon[player][base_pokemon]
    transform_regex = re.compile(
        r"\|detailschange\|(p\d)[ab]: (.+?)\|([^,|]+)-(Mega|Terastal|Hero)"
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
        r"\|p(\d)[ab]: ([^\|]+)\|Revival Blessing[\s\S]*?\-heal\|p(\d)[ab]: ([^\|\n]+)",
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


def get_difference(players: Dict[str, str], winner: str, revives: List[Tuple[str, str]], stats: Dict[str, Dict[str, Dict[str, int]]]) -> str:
    # Retrieves the point difference from winning player to losing player.
    p1_deaths = sum(pokemon["deaths"] for pokemon in stats.get("p1", {}).values())
    p2_deaths = sum(pokemon["deaths"] for pokemon in stats.get("p2", {}).values())
    for player, pokemon in revives:
        for _, pokemon_stats in stats.get(player, {}).items():
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

def initialize_stats(pokemon_data: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, Dict[str, int]]]:
    # Initializes stats (player, nickname, kills, deaths) for each Pokemon.
    stats: Dict[str, Dict[str, Dict[str, int]]] = {}
    for player, pokemon in pokemon_data.items():
        stats[player] = {}
        for actual_pokemon, nickname in pokemon.items():
            stats[player][actual_pokemon] = {"nickname": nickname, "kills": 0, "deaths": 0}
    return stats

def process_stats(json_data: Dict[str, List[str]], stats: Dict[str, Dict[str, Dict[str, int]]], passive_kills: Optional[List[Tuple[str, str, str, str, str]]]) -> None:
    # Updates the kill and death values for each Pokemon.
    log = json_data.get("log", "")
    faint_regex = re.compile(r"\|faint\|p(\d)[ab]: ([^\|\n]+)")
    sandstorm_regex = re.compile(r"\[from\] Sandstorm\n\|faint\|")
    poison_regex = re.compile(r"\[from\] psn\n\|faint\|")
    burn_regex = re.compile(r"\[from\] brn\n\|faint\|")
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
        if poison_regex.search(segment):
            process_poison(fainted_player, fainted_pokemon, actions, stats, passive_kills)
        elif burn_regex.search(segment):
            process_burn(fainted_player, fainted_pokemon, actions, stats, passive_kills)
        elif rocks_regex.search(segment):
            process_rocks(fainted_player, fainted_pokemon, actions, stats, passive_kills)
        elif spikes_regex.search(segment):
            process_spikes(fainted_player, fainted_pokemon, actions, stats, passive_kills)
        elif seed_regex.search(segment):
            process_seed(fainted_player, fainted_pokemon, actions, stats, passive_kills)
        elif sandstorm_regex.search(segment):
            process_sandstorm(fainted_player, fainted_pokemon, actions, stats, passive_kills)
        else:
            process_direct(fainted_player, fainted_pokemon, actions, stats)


def process_sandstorm(
    fainted_player: str,
    fainted_pokemon: str,
    actions: List[str], 
    stats: Dict[str, Dict[str, Dict[str, int]]],
    passive_kills: Optional[List[Tuple[str, str, str]]] = None
    ):
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
                if passive_kills is not None:
                    victim = get_original_pokemon(stats, f"p{fainted_player}", fainted_pokemon)
                    killer = get_original_pokemon(stats, sandstorm_player, sandstorm_starter)
                    passive_kills.append((victim, killer, "Sandstorm", f"p{fainted_player}", sandstorm_player))
                break


def process_poison(
    fainted_player: str,
    fainted_pokemon: str,
    actions: List[str],
    stats: Dict[str, Dict[str, Dict[str, int]]],
    passive_kills: Optional[List[Tuple[str, str, str]]] = None
):
    # Processes kills from toxic or poison.
    poison_starter = None
    poison_player = None
    poison_found = False
    for action in actions:
        for toxic_move in ["Toxic", "Malignant Chain", "Toxic Spikes", "Toxic Chain"]:
            if re.search(rf"\|p(\d)[ab]: ([^\|\n]+)\|{toxic_move}\|p(\d)[ab]: " + re.escape(fainted_pokemon), action):
                if "-status" in actions[actions.index(action) - 1] and "tox" in actions[actions.index(action) - 1]:
                    poison_match = re.search(rf"\|p(\d)[ab]: ([^\|\n]+)\|{toxic_move}\|p(\d)[ab]: ([^\|\n]+)", action)
                    if poison_match:
                        poison_player, poison_pokemon, _, poisoned_pokemon = poison_match.groups()
                        if poisoned_pokemon.strip() == fainted_pokemon:
                            poison_starter = poison_pokemon.strip()
                            poison_player = f"p{poison_player}"
                            if poison_player != f"p{fainted_player}":
                                poison_found = True
                                break
            elif re.search(
                r"\|-status\|p(\d)[ab]: "
                + re.escape(fainted_pokemon)
                + r"\|tox\|\[from\] ability: Toxic Chain\|\[of\] p(\d)[ab]: ([^\|\n]+)",
                action,
            ):
                chain_match = re.search(
                    r"\|-status\|p(\d)[ab]: "
                    + re.escape(fainted_pokemon)
                    + r"\|tox\|\[from\] ability: Toxic Chain\|\[of\] p(\d)[ab]: ([^\|\n]+)",
                    action,
                )
                if chain_match:
                    _, poison_player, poison_starter = chain_match.groups()
                    poison_starter = poison_starter.strip()
                    poison_player = f"p{poison_player}"
                    if poison_player != f"p{fainted_player}":
                        poison_found = True
                        break

        for poison_move in [
            "Sludge", "Sludge Bomb", "Sludge Wave", "Gunk Shot", "Smog", "Poison Fang",
            "Poison Jab", "Poison Sting", "Poison Tail", "Poison Gas", "Poison Powder",
            "Fling", "Cross Poison", "Toxic Thread", "Twineedle", "Barb Barrage",
            "Shell Side Arm", "Mortal Spin", "Dire Claw", "Secret Power",
            "G-Max Befuddle", "G-Max Malodor", "G-Max Stun Shock", "Poison Point"
        ]:
            pattern = rf"\|p(\d)[ab]: ([^\|\n]+)\|{poison_move}\|p(\d)[ab]: " + re.escape(fainted_pokemon)
            if re.search(pattern, action):
                prev_action = actions[actions.index(action) - 2]
                if "-status" in prev_action and "psn" in prev_action:
                    match = re.search(rf"\|p(\d)[ab]: ([^\|\n]+)\|{poison_move}\|p(\d)[ab]: ([^\|\n]+)", action)
                    if match:
                        attacker_player, attacker_pokemon, target_player, target_pokemon = match.groups()
                        if target_pokemon.strip() == fainted_pokemon:
                            poison_starter = attacker_pokemon.strip()
                            poison_player = f"p{attacker_player}"
                            if poison_player != f"p{target_player}":
                                poison_found = True
                                break
            elif re.search(
                r"\|-status\|p(\d)[ab]: "
                + re.escape(fainted_pokemon)
                + r"\|psn\|\[from\] ability: Poison Point\|\[of\] p(\d)[ab]: ([^\|\n]+)",
                action,
            ):
                point_match = re.search(
                    r"\|-status\|p(\d)[ab]: "
                    + re.escape(fainted_pokemon)
                    + r"\|psn\|\[from\] ability: Poison Point\|\[of\] p(\d)[ab]: ([^\|\n]+)",
                    action,
                )
                if point_match:
                    _, poison_player, poison_starter = point_match.groups()
                    poison_starter = poison_starter.strip()
                    poison_player = f"p{poison_player}"
                    if poison_player != f"p{fainted_player}":
                        poison_found = True
                        break
        for ability in ["Psycho Shift", "Synchronize"]:
            if re.search(
                rf"\|p(\d)[ab]: ([^\|\n]+)\|ability: {ability}\n|-status\|p(\d)[ab]: " + re.escape(fainted_pokemon) + r"\|(tox|psn)",
                action,
            ):
                if "-status" in action and ("tox" in action or "psn" in action):
                    full_action = actions[actions.index(action) + 1] + "\n" + action
                    ability_match = re.search(
                        rf"\|p(\d)[ab]: ([^\|\n]+)\|ability: {ability}\n\|-status\|p(\d)[ab]: ([^\|\n]+)",
                        full_action,
                    )
                    if ability_match:
                        ability_player, ability_pokemon, _, target_pokemon = ability_match.groups()
                        if target_pokemon.strip() == fainted_pokemon:
                            poison_starter = ability_pokemon.strip()
                            poison_player = f"p{ability_player}"
                            if poison_player != f"p{fainted_player}":
                                poison_found = True
                                break
    if poison_found and poison_starter:
        for pokemon, data in stats[poison_player].items():
            if data["nickname"] == poison_starter:
                data["kills"] += 1
                if passive_kills is not None:
                    victim = get_original_pokemon(stats, f"p{fainted_player}", fainted_pokemon)
                    killer = get_original_pokemon(stats, poison_player, poison_starter)
                    passive_kills.append((victim, killer, "Poison", f"p{fainted_player}", poison_player))
                break

def process_burn(
    fainted_player: str,
    fainted_pokemon: str,
    actions: List[str],
    stats: Dict[str, Dict[str, Dict[str, int]]],
    passive_kills: Optional[List[Tuple[str, str, str]]] = None
):
    # Processes kills from burn.
    burn_starter = None
    burn_player = None
    burn_found = False
    for action in actions:
        for burn_move in [
            "Will-O-Wisp", "Lava Plume", "Flamethrower", "Fire Blast", "Flare Blitz",
            "Heat Wave", "Scald", "Scorching Sands", "Blaze Kick", "Fire Fang", 
            "Fire Punch", "Ember", "Flame Wheel", "Burning Jealousy", "Inferno", 
            "Pyro Ball", "Infernal Parade", "Blue Flare", "Searing Shot", 
            "Steam Eruption", "Tri Attack", "Secret Power", "Fling", 
            "Matcha Gotcha", "Sacred Fire", "Sandsear Storm"
        ]:
            pattern = rf"\|p(\d)[ab]: ([^\|\n]+)\|{burn_move}\|p(\d)[ab]: " + re.escape(fainted_pokemon)
            if re.search(pattern, action):
                prev_action = actions[actions.index(action) - 2]
                if "-status" in prev_action and "brn" in prev_action:
                    match = re.search(rf"\|p(\d)[ab]: ([^\|\n]+)\|{burn_move}\|p(\d)[ab]: ([^\|\n]+)", action)
                    if match:
                        attacker_player, attacker_pokemon, target_player, target_pokemon = match.groups()
                        if target_pokemon.strip() == fainted_pokemon:
                            burn_starter = attacker_pokemon.strip()
                            burn_player = f"p{attacker_player}"
                            if burn_player != f"p{target_player}":
                                burn_found = True
                                break
            elif re.search(
                r"\|-status\|p(\d)[ab]: "
                + re.escape(fainted_pokemon)
                + r"\|brn\|\[from\] ability: Flame Body\|\[of\] p(\d)[ab]: ([^\|\n]+)",
                action,
            ):
                body_match = re.search(
                    r"\|-status\|p(\d)[ab]: "
                    + re.escape(fainted_pokemon)
                    + r"\|brn\|\[from\] ability: Flame Body\|\[of\] p(\d)[ab]: ([^\|\n]+)",
                    action,
                )
                if body_match:
                    _, burn_player, burn_starter = body_match.groups()
                    burn_starter = burn_starter.strip()
                    burn_player = f"p{burn_player}"
                    if burn_player != f"p{fainted_player}":
                        burn_found = True
                        break
        for ability in ["Synchronize"]:
            if re.search(
                rf"\|p(\d)[ab]: ([^\|\n]+)\|ability: {ability}\n|-status\|p(\d)[ab]: " + re.escape(fainted_pokemon) + r"\|(brn)",
                action,
            ):
                if "-status" in action and "brn" in action:
                    full_action = actions[actions.index(action) + 1] + "\n" + action
                    ability_match = re.search(
                        rf"\|p(\d)[ab]: ([^\|\n]+)\|ability: {ability}\n\|-status\|p(\d)[ab]: ([^\|\n]+)",
                        full_action,
                    )
                    if ability_match:
                        ability_player, ability_pokemon, _, target_pokemon = ability_match.groups()
                        if target_pokemon.strip() == fainted_pokemon:
                            burn_starter = ability_pokemon.strip()
                            burn_player = f"p{ability_player}"
                            if burn_player != f"p{fainted_player}":
                                burn_found = True
                                break
    if burn_found and burn_starter:
        for pokemon, data in stats[burn_player].items():
            if data["nickname"] == burn_starter:
                data["kills"] += 1
                if passive_kills is not None:
                    victim = get_original_pokemon(stats, f"p{fainted_player}", fainted_pokemon)
                    killer = get_original_pokemon(stats, burn_player, burn_starter)
                    passive_kills.append((victim, killer, "Burn", f"p{fainted_player}", burn_player))
                break

def process_spikes(
    fainted_player: str,
    fainted_pokemon: str,
    actions: List[str],
    stats: Dict[str, Dict[str, Dict[str, int]]],
    passive_kills: Optional[List[Tuple[str, str, str]]] = None
):
    # Processes kills from spikes.
    spikes_starter = None
    spikes_player = None
    spikes_found = False
    for action in actions:
        spikes_match = re.search(
            r"\|p(\d)[ab]: ([^\|\n]+)\|(Spikes|Ceaseless Edge)\|", action
        )
        if spikes_match:
            spikes_player, spikes_pokemon, *_ = spikes_match.groups()
            spikes_starter = spikes_pokemon.strip()
            spikes_player = f"p{spikes_player}"
            if spikes_player != f"p{fainted_player}":
                spikes_found = True
                break
    if spikes_found and spikes_starter:
        for pokemon, data in stats[spikes_player].items():
            if data["nickname"] == spikes_starter:
                data["kills"] += 1
                if passive_kills is not None:
                    victim = get_original_pokemon(stats, f"p{fainted_player}", fainted_pokemon)
                    killer = get_original_pokemon(stats, spikes_player, spikes_starter)
                    passive_kills.append((victim, killer, "Spikes", f"p{fainted_player}", spikes_player))
                break

def process_rocks(
    fainted_player: str,
    fainted_pokemon: str,
    actions: List[str],
    stats: Dict[str, Dict[str, Dict[str, int]]],
    passive_kills: Optional[List[Tuple[str, str, str]]] = None
):
    # Processes kills from Stealth Rocks.
    rocks_starter = None
    rocks_player = None
    rocks_found = False
    for action in actions:
        rocks_match = re.search(r"\|p(\d)[ab]: ([^\|\n]+)\|Stealth Rock\|", action)
        if rocks_match:
            rocks_player, rocks_pokemon = rocks_match.groups()
            rocks_starter = rocks_pokemon.strip()
            rocks_player = f"p{rocks_player}"
            if rocks_player != f"p{fainted_player}":
                rocks_found = True
                break
    if rocks_found and rocks_starter:
        for pokemon, data in stats[rocks_player].items():
            if data["nickname"] == rocks_starter:
                data["kills"] += 1
                if passive_kills is not None:
                    victim = get_original_pokemon(stats, f"p{fainted_player}", fainted_pokemon)
                    killer = get_original_pokemon(stats, rocks_player, rocks_starter)
                    passive_kills.append((victim, killer, "Stealth Rock", f"p{fainted_player}", rocks_player))
                break

def process_seed(
    fainted_player: str,
    fainted_pokemon: str,
    actions: List[str],
    stats: Dict[str, Dict[str, Dict[str, int]]],
    passive_kills: Optional[List[Tuple[str, str, str]]] = None
):
    leech_starter = None
    leech_player = None
    for action in actions:
        leech_match = re.search(
            r"\|[^\|]+\|\[from\] Leech Seed\|\[of\] p(\d)[ab]: ([^\|\n]+)",
            action,
        )
        if leech_match:
            leech_player, leech_pokemon = leech_match.groups()
            leech_starter = leech_pokemon.strip()
            leech_player = f"p{leech_player}"
            if leech_player != f"p{fainted_player}":
                break
    if leech_starter and leech_player:
        for pokemon, data in stats[leech_player].items():
            if data["nickname"] == leech_starter:
                data["kills"] += 1
                if passive_kills is not None:
                    victim = get_original_pokemon(stats, f"p{fainted_player}", fainted_pokemon)
                    killer = get_original_pokemon(stats, leech_player, leech_starter)
                    passive_kills.append((victim, killer, "Leech Seed", f"p{fainted_player}", leech_player))
                break

def process_direct(
    fainted_player: str,
    fainted_pokemon: str,
    actions: List[str],
    stats: Dict[str, Dict[str, Dict[str, int]]],
):
    # Processes normal kills that result in one Pokemon directly killing another.
    for action in actions:
        killer = re.search(r"^\|move\|p(\d)[ab]: ([^|]+)\|", action)
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
    pokemon = get_replay_pokemon(json_data)
    stats = initialize_stats(pokemon)
    process_stats(json_data, stats)
    return stats

def get_stats_with_passives(json_data: Dict[str, List[str]]
    ) -> Tuple[Dict[str, Dict[str, Dict[str, int]]], List[Tuple[str, str, str, str, str]]]:
    # Returns the updated stats and a list of passive KOs.
    pokemon = get_replay_pokemon(json_data)
    stats = initialize_stats(pokemon)
    passive_kills: List[Tuple[str, str, str, str, str]] = []
    process_stats(json_data, stats, passive_kills)
    return stats, passive_kills

def create_message(
        players: Dict[str, str], 
        winner: str, 
        loser: str, 
        difference: str, 
        stats: Dict[str, Dict[str, Dict[str, int]]],
        passive_kills: Optional[List[Tuple[str, str, str, str, str]]] = None
) -> str:
    # Creates and returns the final message.
    winner_key = next(key for key, value in players.items() if value == winner)
    loser_key  = next(key for key, value in players.items() if value == loser)
    message = f"**OUTCOME: ||{winner} {difference} {loser}||**\n\n"
    message += f"**{winner}'s Pokemon:**\n"
    winner_message = ""
    for pokemon, data in stats[winner_key].items():
        kills = data["kills"]
        deaths = data["deaths"]
        winner_message += f"{pokemon} (Kills: {kills}, Deaths: {deaths})\n"
    message += f"||```\n{winner_message.strip()}\n```||\n"
    message += f"**{loser}'s Pokemon:**\n"
    loser_message = ""
    for pokemon, data in stats[loser_key].items():
        kills = data["kills"]
        deaths = data["deaths"]
        loser_message += f"{pokemon} (Kills: {kills}, Deaths: {deaths})\n"
    message += f"||```\n{loser_message.strip()}\n```||\n"
    if passive_kills:
        passive_lines = []
        for entry in passive_kills:
            if len(entry) == 5:
                victim, killer, cause, v_key, k_key = entry
                victim_name = players.get(v_key, v_key)
                killer_name = players.get(k_key, k_key)
                passive_lines.append(f"[{victim_name}] {victim} died from [{killer_name}] {killer}'s {cause}")
            else:
                victim, killer, cause = entry
                passive_lines.append(f"{victim} died from {killer}'s {cause}")
        message += f"**Passive KOs:**\n"
        message += f"||```\n" + "\n".join(passive_lines) + "\n```||\n"
    return message
