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
        unique_id = str(uuid.uuid4())
        formatted_name = "-".join(
            part.capitalize() if len(part) > 1 else part for part in pokemon.split("-")
        )
        view = ui.View()
        for index, set_name in enumerate(sets):
            button = ui.Button(label=set_name, custom_id=f"set_{unique_id}_{index}")
            view.add_item(button)
        message = await ctx.send(
            f"Please select a set type for **{formatted_name}**:",
            view=view,
        )
        GiveSet.awaiting_response[unique_id] = {
            "message_id": message.id,
            "user_id": ctx.author.id,
            "sets": sets,
            "url": url,
        }

    @staticmethod
    async def set_selection(ctx, unique_id, set_index, set_name, url):
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
                    if unique_id in GiveSet.awaiting_response:
                        context = GiveSet.awaiting_response[unique_id]

                        # Check if there's an existing set message to edit
                        if "set_message_id" in context:
                            try:
                                set_message_details = await ctx.channel.fetch_message(
                                    context["set_message_id"]
                                )
                                await set_message_details.edit(
                                    content=f"```{set_data}```"
                                )
                            except discord.NotFound:
                                # If the set data message is gone, send a new one
                                new_set_message_details = await ctx.send(
                                    f"```{set_data}```"
                                )
                                context["set_message_id"] = new_set_message_details.id
                        else:
                            # If no set message exists, send a new one and store its ID
                            new_set_message_details = await ctx.send(
                                f"```{set_data}```"
                            )
                            context["set_message_id"] = new_set_message_details.id
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
    async def fetch_set(pokemon: str, generation: str = None) -> tuple:
        # Initializes a headless browser to fetch sets from Smogon
        driver = None
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--log-level=3")
            driver = webdriver.Chrome(options=chrome_options)

            if generation:
                # If generation is specified but no specific set, fetch all sets for the first format found
                gen_code = get_gen(generation)
                if gen_code:
                    url = f"https://www.smogon.com/dex/{gen_code}/pokemon/{pokemon.lower()}/"
                    driver.get(url)
                    if is_valid_pokemon(driver, pokemon):
                        sets = get_set_names(driver)
                        if sets:
                            return None, sets, url
                        else:
                            return None, None, None
                    else:
                        return (
                            f'Pokemon "{pokemon}" not found in Generation "{generation}".',
                            None,
                            None,
                        )
                else:
                    return f"Generation '{generation}' not found.", None, None
            else:
                # If no generation is provided, use fetch_general_set to find the most recent generation
                sets, url = fetch_general_set(driver, pokemon)
                return None, sets, url
        except Exception as e:
            return f"An error occurred: {str(e)}", None, None
        finally:
            if driver:
                driver.quit()
