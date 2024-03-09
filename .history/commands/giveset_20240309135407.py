"""
The function to give Pokemon sets from Smogon based on different types of criteria.
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from smogon.set import *
from asyncio import Lock
from concurrent.futures import ThreadPoolExecutor
import uuid
import asyncio
import random
from discord import Interaction
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from discord.ext import commands


class GiveSet:
    awaiting_response = {}
    pokemon_cache = {"names": [], "expiration": datetime.now()}
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
        # Stores all Pokemon from Bulbapedia into a cache, returns the cache.
        current_time = datetime.now()
        if current_time <= GiveSet.pokemon_cache["expiration"]:
            return GiveSet.pokemon_cache["names"]
        url = "https://bulbapedia.bulbagarden.net/wiki/List_of_Pok%C3%A9mon_by_National_Pok%C3%A9dex_number"
        pokemon_names = []
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--log-level=3")
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//table[contains(@class, 'roundy')]//a[contains(@title, '(Pokémon)')]",
                    )
                )
            )
            pokemon_elements = driver.find_elements(
                By.XPATH,
                "//table[contains(@class, 'roundy')]//a[contains(@title, '(Pokémon)')]",
            )
            for element in pokemon_elements:
                pokemon_name = element.text.replace(" ", "-")
                if pokemon_name:
                    pokemon_names.append(pokemon_name)
        except Exception as e:
            print(f"An error occurred while updating Pokémon cache: {str(e)}")
        finally:
            if driver:
                driver.quit()
        GiveSet.pokemon_cache["names"] = pokemon_names
        GiveSet.pokemon_cache["expiration"] = current_time + GiveSet.cache_duration
        return pokemon_names

    @staticmethod
    def fetch_set(
        pokemon: str, generation: Optional[str] = None, format: Optional[str] = None
    ) -> Tuple[Optional[List[str]], Optional[str]]:
        # Gets the set information based on existing criteria (Pokemon, Pokemon + Generation, Pokemon + Generation + Format).
        cached_data = GiveSet.check_setname_cache(pokemon, generation, format)
        if cached_data:
            return cached_data
        driver = None
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--log-level=3")
            driver = webdriver.Chrome(options=chrome_options)
            set_names, url = get_setinfo(driver, pokemon, generation, format)
            print(f"SET NAMES AND URL HERE FOR {pokemon} HERE: {set_names} {url}")
            GiveSet.update_setname_cache(pokemon, (set_names, url), generation, format)
            return set_names, url
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return None, None
        finally:
            if driver:
                driver.quit()

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
        # Uses fetch_set multiple times to speed up process of fetching multiple Pokemon sets with potential Generation and Format.
        loop = asyncio.get_running_loop()
        tasks = [
            loop.run_in_executor(None, GiveSet.fetch_set_with_gen_format, request)
            for request in requests
        ]
        results = await asyncio.gather(*tasks)
        return results

    @staticmethod
    def fetch_set_with_gen_format(
        request: Dict[str, Optional[str]]
    ) -> Tuple[str, Optional[List[str]], Optional[str]]:
        # Uses fetch_set with request to fetch multiple sets with potential different specifications of Generation and Format.
        pokemon, generation, format = (
            request["name"],
            request["generation"],
            request["format"],
        )
        print(f"POKEMON GENERATION AND FORMAT HERE: {pokemon} {generation} {format}")
        sets, url = GiveSet.fetch_set(pokemon, generation, format)
        return (pokemon, sets, url)

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
                    print(f"MY SET DATA: {set_data}")
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
        message_content = "```" + message_content + "```"
        print(f"MY MESSAGE CONTENT: {message_content}")
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
        valid_pokemon = []
        while len(valid_pokemon) < num:
            remaining = num - len(valid_pokemon)
            selected_pokemon = random.sample(pokemon, k=min(remaining, len(pokemon)))
            tasks = [
                loop.create_task(GiveSet.fetch_randomset_async(pokemon))
                for pokemon in selected_pokemon
            ]
            results = await asyncio.gather(*tasks)
            valid_pokemon.extend([p for p in results if p is not None])
            print(f"VALID POKEMON: {valid_pokemon}")
            for p in valid_pokemon:
                if p[0] in pokemon:
                    pokemon.remove(p[0])
        await GiveSet.display_random_sets(ctx, valid_pokemon[:num])

    @staticmethod
    async def fetch_randomset_async(
        pokemon: str,
    ) -> Optional[Tuple[str, List[str], str]]:
        # Helper function for fetching random sets asynchronously to save time.
        loop = asyncio.get_running_loop()
        eligible_gens = await loop.run_in_executor(None, get_eligible_gens, pokemon)
        if not eligible_gens:
            print(f"THIS POKEMON {pokemon} HAS NO ELIGIBLE GENS!")
            return None
        random_gen = random.choice(eligible_gens)

        eligible_formats = await loop.run_in_executor(
            None, get_eligible_formats, pokemon, random_gen
        )
        if not eligible_formats:
            print(f"THIS POKEMON {pokemon} HAS NO ELIGIBLE FORMATS!")
            return None
        random_format = random.choice(eligible_formats)
        set_data = await loop.run_in_executor(
            None,
            GiveSet.fetch_set_with_gen_format,
            {"name": pokemon, "generation": random_gen, "format": random_format},
        )
        return set_data
