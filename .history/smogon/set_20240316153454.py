"""
General functions in scraping Pokemon Smogon sets.
"""

import asyncio
import requests
import random
from discord import ui, ButtonStyle, Interaction
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple


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
    return get_gen_dict().get(generation.lower())


def get_latest_gen(pokemon: str) -> Optional[str]:
    # Returns the latest eligible generation for the given Pokemon.
    gen_dict = get_gen_dict()
    generations = list(gen_dict.values())[::-1]
    url = "https://smogonapi.herokuapp.com/GetSmogonData/{}/{}"
    for gen_value in generations:
        response = requests.get(url.format(gen_value, pokemon.lower()))
        if response.status_code == 200:
            data = response.json()
            if data.get("strategies"):
                gen_key = [
                    key for key, value in gen_dict.items() if value == gen_value
                ][0]
                return gen_key
            if "error" in data:
                print(f"Error for gen {gen_key} and pokemon {pokemon}: {data['error']}")
                continue
    return None


def get_first_format(pokemon: str, generation: str) -> Optional[str]:
    # Returns the first format given the Pokemon and Generation.
    gen_value = get_gen(generation)
    url = f"https://smogonapi.herokuapp.com/GetSmogonData/{gen_value}/{pokemon.lower()}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        strategies = data.get("strategies", [])
        if strategies:
            return strategies[0]["format"]
        else:
            return None
    else:
        return None


def get_random_gen(pokemon: str) -> Optional[str]:
    # Returns a random eligible gen using the Smogon API given a Pokemon.
    gen_dict = get_gen_dict()
    generations = list(gen_dict.values())
    url = "https://smogonapi.herokuapp.com/GetSmogonData/{}/{}"
    random.shuffle(generations)
    for gen_code in generations:
        response = requests.get(url.format(gen_code, pokemon.lower()))
        if response.status_code == 200:
            data = response.json()
            if data.get("strategies"):
                gen_key = [key for key, value in gen_dict.items() if value == gen_code][
                    0
                ]
                return gen_key
            if "error" in data:
                print(
                    f"Error for gen {gen_code} and pokemon {pokemon}: {data['error']}"
                )
                continue
    return None


def get_random_format(pokemon: str, generation: str) -> Optional[str]:
    # Returns a random eligible format using the Smogon API given a Pokemon and Generation.
    gen_value = get_gen(generation)
    url = f"https://smogonapi.herokuapp.com/GetSmogonData/{gen_value}/{pokemon}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        strategies = data.get("strategies", [])
        formats = [
            strategy["format"] for strategy in strategies if strategy.get("movesets")
        ]
        if formats:
            return random.choice(formats)
        else:
            return None
    else:
        return None


def get_random_set(pokemon: str, generation: str, format: str) -> Optional[str]:
    # Returns a random eligible set name using the Smogon API given a Pokemon, Generation and Format.
    gen_value = get_gen(generation)
    url = f"https://smogonapi.herokuapp.com/GetSmogonData/{gen_value}/{pokemon}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        for strategy in data.get("strategies", []):
            if strategy.get("format") == format:
                if strategy.get("movesets"):
                    set_names = [moveset["name"] for moveset in strategy["movesets"]]
                    return random.choice(set_names)
    else:
        return None


def get_set_names(
    pokemon: str, generation: Optional[str] = None, format: Optional[str] = None
) -> Optional[List[str]]:
    if not generation:
        generation = get_latest_gen(pokemon)
    gen_value = get_gen(generation)
    url = f"https://smogonapi.herokuapp.com/GetSmogonData/{gen_value}/{pokemon.lower()}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        set_names = []
        if not format:
            format = get_first_format(pokemon, generation)
        for strategy in data.get("strategies", []):
            if (
                strategy["format"].replace(" ", "-").lower()
                == format.replace(" ", "-").lower()
            ):
                for moveset in strategy.get("movesets", []):
                    set_names.append(moveset["name"])
        return set_names
    else:
        return None


def get_view(
    unique_id: str, pokemon_data: Tuple[str, Optional[List[str]], Optional[str]]
) -> Tuple[Dict[str, ui.View], str]:
    # Creates a prompt + buttons for Pokemon sets for a single Pokemon.
    pokemon, sets, url = pokemon_data
    view = ui.View()
    formatted_name = "-".join(
        part.capitalize() if len(part) > 1 else part for part in pokemon.split("-")
    )
    prompt = f"Please select a set type for **{formatted_name}**:\n"
    for index, set_name in enumerate(sets):
        button_id = f"set_{unique_id}_{pokemon}_{index}"
        button = ui.Button(label=set_name, custom_id=button_id)
        view.add_item(button)
    return {formatted_name: view}, prompt


