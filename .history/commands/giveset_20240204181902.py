"""
The function to give Pokemon sets from Smogon based on different types of criteria.
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from smogon.set import *
from discord import ui, ButtonStyle
import uuid


# In giveset.py


class GiveSet:
    awaiting_response = {}  # Keeps track of ongoing selections

    @staticmethod
    async def set_prompt(ctx, pokemon, sets, url, multiple_pokemon=False):
        unique_id = str(uuid.uuid4())
        message_id = None

        # For multiple Pokémon, this will be handled differently
        if multiple_pokemon:
            existing_context = [
                key
                for key, val in GiveSet.awaiting_response.items()
                if val["user_id"] == ctx.author.id and val.get("multiple_pokemon")
            ]
            if existing_context:
                unique_id = existing_context[0]
                message_id = GiveSet.awaiting_response[unique_id]["message_id"]
                GiveSet.awaiting_response[unique_id]["sets"][pokemon] = sets
            else:
                GiveSet.awaiting_response[unique_id] = {
                    "user_id": ctx.author.id,
                    "sets": {pokemon: sets},
                    "selected_sets": {},
                    "multiple_pokemon": True,
                    "message_id": None,  # This will be set after sending the initial message
                }
        else:
            GiveSet.awaiting_response[unique_id] = {
                "user_id": ctx.author.id,
                "sets": sets,
                "url": url,
                "multiple_pokemon": False,
                "message_id": None,  # For single Pokémon, this behaves as before
            }

        # Send or update the message depending on if it's a new prompt or an existing one
        if message_id:
            # Update the existing message with new sets or selection
            await GiveSet.update_message(ctx, unique_id)
        else:
            # Send a new message and store its ID
            message = await ctx.send("Select a set:")
            GiveSet.awaiting_response[unique_id]["message_id"] = message.id

    @staticmethod
    async def set_selection(ctx, unique_id, pokemon, set_index):
        # Logic to handle set selection, similar to before but with updates for multiple Pokémon
        context = GiveSet.awaiting_response[unique_id]
        if context["multiple_pokemon"]:
            selected_set = context["sets"][pokemon][set_index]
            context["selected_sets"][pokemon] = selected_set
            await GiveSet.update_message(
                ctx, unique_id
            )  # Update the cumulative message
        else:
            # Handle single Pokémon selection as before
            pass

    @staticmethod
    async def update_message(ctx, unique_id):
        # Logic to update the message with selected sets or prompt for selection
        context = GiveSet.awaiting_response[unique_id]
        if context["multiple_pokemon"]:
            sets_text = "\n\n".join(context["selected_sets"].values())
            await ctx.channel.fetch_message(context["message_id"]).edit(
                content=sets_text
            )
        else:
            # Update message for single Pokémon if needed
            pass

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
