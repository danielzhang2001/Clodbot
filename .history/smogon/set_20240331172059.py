"""
General functions in scraping Pokemon Smogon sets.
"""

import asyncio
import aiohttp
import random
from discord import ButtonStyle, Message
from discord.ui import Button, View
from discord.ext import commands
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from uuid import uuid4

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


def get_gen(generation: str) -> Optional[str]:
    # Returns the generation value from the dictionary with the given Generation.
    if generation is None:
        return None
    gen_dict = get_gen_dict()
    if generation.lower() in gen_dict:
        return gen_dict[generation.lower()]
    if generation.lower() in gen_dict.values():
        return generation.lower()
    return None


async def get_latest_gen(pokemon: str) -> Optional[str]:
    # Returns the latest eligible generation for the given Pokemon.
    gen_dict = get_gen_dict()
    generations = list(gen_dict.values())[::-1]
    url = "https://smogonapi.herokuapp.com/GetSmogonData/{}/{}"
    async with aiohttp.ClientSession() as session:
        for gen_value in generations:
            async with session.get(url.format(gen_value, pokemon.lower())) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("strategies"):
                        gen_key = [
                            key for key, value in gen_dict.items() if value == gen_value
                        ][0]
                        return gen_key
    return None


async def get_random_gen(pokemon: str) -> Optional[str]:
    # Returns a random eligible gen using the Smogon API given a Pokemon.
    gen_dict = get_gen_dict()
    generations = list(gen_dict.values())
    url = "https://smogonapi.herokuapp.com/GetSmogonData/{}/{}"
    random.shuffle(generations)
    async with aiohttp.ClientSession() as session:
        for gen_code in generations:
            async with session.get(url.format(gen_code, pokemon.lower())) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("strategies"):
                        gen_key = [
                            key for key, value in gen_dict.items() if value == gen_code
                        ][0]
                        return gen_key
    return None


async def get_first_format(pokemon: str, generation: str) -> Optional[str]:
    # Returns the first format given the Pokemon and Generation.
    gen_value = get_gen(generation)
    url = f"https://smogonapi.herokuapp.com/GetSmogonData/{gen_value}/{pokemon.lower()}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                strategies = data.get("strategies", [])
                if strategies:
                    return strategies[0]["format"]
    return None


async def get_random_format(pokemon: str, generation: str) -> Optional[str]:
    # Returns a random eligible format using the Smogon API given a Pokemon and Generation.
    gen_value = get_gen(generation)
    url = f"https://smogonapi.herokuapp.com/GetSmogonData/{gen_value}/{pokemon}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                strategies = data.get("strategies", [])
                formats = [
                    strategy["format"]
                    for strategy in strategies
                    if strategy.get("movesets")
                ]
                if formats:
                    return random.choice(formats)
    return None


async def get_set_names(
    pokemon: str, generation: Optional[str] = None, format: Optional[str] = None
) -> Optional[List[str]]:
    # Returns all set names associated with the Pokemon, Generation and Format provided. If no Generation, assumed to be latest one, and if no Format, assumed to be first one.
    if not generation:
        generation = await get_latest_gen(pokemon)
        if generation is None:
            return None
    gen_value = get_gen(generation)
    if gen_value is None:
        return None
    url = f"https://smogonapi.herokuapp.com/GetSmogonData/{gen_value}/{pokemon.lower()}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                set_names = []
                if not format:
                    format = await get_first_format(pokemon, generation)
                for strategy in data.get("strategies", []):
                    if (
                        strategy["format"].replace(" ", "-").lower()
                        == format.replace(" ", "-").lower()
                    ):
                        for moveset in strategy.get("movesets", []):
                            set_names.append(moveset["name"])
                return set_names
    return None


async def get_random_set(pokemon: str, generation: str, format: str) -> Optional[str]:
    # Returns a random eligible set name using the Smogon API given a Pokemon, Generation and Format.
    gen_value = get_gen(generation)
    url = f"https://smogonapi.herokuapp.com/GetSmogonData/{gen_value}/{pokemon}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                for strategy in data.get("strategies", []):
                    if strategy.get("format") == format:
                        if strategy.get("movesets"):
                            set_names = [
                                moveset["name"] for moveset in strategy["movesets"]
                            ]
                            return random.choice(set_names)
    return None


def get_prompt(requests: List[Dict[str, Optional[str]]]) -> str:
    # Returns the initial prompt for the Pokemon(s) specified.
    prompt = "Please select a set type for "
    if len(requests) > 1:
        prompt += "the following Pokemon"
    else:
        request = requests[0]
        pokemon = request["pokemon"]
        generation = (get_gen(request.get("generation")) or "none").upper()
        format = (request.get("format") or "none").upper()
        prompt += f"**{pokemon.upper()}{f' {generation}' if generation != 'NONE' else ''}{f' {format}' if format != 'NONE' else ''}**"
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
                        for generation in [get_gen(request.get("generation")) or "none"]
                        if generation != "none"
                    ]
                    + [
                        format.upper()
                        for format in [request.get("format") or "none"]
                        if format != "none"
                    ]
                )
                + ":",
                style=ButtonStyle.primary,
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


