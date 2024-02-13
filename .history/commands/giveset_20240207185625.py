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
    async def set_prompt(ctx, pokemon_data):
        # Displays prompt with buttons for selection of Pokemon sets
        unique_id = str(uuid.uuid4())
        views = []
        prompt = ""
        if len(pokemon_data) > 1:
            formatted_names = [
                "-".join(
                    part.capitalize() if len(part) > 1 else part
                    for part in pokemon[0].split("-")
                )
                for pokemon in pokemon_data
            ]
            prompt += f"Please select set types for {', '.join(['**' + name + '**' for name in formatted_names])}:\n\n"
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
                    button_label = set_name
                    button_id = f"set_{unique_id}_{pokemon}_{index}"
                    button = ui.Button(label=button_label, custom_id=button_id)
                    view.add_item(button)
                views.append(view)
        else:
            view = ui.View()
            for pokemon, sets, url in pokemon_data:
                formatted_name = "-".join(
                    part.capitalize() if len(part) > 1 else part
                    for part in pokemon.split("-")
                )
                prompt += f"Please select a set type for **{formatted_name}**:\n"
                for index, set_name in enumerate(sets):
                    button_label = set_name
                    button_id = f"set_{unique_id}_{pokemon}_{index}"
                    button = ui.Button(label=button_label, custom_id=button_id)
                    view.add_item(button)
                prompt += "\n"
            views.append(view)
        message = await ctx.send(prompt.strip(), view=views[0])
        for view in views[1:]:
            await ctx.send(view=view)
        GiveSet.awaiting_response[unique_id] = {
            "user_id": ctx.author.id,
            "pokemon_data": pokemon_data,
            "messages": {},
        }

    @staticmethod
    async def set_selection(interaction, unique_id, set_index, set_name, url, pokemon):
        context = GiveSet.awaiting_response.get(unique_id)
        if not context:
            await interaction.followup.send(
                "Session expired or not found.", ephemeral=True
            )
            return

        # Retrieve or initialize the combined sets message content
        combined_sets_message = context.get("combined_sets_message", "")

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
                    # Format and append the new set data to the combined message
                    combined_sets_message += f"{set_data}\n\n"
                    context["combined_sets_message"] = combined_sets_message

                    channel = interaction.client.get_channel(interaction.channel_id)
                    final_message_content = f"```{combined_sets_message}```"
                    # Update or send new combined message
                    if "combined_message_id" in context:
                        message_id = context["combined_message_id"]
                        message = await channel.fetch_message(message_id)
                        await message.edit(content=final_message_content)
                    else:
                        message = await channel.send(final_message_content)
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
