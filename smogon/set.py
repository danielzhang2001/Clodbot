"""
General functions in getting Pokemon Smogon sets.
"""

import aiohttp
import random
import discord
from discord.ui import Button, View
from discord.ext import commands
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, List, Tuple
from uuid import uuid4
from errors import *

selected_states = {}
selected_sets = {}


def get_gen_dict() -> Dict[str, str]:
    # Returns generation dictionary.
    return {
        "gen1": "rb",
        "gen2": "gs",
        "gen3": "rs",
        "gen4": "dp",
        "gen5": "bw",
        "gen6": "xy",
        "gen7": "sm",
        "gen8": "ss",
        "gen9": "sv",
    }


async def get_latest_gen(pokemon: str) -> Optional[str]:
    # Returns the latest eligible generation for the given Pokemon.
    gen_dict = get_gen_dict()
    generations = list(gen_dict.keys())[::-1]
    async with aiohttp.ClientSession() as session:
        for gen_key in generations:
            url = f"https://pkmn.github.io/smogon/data/sets/{gen_key}.json"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if pokemon.lower() in (p.lower() for p in data):
                        return gen_key
    return None


async def get_random_gen(pokemon: str) -> Optional[str]:
    # Returns a random eligible gen using the Smogon API given a Pokemon.
    gen_dict = get_gen_dict()
    generations = list(gen_dict.keys())
    random.shuffle(generations)
    async with aiohttp.ClientSession() as session:
        for gen_key in generations:
            url = f"https://pkmn.github.io/smogon/data/sets/{gen_key}.json"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if pokemon.lower() in (p.lower() for p in data):
                        return gen_key
    return None


async def get_first_format(pokemon: str, generation: str) -> Optional[str]:
    # Returns the first format given the Pokemon and Generation.
    url = f"https://pkmn.github.io/smogon/data/sets/{generation}.json"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if pokemon.lower() in (p.lower() for p in data):
                    pokemon_key = next(p for p in data if p.lower() == pokemon.lower())
                    pokemon_data = data[pokemon_key]
                    first_format = next(iter(pokemon_data), None)
                    return first_format
    return None


async def get_random_format(pokemon: str, generation: str) -> Optional[str]:
    # Returns a random eligible format using the Smogon API given a Pokemon and Generation.
    url = f"https://pkmn.github.io/smogon/data/sets/{generation}.json"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if pokemon.lower() in (p.lower() for p in data):
                    pokemon_key = next(p for p in data if p.lower() == pokemon.lower())
                    pokemon_data = data[pokemon_key]
                    formats = list(pokemon_data.keys())
                    if formats:
                        return random.choice(formats)
    return None


async def get_set_names(
    pokemon: str, generation: Optional[str] = None, format: Optional[str] = None
) -> Optional[List[str]]:
    # Returns all set names associated with the Pokemon, Generation and Format provided. If no Generation, assumed to be latest one, and if no Format, assumed to be first one.
    pokemon = format_pokemon(pokemon)
    if not generation:
        generation = await get_latest_gen(pokemon)
        if generation is None:
            return None
    url = f"https://pkmn.github.io/smogon/data/sets/{generation}.json"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if pokemon.lower() in (p.lower() for p in data):
                    pokemon_key = next(p for p in data if p.lower() == pokemon.lower())
                    pokemon_data = data[pokemon_key]
                    if not format:
                        format = await get_first_format(pokemon, generation)
                    if format and format in pokemon_data:
                        format_data = pokemon_data[format]
                        set_names = list(format_data.keys())
                        return set_names
    return None


async def get_random_set(pokemon: str, generation: str, format: str) -> Optional[str]:
    # Returns a random eligible set name given a Pokemon, Generation, and Format.
    url = f"https://pkmn.github.io/smogon/data/sets/{generation}.json"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                if pokemon.lower() in (p.lower() for p in data):
                    pokemon_key = next(p for p in data if p.lower() == pokemon.lower())
                    pokemon_data = data[pokemon_key]
                    if format in pokemon_data:
                        format_data = pokemon_data[format]
                        set_names = list(format_data.keys())
                        if set_names:
                            return random.choice(set_names)
    return None


def get_prompt(requests: List[Dict[str, Optional[str]]]) -> str:
    # Returns the initial prompt for the Pokemon(s) specified.
    prompt = "Please select a set type for "
    if len(requests) > 1:
        prompt += "the following Pokemon"
    else:
        request = requests[0]
        pokemon = request["pokemon"].upper()
        generation = (
            request.get("generation").upper() if request.get("generation") else None
        )
        format = request.get("format").upper() if request.get("format") else None
        prompt += f"**{pokemon}{f' {generation}' if generation else ''}{f' {format}' if format else ''}**"
    prompt += ":"
    return prompt


def get_view(
    prompt_key: str,
    message_key: str,
    request: Dict[str, Optional[str]],
    set_names: List[str],
    request_count: int,
) -> View:
    # Returns the view with a set of buttons for each Pokemon request.
    view = View()
    pokemon, generation, format = (
        request["pokemon"],
        request.get("generation", "none"),
        request.get("format", "none"),
    )
    if request_count > 1:
        view.add_item(
            Button(
                label=" ".join(
                    [pokemon.upper()]
                    + [
                        generation.upper()
                        for generation in [request.get("generation") or "none"]
                        if generation != "none"
                    ]
                    + [
                        format.upper()
                        for format in [request.get("format") or "none"]
                        if format != "none"
                    ]
                )
                + ":",
                style=discord.ButtonStyle.primary,
                disabled=True,
            )
        )
    for name in set_names:
        button_key = uuid4().hex[:5]
        button_id = f"{prompt_key}_{message_key}_{button_key}_{pokemon}_{generation or 'none'}_{format or 'none'}_{name}_{request_count}".replace(
            " ", ""
        )
        view.add_item(Button(label=name, custom_id=button_id))
    return view


