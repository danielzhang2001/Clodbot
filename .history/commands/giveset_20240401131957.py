"""
The function to give Pokemon sets from Smogon based on different types of criteria.
"""

import uuid
import asyncio
import random
import aiohttp
import discord
from smogon.set import *
from asyncio import Lock
from concurrent.futures import ThreadPoolExecutor
from discord import ButtonStyle
from discord.ui import Button, View
from discord.ext import commands
from typing import Optional, List, Dict, Tuple
from uuid import uuid4
from datetime import datetime


class GiveSet:
    awaiting_response = {}
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

    @staticmethod
    async def set_prompt(
        ctx: commands.Context, requests: List[Dict[str, Optional[str]]]
    ) -> None:
        # Displays prompt with buttons for selection of Pokemon sets.
        tasks = [
            get_set_names(req["pokemon"], req["generation"], req["format"])
            for req in requests
        ]
        results = await asyncio.gather(*tasks)
        valid_requests, valid_results = await filter_requests(ctx, requests, results)
        if not valid_requests:
            return
        prompt_key = uuid4().hex[:20]
        request_count = len(valid_requests)
        prompt = get_prompt(valid_requests)
        await ctx.send(prompt)
        for index, (request, set_names) in enumerate(
            zip(valid_requests, valid_results)
        ):
            message_key = uuid4().hex[:5]
            view = get_view(prompt_key, message_key, request, set_names, request_count)
            message = await ctx.send(view=view)
            if index == 0:
                GiveSet.first_row[prompt_key] = (message.id, datetime.

    @staticmethod
    async def set_selection(
        interaction: discord.Interaction,
        prompt_key: str,
        message_key: str,
        button_key: str,
        request_count: int,
        set_name: str,
        pokemon: str,
        generation: Optional[str] = None,
        format: Optional[str] = None,
    ):
        # Fetches and displays the appropriate set data when a button is clicked.
        deselected = message_key + button_key in selected_states.get(prompt_key, [])
        if deselected:
            await remove_set(prompt_key, message_key, button_key)
        else:
            set_data = await GiveSet.fetch_set(set_name, pokemon, generation, format)
            await add_set(prompt_key, message_key, button_key, set_data)
        set_data = "\n\n".join(
            "\n\n".join(data for data in sets)
            for sets in selected_sets.get(prompt_key, {}).values()
        )
        first_row = GiveSet.first_row.get(prompt_key)
        first_message = await interaction.channel.fetch_message(first_row)
        selected_row = await interaction.channel.fetch_message(interaction.message.id)
        updated_view = update_buttons(
            selected_row, interaction.data["custom_id"], deselected, request_count > 1
        )
        updated_content = f"```\n{set_data}```\n" if set_data else ""
        await selected_row.edit(view=updated_view)
        await first_message.edit(content=updated_content)
