"""
The function to give Pokemon sets from Smogon based on different types of criteria.
"""

import uuid
import asyncio
import random
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from smogon.set import *
from asyncio import Lock
from concurrent.futures import ThreadPoolExecutor
from discord import Interaction
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from discord.ext import commands


class GiveSet:
    awaiting_response = {}
    setname_cache = {}
    setinfo_cache = {}
    cache_duration = timedelta(hours=730)

    @staticmethod
    def get_setinfo_key(
        pokemon: str,
        set_name: str,
        generation: Optional[str] = None,
        format: Optional[str] = None,
    ) -> str:
        # Generates a key for accessing the cache of set data.
        parts = [pokemon.lower(), set_name.lower()]
        if generation:
            parts.append(f"gen{generation}")
        if format:
            parts.append(format.lower())
        return "_".join(parts)

    @staticmethod
    def check_setinfo_cache(
        pokemon: str,
        set_name: str,
        generation: Optional[str] = None,
        format: Optional[str] = None,
    ) -> Optional[dict]:
        # Checks if data is available in the set data cache and not expired.
        key = GiveSet.get_setinfo_key(pokemon, set_name, generation, format)
        if key in GiveSet.setinfo_cache:
            data, expiration = GiveSet.setinfo_cache[key]
            if datetime.now() < expiration:
                return data
        return None

    @staticmethod
    def update_setinfo_cache(
        pokemon: str,
        name: str,
        data: str,
        generation: Optional[str] = None,
        format: Optional[str] = None,
    ) -> None:
        # Updates the set data cache with new data.
        key = GiveSet.get_setinfo_key(pokemon, name, generation, format)
        expiration = datetime.now() + GiveSet.cache_duration
        GiveSet.setinfo_cache[key] = (data, expiration)

    @staticmethod
    def get_setname_key(
        pokemon: str, generation: Optional[str] = None, format: Optional[str] = None
    ) -> str:
        # Generates a key for accessing the cache of set names.
        parts = [pokemon.lower()]
        if generation:
            parts.append(f"gen{generation}")
        if format:
            parts.append(format.lower())
        return "_".join(parts)

    @staticmethod
    def check_setname_cache(
        pokemon: str, generation: Optional[str] = None, format: Optional[str] = None
    ) -> Optional[Tuple[List[str], str]]:
        # Checks if data is available in the set names cache and not expired.
        key = GiveSet.get_setname_key(pokemon, generation, format)
        if key in GiveSet.setname_cache:
            data, expiration = GiveSet.setname_cache[key]
            if datetime.now() < expiration:
                return data
        return None

    @staticmethod
    def update_setname_cache(
        pokemon: str,
        data: Tuple[List[str], str],
        generation: Optional[str] = None,
        format: Optional[str] = None,
    ) -> None:
        # Updates the set names cache with new data.
        key = GiveSet.get_setname_key(pokemon, generation, format)
        expiration = datetime.now() + GiveSet.cache_duration
        GiveSet.setname_cache[key] = (data, expiration)

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
        item = moveset.get("items", [])[0] if moveset.get("items") else "None"
        ability = (
            moveset.get("abilities", [])[0] if moveset.get("abilities") else "None"
        )
        evs_dict = moveset.get("evconfigs", [{}])[0]
        evs = (
            " / ".join(
                f"{value} {key.upper()}" for key, value in evs_dict.items() if value > 0
            )
            .replace("HP", "HP")
            .replace("ATK", "Atk")
            .replace("DEF", "Def")
            .replace("SPA", "SpA")
            .replace("SPD", "SpD")
            .replace("SPE", "Spe")
        )
        nature = moveset.get("natures", [])[0] if moveset.get("natures") else "None"
        moves = "\n- ".join(
            random.choice(move)["move"] for move in moveset.get("moveslots", [])
        )
        formatted_set = f"{name} @ {item}\nAbility: {ability}\nEVs: {evs}\n{nature} Nature\n- {moves}"
        return formatted_set

    @staticmethod
    async def fetch_set_async(
        pokemon: str, generation: Optional[str] = None, format: Optional[str] = None
    ) -> Tuple[Optional[List[str]], Optional[str]]:
        # Helper function for fetching sets asynchronously to save time.
        loop = asyncio.get_running_loop()
        sets, url = await loop.run_in_executor(
            None, GiveSet.fetch_set, pokemon, generation, format
        )
        return sets, url

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
        ctx: commands.Context,
        pokemon_data: List[
            Tuple[str, Optional[List[str]], Optional[str], Optional[str], Optional[str]]
        ],
    ) -> None:
        # Displays prompt with buttons for selection of Pokemon sets.
        unique_id = str(uuid.uuid4())
        views = {}
        prompt = ""
        messages = []
        GiveSet.awaiting_response[unique_id] = {
            "user_id": ctx.author.id,
            "pokemon_data": pokemon_data,
            "views": views,
            "message_ids": [],
            "lock": asyncio.Lock(),
        }
        if len(pokemon_data) > 1:
            views, prompt = get_multiview(unique_id, pokemon_data)
        else:
            pokemon, sets, url, _, _ = pokemon_data[0]
            views, prompt = get_view(unique_id, (pokemon, sets, url))
        await ctx.send(prompt)
        for formatted_name, view in views.items():
            message = await ctx.send(view=view)
            GiveSet.awaiting_response[unique_id]["views"][message.id] = view
            GiveSet.awaiting_response[unique_id]["message_ids"].append(message.id)

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
    async def display_random_sets(
        ctx: commands.Context, pokemon_data: List[Tuple[str, List[str], str]]
    ) -> None:
        # Displays all sets in one textbox given multiple Pokemon and their sets.
        message_content = ""
        for pokemon, sets, url in pokemon_data:
            if sets is None or not sets:
                await ctx.send(f"No sets found for {pokemon_data}. Skipping.")
            set_name = random.choice(sets)
            driver = None
            try:
                chrome_options = Options()
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--log-level=3")
                driver = webdriver.Chrome(options=chrome_options)
                driver.get(url)
                if get_export_btn(driver, set_name):
                    set_data = get_textarea(driver, set_name)
                    if set_data:
                        message_content += f"{set_data}\n\n"
                    else:
                        message_content += (
                            f"Error fetching set data for **{pokemon}**.\n\n"
                        )
            except Exception as e:
                message_content += (
                    f"An error occurred fetching set for **{pokemon}**: {str(e)}\n\n"
                )
            finally:
                if driver:
                    driver.quit()
        message_content = "```" + "\n" + message_content + "```"
        if message_content.strip() != "``````":
            await ctx.send(message_content)
        else:
            await ctx.send("Unable to fetch data for the selected Pokémon sets.")

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
            print(f"REMAINING: {remaining}")
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