def get_multiview(
    unique_id: str,
    pokemon_data: List[
        Tuple[str, Optional[List[str]], Optional[str], Optional[str], Optional[str]]
    ],
) -> Tuple[Dict[str, ui.View], str]:
    # Creates a prompt and buttons for Pokemon sets for multiple Pokemon.
    views = {}
    formatted_names = [
        "-".join(
            part.capitalize() if len(part) > 1 else part for part in pokemon.split("-")
        )
        for pokemon, _, _, _, _ in pokemon_data
    ]
    prompt = f"Please select set types for {', '.join(['**' + name + '**' for name in formatted_names])}:\n\n"
    for pokemon, sets, url, _, _ in pokemon_data:
        view = ui.View()
        formatted_name = "-".join(
            part.capitalize() if len(part) > 1 else part for part in pokemon.split("-")
        )
        view.add_item(
            ui.Button(
                label=f"{formatted_name}:", style=ButtonStyle.primary, disabled=True
            )
        )
        for index, set_name in enumerate(sets):
            button_id = f"set_{unique_id}_{pokemon}_{index}"
            button = ui.Button(label=set_name, custom_id=button_id)
            view.add_item(button)
        views[formatted_name] = view
    return views, prompt


def format_name(pokemon: str) -> str:
    # Format the Pokémon name to have each word (split by hyphen) start with a capital letter and the rest lowercase, except for single letters after hyphen which should remain lowercase.
    formatted_parts = []
    for part in pokemon.split("-"):
        if len(part) > 1:
            formatted_parts.append(part.capitalize())
        else:
            formatted_parts.append(part.lower())
    return "-".join(formatted_parts)


def update_buttons(view = ui.View, button_id: str) -> None:
    # Update the coloring of the buttons when it is clicked.
    for item in view.children:
        if item.custom_id == selected_button_custom_id:
            item.style = ButtonStyle.success
        else:
            item.style = ButtonStyle.secondary


async def update_button_rows(
    context: dict, interaction: Interaction, selected_sets: dict
) -> None:
    channel = interaction.client.get_channel(interaction.channel_id)
    # Iterates over all button rows to change button styles.
    for message_id in context.get("message_ids", []):
        view = context["views"].get(message_id)
        if view:
            update_buttons(view, selected_sets)
            try:
                message = await channel.fetch_message(message_id)
                await message.edit(view=view)
            except Exception as e:
                print(f"Failed to update message {message_id}: {e}")


async def update_message(
    context: dict,
    interaction: Interaction,
    unique_id: str,
    pokemon: Optional[str] = None,
    set_index: Optional[int] = None,
    set_display: Optional[str] = None,
) -> None:
    # Updates the set message of either adding or deleting a set after a set button is clicked.
    context.setdefault("sets", {})
    if set_index is not None:
        set_index = int(set_index)
    channel = interaction.client.get_channel(interaction.channel_id)
    selected_sets = context.get("selected_sets", {})
    if set_display and pokemon and set_index is not None:
        context["sets"].setdefault(pokemon, {})
        context["sets"][pokemon][set_index] = set_display
    message_content = context.get("prompt_message", "")
    for selected_pokemon, selected_index in selected_sets.items():
        if (
            selected_pokemon in context["sets"]
            and selected_index in context["sets"][selected_pokemon]
        ):
            set_info = context["sets"][selected_pokemon][selected_index]
            message_content += f"{set_info}\n\n"
    if message_content.strip():
        message_content = f"```{message_content}```"
    await update_button_rows(context, interaction, selected_sets)
    firstrow_id = context.get("message_ids", [None])[0]
    if firstrow_id is None:
        await interaction.followup.send(
            "Error: Button message ID not found.", ephemeral=True
        )
        return
    message = await channel.fetch_message(firstrow_id)
    view = context["views"].get(firstrow_id)
    if not view:
        await interaction.followup.send("Error: Button view not found.", ephemeral=True)
        return
    await message.edit(content=message_content, view=view)


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
            move = random.choice(slot)["move"]
            moves.append(move)
    moves_str = "\n- " + "\n- ".join(moves)
    formatted_set = f"{name}{item_str}{ability_str}{level_str}{evs_str}{ivs_str}{tera_str}{nature_str}{moves_str}"
    return formatted_set.strip()