def format_name(pokemon: str) -> str:
    # Format the Pokémon name to have each word (split by hyphen) start with a capital letter and the rest lowercase, except for single letters after hyphen which should remain lowercase.
    formatted_parts = []
    for part in pokemon.split("-"):
        if len(part) > 1:
            formatted_parts.append(part.capitalize())
        else:
            formatted_parts.append(part.lower())
    return "-".join(formatted_parts)


def format_set(moveset: dict) -> str:
    # Returns the formatted set data from the moveset information given.
    name = moveset["pokemon"]
    item = moveset.get("items", [])
    item_str = f" @ {item[0]}" if item else ""
    level = moveset.get("levels", [])
    level_str = f"\nLevel: {level[0]}" if level else ""
    ability = moveset.get("abilities", [])
    ability_str = f"\nAbility: {ability[0]}" if ability else ""
    evs_list = moveset.get("evconfigs", [])
    if evs_list:
        evs_dict = evs_list[0]
        evs = " / ".join(
            (
                f"{value} {'HP' if key == 'hp' else key.capitalize()}"
                if key != "spa" and key != "spd" and key != "spe"
                else f"{value} {'Atk' if key == 'atk' else 'Def' if key == 'def' else 'SpA' if key == 'spa' else 'SpD' if key == 'spd' else 'Spe'}"
            )
            for key, value in evs_dict.items()
            if value > 0
        )
        evs_str = f"\nEVs: {evs}" if evs else ""
    else:
        evs_str = ""
    ivs_list = moveset.get("ivconfigs", [])
    if ivs_list:
        ivs_dict = ivs_list[0]
        ivs = " / ".join(
            (
                f"{value} {'HP' if key == 'hp' else key.capitalize()}"
                if key != "spa" and key != "spd" and key != "spe"
                else f"{value} {'Atk' if key == 'atk' else 'Def' if key == 'def' else 'SpA' if key == 'spa' else 'SpD' if key == 'spd' else 'Spe'}"
            )
            for key, value in ivs_dict.items()
            if value != 31
        )
        ivs_str = f"\nIVs: {ivs}" if ivs else ""
    else:
        ivs_str = ""
    tera = moveset.get("teratypes", [])
    tera_str = f"\nTera Type: {random.choice(tera)}" if tera else ""
    nature = moveset.get("natures", [])
    nature_str = f"\n{nature[0]} Nature" if nature else ""
    moves = []
    for slot in moveset.get("moveslots", []):
        if slot:
            available_moves = [move["move"] for move in slot]
            selected_move = random.choice(available_moves)
            moves.append(selected_move)
            available_moves.remove(selected_move)
            while selected_move in moves[:-1]:
                selected_move = random.choice(available_moves)
                moves[-1] = selected_move
                available_moves.remove(selected_move)
    moves_str = "\n- " + "\n- ".join(moves)
    formatted_set = f"{name}{item_str}{ability_str}{level_str}{evs_str}{ivs_str}{tera_str}{nature_str}{moves_str}"
    return formatted_set.strip()


async def add_set(prompt_key, message_key, button_key, set_data):
    # Adds the set information to the selected sets and Pokemon information to the selected states.
    selected_states.setdefault(prompt_key, [])
    selected_sets.setdefault(prompt_key, {})
    selected_states[prompt_key].append(message_key + button_key)
    selected_sets[prompt_key][message_key] = [set_data]


async def remove_set(prompt_key, message_key, button_key):
    # Removes the set information from the selected sets and Pokemon information from the selected states.
    selected_states[prompt_key] = [
        state
        for state in selected_states[prompt_key]
        if not state.startswith(message_key)
    ]
    selected_sets[prompt_key].pop(message_key)


def update_buttons(
    message: Message, button_id: str, deselected: bool, multiple: bool
) -> None:
    # Update the coloring of the buttons when a button is selected or deselected.
    view = View()
    first_button = True
    for component in message.components:
        for item in component.children:
            disabled = False
            if multiple and first_button:
                style = ButtonStyle.primary
                disabled = True
                first_button = False
            elif deselected and item.custom_id == button_id:
                style = ButtonStyle.secondary
            else:
                style = (
                    ButtonStyle.success
                    if item.custom_id == button_id
                    else ButtonStyle.secondary
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
        await ctx.send("Cannot find sets for " + ", ".join(invalid_requests) + ".")
    return valid_requests, valid_results
