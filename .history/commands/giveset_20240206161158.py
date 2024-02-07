"""
The function to give Pokemon sets from Smogon based on different types of criteria.
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from smogon.set import *
from discord import ui, ButtonStyle
import uuid


class GiveSet:
    awaiting_response = {}

    @staticmethod
    async def set_prompt(ctx, pokemons_data):
        # Sends a message prompting the user to select a set for Pokemon.
        unique_id = str(uuid.uuid4())
        view = ui.View()
        prompt_text = ""
        multiple = len(pokemons_data) > 1

        if multiple:
            pokemon_names = [data[0] for data in pokemons_data]  # Extract pokemon names
            prompt_text = f"Please select set types for {', '.join(['**' + name + '**' for name in pokemon_names])}:\n"
            for pokemon, sets, url in pokemons_data:
                formatted_name = "-".join(
                    part.capitalize() if len(part) > 1 else part
                    for part in pokemon.split("-")
                )
                for index, set_name in enumerate(sets):
                    button_label = (
                        f"{formatted_name}: {set_name}"  # Keep labels detailed
                    )
                    button_id = f"set_{unique_id}_{pokemon}_{index}"
                    button = ui.Button(label=button_label, custom_id=button_id)
                    view.add_item(button)
        else:
            for pokemon, sets, url in pokemons_data:
                formatted_name = "-".join(
                    part.capitalize() if len(part) > 1 else part
                    for part in pokemon.split("-")
                )
                prompt_text += f"Please select a set type for **{formatted_name}**:\n"
                for index, set_name in enumerate(sets):
                    button_label = set_name  # Use simple labels for single Pokémon
                    button_id = f"set_{unique_id}_{pokemon}_{index}"
                    button = ui.Button(label=button_label, custom_id=button_id)
                    view.add_item(button)
                prompt_text += "\n"

        message = await ctx.send(prompt_text.strip(), view=view)
        GiveSet.awaiting_response[unique_id] = {
            "user_id": ctx.author.id,
            "pokemons_data": pokemons_data,
            "messages": {},
        }

    @staticmethod
    async def set_selection(interaction, unique_id, set_index, set_name, url, pokemon):
        # Generates the set data for the given criteria (Pokemon, Pokemon + Generation, Pokemon + Generation + Format)
        context = GiveSet.awaiting_response.get(unique_id)
        if not context:
            await interaction.followup.send(
                "Session expired or not found.", ephemeral=True
            )
            return
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
                    messages = context.get("messages", {})
                    channel = interaction.client.get_channel(interaction.channel_id)

                    if pokemon in messages:
                        message_id = messages[pokemon]
                        message = await channel.fetch_message(message_id)
                        await message.edit(content=f"```{set_data}```")
                    else:
                        new_message = await channel.send(f"```{set_data}```")
                        messages[pokemon] = new_message.id
                        context["messages"] = messages
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
    async def fetch_set(
        pokemon: str, generation: str = None, format: str = None
    ) -> tuple:
        # Gets the set information based on existing criteria (Pokemon, Pokemon + Generation, Pokemon + Generation + Format)
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
