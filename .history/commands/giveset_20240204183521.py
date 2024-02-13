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
    prompts = []

    @staticmethod
    async def set_prompt(ctx, pokemons, sets_dict, urls_dict):
        view = ui.View()
        prompt_message = ""
        for pokemon in pokemons:
            sets = sets_dict[pokemon]
            url = urls_dict[pokemon]
            unique_id = str(uuid.uuid4())
            formatted_name = "-".join(
                part.capitalize() if len(part) > 1 else part
                for part in pokemon.split("-")
            )
            prompt_message += f"Please select a set type for **{formatted_name}**:\n"
            for index, set_name in enumerate(sets):
                button = ui.Button(label=set_name, custom_id=f"set_{unique_id}_{index}")
                view.add_item(button)
            GiveSet.awaiting_response[unique_id] = {
                "user_id": ctx.author.id,
                "sets": sets,
                "url": url,
            }

        message = await ctx.send(prompt_message, view=view)
        for unique_id in GiveSet.awaiting_response:
            GiveSet.awaiting_response[unique_id]["message_id"] = message.id

    @staticmethod
    async def set_selection(ctx, unique_id, set_index, set_name, url):
        # Gives the set data based on the button selected from the Pokemon prompt.
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
                    if unique_id in GiveSet.awaiting_response:
                        context = GiveSet.awaiting_response[unique_id]
                        if "set_message_id" in context:
                            try:
                                message_details = await ctx.channel.fetch_message(
                                    context["set_message_id"]
                                )
                                await message_details.edit(content=f"```{set_data}```")
                            except discord.NotFound:
                                new_message_details = await ctx.send(
                                    f"```{set_data}```"
                                )
                                context["set_message_id"] = new_message_details.id
                        else:
                            new_message_details = await ctx.send(f"```{set_data}```")
                            context["set_message_id"] = new_message_details.id
                else:
                    await ctx.send("Error fetching set data.")
            else:
                await ctx.send("Error finding set. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")
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
