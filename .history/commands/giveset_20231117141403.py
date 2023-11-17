from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from smogon.set import *


class GiveSet:
    awaiting_response = {}

    @staticmethod
    async def set_prompt(ctx, pokemon, sets, url):
        # Sends a message prompting the user to select a set and waits for their response.
        formatted_sets = (
            "```\n"
            + "\n".join([f"{index+1}) {s}" for index, s in enumerate(sets)])
            + "\n```"
        )
        message = await ctx.send(
            f"Please specify set type for **{'-'.join(part.capitalize() if len(part) > 1 else part for part in pokemon.split('-'))}**:\n{formatted_sets}"
        )
        GiveSet.awaiting_response[ctx.channel.id] = {
            "message_id": message.id,
            "user_id": ctx.author.id,
            "sets": sets,
            "url": url,
        }

    @staticmethod
    async def set_selection(ctx, message):
        # Handles the user's selection of a set after prompting.
        channel_id = ctx.channel.id
        driver = None
        if channel_id in GiveSet.awaiting_response:
            context = GiveSet.awaiting_response[channel_id]
            url = context["url"]
            if message.author.id == context["user_id"] and message.content.isdigit():
                set_index = int(message.content) - 1
                if 0 <= set_index < len(context["sets"]):
                    try:
                        chrome_options = Options()
                        chrome_options.add_argument("--headless")
                        chrome_options.add_argument("--log-level=3")
                        driver = webdriver.Chrome(options=chrome_options)
                        driver.get(url)
                        # Fetch the set data
                        set_name = context["sets"][set_index]
                        if get_export_btn(driver, set_name):
                            set_data = get_textarea(driver, set_name)
                            if set_data:
                                await ctx.send(f"```{set_data}```")
                            else:
                                await ctx.send("Error fetching set data.")
                        else:
                            await ctx.send("Error finding set. Please try again.")
                    except Exception as e:
                        await ctx.send(f"An error occurred: {str(e)}")
                    finally:
                        if driver:
                            driver.quit()
                else:
                    await ctx.send(
                        "Invalid selection. Please choose a valid set number."
                    )
                del GiveSet.awaiting_response[channel_id]

    @staticmethod
    async def fetch_set(
        pokemon: str, generation: str = None, format: str = None, set: str = None
    ) -> str:
        # Fetch the set from Smogon for the given Pokemon name, generation, format, and set name.
        # If only Pokemon given, assume most recent generation and first format found and give prompt on all possible sets for user to choose.
        driver = None
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--log-level=3")
            driver = webdriver.Chrome(options=chrome_options)
            name = format_name(pokemon)
            if generation is None and format is None and set is None:
                return fetch_general_sets(driver, name)
            else:
                return fetch_specific_set(driver, name, generation, format, set)
        except Exception as e:
            return f"An error occurred: {str(e)}"
        finally:
            if driver:
                driver.quit()