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
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from discord.ext import commands


class GiveSet:
    awaiting_response = {}

    @staticmethod
    def fetch_all_pokemon() -> List[str]:
        # Retrieves a list of all Pokemon using PokeAPI.
        url = "https://pokeapi.co/api/v2/pokemon-species?limit=10000"
        response = requests.get(url)
        data = response.json()
        pokemon_names = [species["name"] for species in data["results"]]
        return pokemon_names

    @staticmethod
    def fetch_set(pokemon: str, generation: str, format: str, set: str) -> str:
        # Fetches and displays set data based on Pokemon, Generation, Format and Set names given.
        gen_code = get_gen(generation)
        url = f"https://smogonapi.herokuapp.com/GetSmogonData/{gen_code}/{pokemon}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            for strategy in data.get("strategies", []):
                if strategy["format"].lower() == format.lower():
                    for moveset in strategy.get("movesets", []):
                        if moveset["name"].lower() == set.lower():
                            return GiveSet.format_set(moveset)
        return "Set not found."

    @staticmethod
    def format_set(moveset: dict) -> str:
        # Returns the formatted set data from the moveset information given.
        name = moveset["pokemon"]
        item = moveset.get("items", [])
        item_str = f" @ {item[0]}" if item else ""
        ability = moveset.get("abilities", [])
        ability_str = f"\nAbility: {ability[0]}" if ability else ""
        evs_list = moveset.get("evconfigs", [])
        if evs_list:
            evs_dict = evs_list[0]
            evs = " / ".join(
                f"{value} {key.capitalize()}"
                for key, value in evs_dict.items()
                if value > 0
            )
            evs_str = f"\nEVs: {evs}" if evs else ""
        else:
            evs_str = ""
        nature = moveset.get("natures", [])
        nature_str = f"\n{nature[0]} Nature" if nature else ""
        moves = []
        for slot in moveset.get("moveslots", []):
            if slot:
                move = random.choice(slot)["move"]
                moves.append(move)
        moves_str = "\n- " + "\n- ".join(moves)
        formatted_set = f"{name}{item_str}{ability_str}{evs_str}{nature_str}{moves_str}"
        return formatted_set.strip()

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
    async def set_prompt(ctx, pokemon: str, generation: Optional[str] = None, format: Optional[str] = None): -> None:
        # Displays prompt with buttons for selection of Pokemon sets.
        set_names = get_set_names(pokemon, generation, format)
        formatted_name = "-".join(part.capitalize() if len(part) > 1 else part for part in pokemon.split("-"))
        prompt = f"Please select a set type for **{formatted_name}**:\n"
        view = View()
        for set_name in set_names:
            button = Button(label=set_name, style=ButtonStyle.secondary)
            view.add_item(button)
        ctx.send(prompt, view=view)

    @staticmethod
    async def set_selection(
        interaction: Interaction,
        unique_id: str,
        set_index: int,
        set_name: str,
        url: str,
        pokemon: str,
    ) -> None:
        # Handles button functionality from set_prompt when clicked
        context = GiveSet.awaiting_response.get(unique_id)
        if not context:
            await interaction.followup.send(
                "Session expired or not found.", ephemeral=True
            )
            return
        lock = context["lock"]
        async with lock:
            if "selected_sets" not in context:
                context["selected_sets"] = {}
            selected_sets = context["selected_sets"]
            if pokemon in selected_sets and selected_sets[pokemon] == set_index:
                del selected_sets[pokemon]
            else:
                selected_sets[pokemon] = set_index
            pokemon_data = context["pokemon_data"]
            for data in pokemon_data:
                if data[0] == pokemon:
                    _, _, _, generation, format = data
                    break
            set_display = GiveSet.check_setinfo_cache(
                pokemon, set_name, generation, format
            )
            if not set_display:
                driver = None
                try:
                    chrome_options = Options()
                    chrome_options.add_argument("--headless")
                    chrome_options.add_argument("--log-level=3")
                    driver = webdriver.Chrome(options=chrome_options)
                    driver.get(url)
                    if get_export_btn(driver, set_name):
                        set_data = get_textarea(driver, set_name)
                        GiveSet.update_setinfo_cache(
                            pokemon, set_name, set_data, generation, format
                        )
                        set_display = set_data
                    else:
                        await interaction.followup.send(
                            "Error fetching set data.", ephemeral=True
                        )
                        return
                except Exception as e:
                    await interaction.followup.send(
                        f"An error occurred: {str(e)}", ephemeral=True
                    )
                    return
                finally:
                    if driver:
                        driver.quit()
            if set_display:
                await update_message(
                    context,
                    interaction,
                    unique_id,
                    pokemon,
                    set_index,
                    set_display,
                )
            else:
                await interaction.followup.send(
                    "Error fetching set data.", ephemeral=True
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
        loop = asyncio.get_running_loop()
        random_gen = await loop.run_in_executor(None, get_random_gen, pokemon)
        if not random_gen:
            return None
        random_format = await loop.run_in_executor(
            None, get_random_format, pokemon, random_gen
        )
        if not random_format:
            return None
        random_set = await loop.run_in_executor(
            None, get_random_set, pokemon, random_gen, random_format
        )
        if not random_set:
            return None
        formatted_set = await loop.run_in_executor(
            None, GiveSet.fetch_set, pokemon, random_gen, random_format, random_set
        )
        return formatted_set
