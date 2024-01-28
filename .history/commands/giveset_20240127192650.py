"""
The function to give Pokemon sets from smogon based on different types of criteria.
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from smogon.set import *
from discord import ui, ButtonStyle
import uuid


class GiveSet:
    awaiting_response = {}

    @staticmethod
    async def set_prompt(ctx, pokemon, sets, url):
        # Sends a message prompting the user to select a set with button selections and waits for their response.
        formatted_name = "-".join(
            part.capitalize() if len(part) > 1 else part for part in pokemon.split("-")
        )
        unique_id = str(uuid.uuid4())
        view = ui.View()
        for index, set_name in enumerate(sets):
            button = ui.Button(label=set_name, custom_id=f"set_{unique_id}_{index}")
            view.add_item(button)
        message = await ctx.send(
            f"Please select a set type for **{formatted_name}**:",
            view=view,
        )
        GiveSet.awaiting_response[ctx.channel.id] = {
            "message_id": message.id,
            "user_id": ctx.author.id,
            "sets": sets,
            "url": url,
        }

    @staticmethod
    async def set_selection(ctx, set_index, set_name, url):
        # Handles the set selection based on the index from the button interaction.
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
                    channel_id = ctx.channel.id
                    if channel_id in GiveSet.awaiting_response:
                        context = GiveSet.awaiting_response[channel_id]
                        if "message_id" in context:
                            try:
                                message_details = await ctx.channel.fetch_message(
                                    context["message_id"]
                                )
                                await message_details.edit(content=f"```{set_data}```")
                            except discord.NotFound:
                                message_details = await ctx.send(f"```{set_data}```")
                                context["message_id"] = message_details.id
                        else:
                            message_details = await ctx.send(f"```{set_data}```")
                            context["message_id"] = message_details.id
                    else:
                        message_details = await ctx.send(f"```{set_data}```")
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
        pokemon: str, generation: str = None, format: str = None, set: str = None
    ) -> tuple:
        # Directs to the fetch set type based on whether only a Pokemon name is provided or more.
        driver = None
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--log-level=3")
            driver = webdriver.Chrome(options=chrome_options)
            if generation is None and format is None and set == "":
                sets, url = fetch_general_set(driver, pokemon)
                return None, sets, url
            else:
                set_data = fetch_specific_set(driver, pokemon, generation, format, set)
                return set_data, None, None
        except Exception as e:
            return f"An error occurred: {str(e)}", None, None
        finally:
            if driver:
                driver.quit()
