"""
The function to give Pokemon sets from Smogon based on different types of criteria.
"""

import uuid
import asyncio
import random
import aiohttp
from smogon.set import *
from asyncio import Lock
from concurrent.futures import ThreadPoolExecutor
from discord import Interaction
from discord import ButtonStyle
from discord.ui import Button, View
from discord.ext import commands
from typing import Optional, List, Dict, Tuple


class GiveSet:
    awaiting_response = {}
    selected_states = {}
    selected_sets = {}
    first_row = {}

    @staticmethod
    async def fetch_pokemon() -> List[str]:
        # Retrieves a list of all Pokemon using PokeAPI.
        url = "https://pokeapi.co/api/v2/pokemon-species?limit=10000"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    pokemon_names = [species["name"] for species in data["results"]]
                    return pokemon_names

    @staticmethod
    async def fetch_set(
        set_name: str,
        pokemon: str,
        generation: Optional[str] = None,
        format: Optional[str] = None,
    ) -> str:
        # Fetches and displays set data based on Pokemon, Generation, Format and Set names given.
        if not generation:
            generation = await get_latest_gen(pokemon)
        gen_value = get_gen(generation)
        url = f"https://smogonapi.herokuapp.com/GetSmogonData/{gen_value}/{pokemon}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if not format:
                        format = await get_first_format(pokemon, generation)
                    for strategy in data.get("strategies", []):
                        if (
                            strategy["format"].lower()
                            == format.replace("-", " ").lower()
                        ):
                            for moveset in strategy.get("movesets", []):
                                if (
                                    moveset["name"].lower().replace(" ", "")
                                    == set_name.lower()
                                ):
                                    return format_set(moveset)

    @staticmethod
    async def set_prompt(
        ctx: commands.Context, requests: List[Dict[str, Optional[str]]]
    ) -> None:
        # Displays prompt with buttons for selection of Pokemon sets.
        key = str(uuid.uuid4())
        request_count = len(requests)
        prompt = "Please select a set type for "
        if request_count > 1:
            prompt += "the following Pokemon"
        else:
            request = requests[0]
            pokemon = request["pokemon"]
            generation = (get_gen(request.get("generation")) or "none").upper()
            format = (request.get("format", "none") or "none").upper()
            prompt += f"**{pokemon.upper()}{f' {generation}' if generation != 'NONE' else ''}{f' {format}' if format != 'NONE' else ''}**"
        prompt += ":"
        await ctx.send(prompt)
        tasks = [
            get_set_names(req["pokemon"], req["generation"], req["format"])
            for req in requests
        ]
        results = await asyncio.gather(*tasks)
        for index, (request, set_names) in enumerate(zip(requests, results)):
            view = get_view(key, request, set_names, request_count)
            message = await ctx.send(view=view)
            if index == 0:
                GiveSet.first_row[key] = message.id

    @staticmethod
    async def set_selection(
        interaction,
        set_name: str,
        pokemon: str,
        generation: Optional[str] = None,
        format: Optional[str] = None,
    ):
        # Fetches and displays the appropriate set data when a button is clicked.
        parts = interaction.data["custom_id"].split("_")
        key = parts[0]
        request_count = int(parts[-1])
        state = f"{pokemon}_{generation or 'none'}_{format or 'none'}_{set_name}"
        pokemon_state = f"{pokemon}_{generation or 'none'}_{format or 'none'}"
        deselected = state in GiveSet.selected_states.get(key, [])
        if deselected:
            await remove_set(key, state, pokemon_state)
        else:
            await add_set(key, set_name, pokemon, generation, format)
        set_data = "\n\n".join(
            "\n\n".join(data for data in sets)
            for sets in GiveSet.selected_sets.get(key, {}).values()
        )
        first_row = GiveSet.first_row.get(key)
        first_message = await interaction.channel.fetch_message(first_row)
        selected_row = await interaction.channel.fetch_message(interaction.message.id)
        updated_view = update_buttons(
            selected_row, interaction.data["custom_id"], deselected, request_count > 1
        )
        updated_content = f"```\n{set_data}```\n" if set_data else ""
        await selected_row.edit(view=updated_view)
        await first_message.edit(content=updated_content)

    @staticmethod
    async def fetch_random_sets(ctx: commands.Context, input_str: str) -> None:
        # Generates and displays random Pokemon sets with random eligible Generations and Formats.
        args_list = input_str.split()
        num = 1
        if len(args_list) > 1:
            if args_list[1].isdigit() and int(args_list[1]) >= 1:
                num = int(args_list[1])
            else:
                await ctx.send(
                    "Please follow this format: ```Clodbot, giveset random [Number >= 1, Nothing = 1]```"
                )
                return
        pokemon = await GiveSet.fetch_pokemon()
        loop = asyncio.get_event_loop()
        formatted_sets = []
        while len(formatted_sets) < num:
            remaining = num - len(formatted_sets)
            selected_pokemon = random.sample(pokemon, k=min(remaining, len(pokemon)))
            tasks = [
                loop.create_task(GiveSet.fetch_randomset_async(pokemon))
                for pokemon in selected_pokemon
            ]
            results = await asyncio.gather(*tasks)
            formatted_sets.extend([i for i in results if i is not None])
            for p in results:
                if p and p[0] in pokemon:
                    pokemon.remove(p[0])
        await ctx.send(f"```\n" + "\n\n".join(formatted_sets) + "\n```")

    @staticmethod
    async def fetch_randomset_async(pokemon: str) -> Optional[str]:
        # Helper function for fetching random sets asynchronously to save time.
        random_gen = await get_random_gen(pokemon)
        if not random_gen:
            return None
        random_format = await get_random_format(pokemon, random_gen)
        if not random_format:
            return None
        random_set = await get_random_set(pokemon, random_gen, random_format)
        if not random_set:
            return None
        formatted_set = await GiveSet.fetch_set(
            random_set, pokemon, random_gen, random_format
        )
        return formatted_set