def format_pokemon(pokemon: str) -> str:
    # Returns the pokemon name with proper case formatting.
    if "-" in pokemon:
        pokemon = pokemon.replace("-", " ")
    parts = [part.capitalize() for part in pokemon.split(" ")]
    return " ".join(parts)


def format_set(pokemon: str, moveset: dict) -> str:
    # Returns the formatted set data from the pokemon and moveset information given.
    stats = {
        "hp": "HP",
        "atk": "Atk",
        "def": "Def",
        "spa": "SpA",
        "spd": "SpD",
        "spe": "Spe",
    }
    pokemon_str = format_pokemon(pokemon)
    item = moveset.get("item", "")
    ability = moveset.get("ability", "")
    evs = moveset.get("evs", {})
    ivs = moveset.get("ivs", {})
    tera = moveset.get("teratypes", "")
    nature = moveset.get("nature", "")
    moves = []
    if isinstance(item, list):
        item_str = f" @ {random.choice(item)}" if item else ""
    else:
        item_str = f" @ {item}" if item else ""
    if isinstance(ability, list):
        ability_str = f"Ability: {random.choice(item)}" if ability else ""
    else:
        ability_str = f"Ability: {ability}" if ability else ""
    if isinstance(evs, list) and all(isinstance(item, dict) for item in evs):
        evs = random.choice(evs)
    evs = " / ".join(f"{value} {stats[key]}" for key, value in evs.items() if value > 0)
    evs_str = f"EVs: {evs}" if evs else ""
    if isinstance(ivs, list) and all(isinstance(item, dict) for item in ivs):
        ivs = random.choice(ivs)
    ivs = " / ".join(f"{value} {stats[key]}" for key, value in ivs.items() if value > 0)
    ivs_str = f"IVs: {ivs}" if ivs else ""
    if isinstance(tera, list):
        tera_str = f"Tera Type: {random.choice(tera)}" if tera else ""
    else:
        tera_str = f"Tera Type: {tera}" if tera else ""
    if isinstance(nature, list):
        nature_str = f"{random.choice(nature)} Nature" if nature else ""
    else:
        nature_str = f"{nature} Nature" if nature else ""
    for move in moveset.get("moves", []):
        if isinstance(move, list):
            selected_move = random.choice(move)
            moves.append(f"- {selected_move}")
        else:
            moves.append(f"- {move}")
    moves_str = "\n".join(moves)
    formatted_set = f"{pokemon_str}{item_str}"
    if ability_str:
        formatted_set += f"\n{ability_str}"
    if evs_str:
        formatted_set += f"\n{evs_str}"
    if ivs_str:
        formatted_set += f"\n{ivs_str}"
    if tera_str:
        formatted_set += f"\n{tera_str}"
    if nature_str:
        formatted_set += f"\n{nature_str}"
    formatted_set += f"\n{moves_str}"
    return formatted_set.strip()


async def add_set(
    prompt_key: str, message_key: str, button_key: str, set_data: str
) -> None:
    # Adds the set information to the selected sets and Pokemon information to the selected states.
    selected_states.setdefault(prompt_key, [])
    selected_sets.setdefault(prompt_key, {})
    selected_states[prompt_key] = message_key + button_key
    selected_sets[prompt_key][message_key] = [set_data]


async def remove_set(prompt_key: str, message_key: str, button_key: str) -> None:
    # Removes the set information from the selected sets and Pokemon information from the selected states.
    selected_states[prompt_key] = [
        state
        for state in selected_states[prompt_key]
        if not state.startswith(message_key)
    ]
    selected_sets[prompt_key].pop(message_key)


def update_buttons(
    message: discord.Message, button_id: str, deselected: bool, multiple: bool
) -> None:
    # Update the coloring of the buttons when a button is selected or deselected.
    view = View()
    first_button = True
    for component in message.components:
        for item in component.children:
            disabled = False
            if multiple and first_button:
                style = discord.ButtonStyle.primary
                disabled = True
                first_button = False
            elif deselected and item.custom_id == button_id:
                style = discord.ButtonStyle.secondary
            else:
                style = (
                    discord.ButtonStyle.success
                    if item.custom_id == button_id
                    else discord.ButtonStyle.secondary
                )
            button = Button(
                style=style,
                label=item.label,
                custom_id=item.custom_id,
                disabled=disabled,
            )
            view.add_item(button)
    return view


async def filter_requests(
    ctx: commands.Context,
    requests: List[Dict[str, Optional[str]]],
    results: List[Optional[List[str]]],
) -> Tuple[List[Dict[str, Optional[str]]], List[List[str]]]:
    # Filters in only valid Pokemon requests and sends an error message for each invalid request.
    valid_requests = []
    valid_results = []
    invalid_requests = []
    for request, set_names in zip(requests, results):
        if set_names is None or not set_names:
            pokemon = request["pokemon"]
            generation = request.get("generation", "")
            format = request.get("format", "")
            invalid_parts = [f"**{pokemon}**"]
            if generation:
                invalid_parts.append(f"**{generation}**")
            if format:
                invalid_parts.append(f"**{format}**")
            invalid_requests.append(" ".join(invalid_parts))
        else:
            valid_requests.append(request)
            valid_results.append(set_names)
    if invalid_requests:
        await ctx.send(InvalidRequest(invalid_requests).args[0])
    return valid_requests, valid_results
