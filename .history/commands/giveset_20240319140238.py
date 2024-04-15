"""
The function to give Pokemon sets from Smogon based on different types of criteria.
"""

import uuid
import asyncio
import random
import requests
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

    @staticmethod
    def fetch_all_pokemon() -> List[str]:
        # Retrieves a list of all Pokemon using PokeAPI.
        url = "https://pokeapi.co/api/v2/pokemon-species?limit=10000"
        response = requests.get(url)
        data = response.json()
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
            generation = get_latest_gen(pokemon)
        gen_value = get_gen(generation)
        url = f"https://smogonapi.herokuapp.com/GetSmogonData/{gen_value}/{pokemon}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if not format:
                format = get_first_format(pokemon, generation)
            for strategy in data.get("strategies", []):
                if strategy["format"].lower() == format.replace("-", " ").lower():
                    for moveset in strategy.get("movesets", []):
                        if moveset["name"].lower() == set_name.lower():
                            return format_set(moveset)
        return "Set not found."

    @staticmethod
    async def fetch_multiset_async(
        requests: List[Dict[str, Optional[str]]]
    ) -> List[Tuple[Optional[List[str]], Optional[str]]]:
        # Uses fetch_set to fetch multiple sets with potential different specifications of Generation and Format asynchronously.
        loop = asyncio.get_running_loop()
        tasks = [
            loop.run_in_executor(
                None,
                GiveSet.fetch_set,
                request["pokemon"],
                request.get("generation"),
                request.get("format"),
            )
            for request in requests
        ]
        results = await asyncio.gather(*tasks)
        final_results = [
            (requests[i]["pokemon"], result[0], result[1])
            for i, result in enumerate(results)
        ]
        return final_results

    @staticmethod
    async def set_prompt(
        ctx: commands.Context, requests: List[Dict[str, Optional[str]]]
    ) -> None:
        # Displays prompt with buttons for selection of Pokemon sets.
        prompt = "Please select a set type for "
        view = View()
        for index, request in enumerate(requests):
            pokemon, generation, format = (
                request["pokemon"],
                request["generation"],
                request["format"],
            )
            set_names = get_set_names(pokemon, generation, format)
            gen_code = get_gen(generation).upper() if get_gen(generation) else ""
            format = format.upper() if format else ""
            if index > 0:
                prompt += ", "
            prompt += f"**{pokemon.upper()}**{f' {gen_code}' if gen_code else ''}{f' {format}' if format else ''}"
            for set_name in set_names:
                btn_id = (
                    f"{pokemon}_{generation or 'none'}_{format or 'none'}_{set_name}"
                )
                button = Button(
                    label=set_name, custom_id=btn_id, style=ButtonStyle.secondary
                )
                view.add_item(button)
        prompt += ":"
        await ctx.send(prompt, view=view)

    @staticmethod
    async def set_selection(
        interaction,
        set_name: str,
        pokemon: str,
        generation: Optional[str] = None,
        format: Optional[str] = None,
    ):
        # Fetches and display the appropriate set data when a button is clicked.
        current_state = GiveSet.selected_states.get(interaction.message.id, None)
        new_state = f"{pokemon}_{generation or 'none'}_{format or 'none'}_{set_name}"
        prompt = (
            f"Please select a set type for **{pokemon.upper()}"
            f"{' ' + get_gen(generation).upper() if get_gen(generation) else ''}"
            f"{' ' + format.upper() if format else ''}**:\n"
        )
        if current_state == new_state:
            GiveSet.selected_states[interaction.message.id] = None
            formatted_set = ""
        else:
            set_data = await GiveSet.fetch_set(set_name, pokemon, generation, format)
            formatted_set = f"```\n{set_data}\n```"
            GiveSet.selected_states[interaction.message.id] = new_state
        view = update_buttons(
            interaction.message,
            interaction.data["custom_id"],
            GiveSet.selected_states[interaction.message.id] is None,
        )
        await interaction.edit_original_response(
            content=prompt + formatted_set, view=view
        )

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
        pokemon = GiveSet.fetch_all_pokemon()
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
        random_gen = get_random_gen(pokemon)
        if not random_gen:
            return None
        random_format = get_random_format(pokemon, random_gen)
        if not random_format:
            return None
        random_set = get_random_set(pokemon, random_gen, random_format)
        if not random_set:
            return None
        formatted_set = await GiveSet.fetch_set(
            random_set, pokemon, random_gen, random_format
        )
        return formatted_set
