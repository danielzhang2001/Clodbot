from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from smogon.set import *
from discord import ui, ButtonStyle


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
        view = ui.View()
        for index, set_name in enumerate(sets):
            button = ui.Button(label=set_name, custom_id=f"set_{index}")
            view.add_item(button)

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
    ) -> tuple:
        # Refactored to handle different scenarios internally and return appropriate data.
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
