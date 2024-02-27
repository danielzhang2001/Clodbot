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
import time


class GiveSet:
    awaiting_response = {}

    # For caching Pokemon names
    pokemon_cache = {"names": [], "last_updated": 0}

    @staticmethod
    def fetch_cache():
        # Stores all Pokemon from Bulbapedia into a cache that updates every 24 hours, returns the cache.
        current_time = time.time()
        if not GiveSet.pokemon_cache["names"] or (
            current_time - GiveSet.pokemon_cache["last_updated"] > 86400
        ):
            print("Updating Pokémon cache...")
            url = "https://bulbapedia.bulbagarden.net/wiki/List_of_Pok%C3%A9mon_by_National_Pok%C3%A9dex_number"
            driver = None
            try:
                chrome_options = Options()
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("log-level=3")
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
                pokemon_names = []
                for element in pokemon_elements:
                    pokemon_name = element.text.replace(" ", "-")
                    if pokemon_name:
                        pokemon_names.append(pokemon_name)
                GiveSet.pokemon_cache["names"] = pokemon_names
                GiveSet.pokemon_cache["last_updated"] = current_time
            except Exception as e:
                print(f"An error occurred while updating Pokémon cache: {str(e)}")
            finally:
                if driver:
                    driver.quit()
        else:
            print("Using cached Pokémon data...")
        return GiveSet.pokemon_cache["names"]

    @staticmethod
    async def set_prompt(ctx, pokemon_data):
        # Displays prompt with buttons for selection of Pokemon sets.
        unique_id = str(uuid.uuid4())
        GiveSet.awaiting_response[unique_id] = {
            "user_id": ctx.author.id,
            "pokemon_data": pokemon_data,
            "views": views,
            "message_ids": [],
            "lock": asyncio.Lock(),
        }
        if len(pokemon_data) > 1:
            formatted_names = [
                "-".join(
                    part.capitalize() if len(part) > 1 else part
                    for part in pokemon[0].split("-")
                )
                for pokemon in pokemon_data
            ]
            prompt = f"Please select set types for {', '.join(['**' + name + '**' for name in formatted_names])}:\n\n"
            await ctx.send(prompt)
            for pokemon, sets, url in pokemon_data:
                view = ui.View()
                formatted_name = "-".join(
                    part.capitalize() if len(part) > 1 else part
                    for part in pokemon.split("-")
                )
                view.add_item(
                    ui.Button(
                        label=f"{formatted_name}:",
                        style=ButtonStyle.secondary,
                        disabled=True,
                    )
                )
                for index, set_name in enumerate(sets):
                    button_id = f"set_{unique_id}_{pokemon}_{index}"
                    button = ui.Button(label=set_name, custom_id=button_id)
                    view.add_item(button)
                message = await ctx.send(view=view)
                views[message.id] = view
        else:
            pokemon, sets, url = pokemon_data[0]
            view = ui.View()
            formatted_name = "-".join(
                part.capitalize() if len(part) > 1 else part
                for part in pokemon.split("-")
            )
            prompt = f"Please select a set type for **{formatted_name}**:\n"
            await ctx.send(prompt)
            for index, set_name in enumerate(sets):
                button_id = f"set_{unique_id}_{pokemon}_{index}"
                button = ui.Button(label=set_name, custom_id=button_id)
                view.add_item(button)
            message = await ctx.send(view=view)
            views[message.id] = view
        GiveSet.awaiting_response[unique_id]["views"] = views
        GiveSet.awaiting_response[unique_id]["message_ids"] = [
            msg.id for msg in messages
        ]

    @staticmethod
    async def set_selection(interaction, unique_id, set_index, set_name, url, pokemon):
        # Handles button functionality to display appropriate set when clicked.
        context = GiveSet.awaiting_response.get(unique_id)
        if not context:
            await interaction.followup.send(
                "Session expired or not found.", ephemeral=True
            )
            return
        lock = context["lock"]
        async with lock:
            if "sets" not in context:
                context["sets"] = {}
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
                        context["sets"][pokemon] = f"{set_data}\n\n"
                        sets_message = "".join(context["sets"].values())
                        message_content = f"```{sets_message}```"
                        channel = interaction.client.get_channel(interaction.channel_id)
                        original_message_id = interaction.message.id
                        view = context["views"].get(original_message_id)
                        if not view:
                            await interaction.followup.send(
                                "Original message view not found.", ephemeral=True
                            )
                            return
                        is_multi_pokemon = len(context["pokemon_data"]) > 1
                        for index, item in enumerate(view.children):
                            if is_multi_pokemon and index % len(view.children) == 0:
                                item.disabled = True
                            else:
                                item.disabled = False
                        for item in view.children:
                            if (
                                item.custom_id
                                == f"set_{unique_id}_{pokemon}_{set_index}"
                            ):
                                item.disabled = True
                                break
                        original_message = await channel.fetch_message(
                            original_message_id
                        )
                        await original_message.edit(view=view)
                        if "combined_message_id" in context:
                            message_id = context["combined_message_id"]
                            message = await channel.fetch_message(message_id)
                            await message.edit(content=message_content)
                        else:
                            message = await channel.send(message_content)
                            context["combined_message_id"] = message.id
                    else:
                        await interaction.followup.send(
                            "Error fetching set data.", ephemeral=True
                        )
                else:
                    await interaction.followup.send(
                        "Error finding set. Please try again.", ephemeral=True
                    )
            except Exception as e:
                await interaction.followup.send(
                    f"An error occurred: {str(e)}", ephemeral=True
                )
            finally:
                if driver:
                    driver.quit()

    @staticmethod
    def fetch_set(pokemon: str, generation: str = None, format: str = None) -> tuple:
        # Gets the set information based on existing criteria (Pokemon, Pokemon + Generation, Pokemon + Generation + Format).
        driver = None
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--log-level=3")
            driver = webdriver.Chrome(options=chrome_options)
            if generation:
                gen_code = get_gen(generation)
                if not gen_code:
                    return None, None
                url = (
                    f"https://www.smogon.com/dex/{gen_code}/pokemon/{pokemon.lower()}/"
                )
                driver.get(url)
                if format:
                    url += f"{format.lower()}/"
                    driver.get(url)
                    if not is_valid_format(driver, format):
                        return None, None
                if not is_valid_pokemon(driver, pokemon):
                    return None, None
            else:
                for gen in reversed(get_gen_dict().values()):
                    url = f"https://www.smogon.com/dex/{gen}/pokemon/{pokemon.lower()}/"
                    driver.get(url)
                    if is_valid_pokemon(driver, pokemon) and has_export_buttons(driver):
                        sets = get_set_names(driver)
                        return sets, url
                return None, None
            sets = get_set_names(driver)
            return sets, url
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return None, None
        finally:
            if driver:
                driver.quit()

    @staticmethod
    async def fetch_set_async(pokemon: str, generation: str = None, format: str = None):
        # Helper function for fetching sets asynchronously to save time.
        loop = asyncio.get_running_loop()  # For Python 3.7+
        sets, url = await loop.run_in_executor(
            None, GiveSet.fetch_set, pokemon, generation, format
        )
        return sets, url

    @staticmethod
    async def fetch_multiple_sets_async(pokemon_names: list):
        # Uses fetch_set_async multiple times to speed up process of fetching multiple Pokemon sets.
        tasks = [GiveSet.fetch_set_async(name) for name in pokemon_names]
        results = await asyncio.gather(*tasks)
        return results

    @staticmethod
    async def display_sets(ctx, pokemon_data):
        # Displays all sets in one textbox given Pokemon and their Sets.
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
