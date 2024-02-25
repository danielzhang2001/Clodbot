"""
The function to give Pokemon sets from Smogon based on different types of criteria.
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from smogon.set import *
from discord import ui, ButtonStyle
from asyncio import Lock
from concurrent.futures import ThreadPoolExecutor
import uuid
import asyncio
from datetime import datetime, timedelta


class GiveSet:
    awaiting_response = {}
    # For caching Pokemon names
    pokemon_cache = {"names": [], "expiration": datetime.now()}
    # For caching Pokemon sets
    set_cache = {}
    # For caching Pokemon set info
    set_display_cache = {}
    # Cache expiration duration
    cache_duration = timedelta(hours=730)

    @staticmethod
    def get_cache_key(pokemon, generation=None, format=None):
        # Generates a key for accessing the cache.
        return (
            pokemon.lower(),
            str(generation).lower() if generation else None,
            str(format).lower() if format else None,
        )

    @staticmethod
    def check_cache(pokemon, generation=None, format=None):
        # Checks if data is available in the cache and not expired.
        key = GiveSet.get_cache_key(pokemon, generation, format)
        if key in GiveSet.set_cache:
            data, expiration = GiveSet.set_cache[key]
            if datetime.now() < expiration:
                return data
        return None

    @staticmethod
    def update_cache(pokemon, data, generation=None, format=None):
        # Updates the cache with new data every month.
        key = GiveSet.get_cache_key(pokemon, generation, format)
        expiration = datetime.now() + GiveSet.cache_duration
        GiveSet.set_cache[key] = (data, expiration)

    @staticmethod
    def fetch_cache():
        # Stores all Pokemon from Bulbapedia into a cache that updates every month, returns the cache.
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
    def fetch_set(pokemon, generation=None, format=None):
        # Gets the set information based on existing criteria (Pokemon, Pokemon + Generation, Pokemon + Generation + Format).
        cached_data = GiveSet.check_cache(pokemon, generation, format)
        if cached_data:
            return cached_data
        driver = None
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--log-level=3")
            driver = webdriver.Chrome(options=chrome_options)
            set_names, url = get_setinfo(driver, pokemon, generation, format)
            GiveSet.update_cache(pokemon, (set_names, url), generation, format)
            return set_names, url
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return None, None
        finally:
            if driver:
                driver.quit()

    @staticmethod
    async def fetch_set_async(pokemon, generation=None, format=None):
        # Helper function for fetching sets asynchronously to save time.
        loop = asyncio.get_running_loop()  # For Python 3.7+
        sets, url = await loop.run_in_executor(
            None, GiveSet.fetch_set, pokemon, generation, format
        )
        return sets, url

    @staticmethod
    async def fetch_multiset_async(pokemon_names):
        # Uses fetch_set_async multiple times to speed up process of fetching multiple Pokemon sets.
        tasks = [GiveSet.fetch_set_async(name) for name in pokemon_names]
        results = await asyncio.gather(*tasks)
        return results

    @staticmethod
    async def set_prompt(ctx, pokemon_data):
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
            views, prompt = get_view(unique_id, pokemon_data[0])
        await ctx.send(prompt)
        for formatted_name, view in views.items():
            message = await ctx.send(view=view)
            GiveSet.awaiting_response[unique_id]["views"][message.id] = view
            GiveSet.awaiting_response[unique_id]["message_ids"].append(message.id)

    @staticmethod
    async def set_selection(interaction, unique_id, set_index, set_name, url, pokemon):
        # Handles sending and updating the set message when prompt buttons are clicked.
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
                        if pokemon in selected_sets:
                            await update_message(
                                context,
                                interaction,
                                unique_id,
                                pokemon,
                                set_index,
                                set_data,
                            )
                        else:
                            await update_message(
                                context, interaction, unique_id, pokemon
                            )
                    else:
                        await interaction.followup.send(
                            "Error fetching set data.", ephemeral=True
                        )
            except Exception as e:
                await interaction.followup.send(
                    f"An error occurred: {str(e)}", ephemeral=True
                )
            finally:
                if driver:
                    driver.quit()

    @staticmethod
    async def display_sets(ctx, pokemon_data):
        # Displays all sets in one textbox given multiple Pokemon and their sets.
        message_content = ""
        for pokemon, sets, url in pokemon_data:
            set_name = sets[0]
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
                else:
                    message_content += f"Error finding set for **{pokemon}**.\n\n"
            except Exception as e:
                message_content += (
                    f"An error occurred fetching set for **{pokemon}**: {str(e)}\n\n"
                )
            finally:
                if driver:
                    driver.quit()
        message_content = "```" + message_content + "```"
        if message_content.strip() != "``````":
            await ctx.send(message_content)
        else:
            await ctx.send("Unable to fetch data for the selected Pokémon sets.")
