"""
General functions in scraping Pokemon Smogon sets.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from discord import ui, ButtonStyle


def get_gen_dict() -> dict:
    # Returns generation dictionary.
    return {
        "gen1": "rb",
        "gen2": "gs",
        "gen3": "rs",
        "gen4": "dp",
        "gen5": "bw",
        "gen6": "xy",
        "gen7": "sm",
        "gen8": "ss",
        "gen9": "sv",
    }


def get_gen(generation: str) -> str:
    # Retrieves generation dictionary.
    return get_gen_dict().get(generation.lower())


def get_setnames(driver: webdriver.Chrome) -> list:
    # Finds and returns all set names on the page.
    try:
        export_buttons = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "ExportButton"))
        )
        set_names = []
        for export_button in export_buttons:
            set_header = export_button.find_element(By.XPATH, "./following-sibling::h1")
            set_names.append(set_header.text)
        return set_names
    except Exception as e:
        print(f"Error in retrieving set names: {str(e)}")
        return None


def get_export_btn(driver: webdriver.Chrome, set: str) -> bool:
    # Finds and clicks export button for the specific set.
    try:
        set_header = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    f"//h1[translate(text(),'abcdefghijklmnopqrstuvwxyz','ABCDEFGHIJKLMNOPQRSTUVWXYZ') = '{set.upper()}']",
                )
            )
        )
        export_button = WebDriverWait(set_header, 10).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "./preceding-sibling::button[contains(@class, 'ExportButton')][1]",
                )
            )
        )
        export_button.click()
        return True
    except Exception as e:
        print(f"Export Button Error: {str(e)}")
        return False


def get_textarea(driver: webdriver.Chrome, pokemon: str) -> str:
    # Finds and returns text area contents for a Pokemon set.
    try:
        textarea = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "textarea"))
        )
        return textarea.text
    except Exception as e_textarea:
        print(f"Textarea Error: {str(e_textarea)}")
        return None


def get_view(unique_id, pokemon_data):
    # Creates a prompt + buttons for Pokemon sets for a single Pokemon.
    pokemon, sets, url = pokemon_data
    view = ui.View()
    formatted_name = "-".join(
        part.capitalize() if len(part) > 1 else part for part in pokemon.split("-")
    )
    prompt = f"Please select a set type for **{formatted_name}**:\n"
    for index, set_name in enumerate(sets):
        button_id = f"set_{unique_id}_{pokemon}_{index}"
        button = ui.Button(label=set_name, custom_id=button_id)
        view.add_item(button)
    return {formatted_name: view}, prompt


def get_multiview(unique_id, pokemon_data):
    # Creates a prompt + buttons for Pokemon sets for multiple Pokemon.
    views = {}
    formatted_names = [
        "-".join(
            part.capitalize() if len(part) > 1 else part for part in pokemon.split("-")
        )
        for pokemon, _, _ in pokemon_data
    ]
    prompt = f"Please select set types for {', '.join(['**' + name + '**' for name in formatted_names])}:\n\n"
    for pokemon, sets, url in pokemon_data:
        view = ui.View()
        formatted_name = "-".join(
            part.capitalize() if len(part) > 1 else part for part in pokemon.split("-")
        )
        view.add_item(
            ui.Button(
                label=f"{formatted_name}:", style=ButtonStyle.secondary, disabled=True
            )
        )
        for index, set_name in enumerate(sets):
            button_id = f"set_{unique_id}_{pokemon}_{index}"
            button = ui.Button(label=set_name, custom_id=button_id)
            view.add_item(button)
        views[formatted_name] = view
    return views, prompt


def get_setinfo(driver, pokemon, generation=None, format=None):
    # Retrieves the set names and the url with the Driver, Pokemon, Generation (Optional) and Format (Optional) provided.
    if generation:
        gen_code = get_gen(generation)
        if not gen_code:
            return None, None
        url = f"https://www.smogon.com/dex/{gen_code}/pokemon/{pokemon.lower()}/"
        driver.get(url)
        if format:
            url += f"{format.lower()}/"
            driver.get(url)
            if not is_valid_format(driver, format) or not is_valid_pokemon(
                driver, pokemon
            ):
                return None, None
        else:
            if not is_valid_pokemon(driver, pokemon):
                return None, None
        set_names = get_setnames(driver)
        return set_names, url if set_names else (None, None)
    else:
        for gen in reversed(get_gen_dict().values()):
            url = f"https://www.smogon.com/dex/{gen}/pokemon/{pokemon.lower()}/"
            driver.get(url)
            if is_valid_pokemon(driver, pokemon) and has_export_buttons(driver):
                set_names = get_setnames(driver)
                return set_names, url if set_names else (None, None)
    return None, None


def is_valid_pokemon(driver: webdriver.Chrome, pokemon: str) -> bool:
    # Check if the Pokemon name exists on the page.
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    f"//h1[translate(text(), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ')='{pokemon.upper()}']",
                )
            )
        )
        return True
    except:
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        f"//h1[translate(text(), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ')='{pokemon.upper().replace('-', ' ')}']",
                    )
                )
            )
            return True
        except:
            return False


def is_valid_format(driver: webdriver.Chrome, format: str) -> bool:
    # Check if the Pokemon format exists on the page.
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CLASS_NAME, "PokemonPage-StrategySelector")
            )
        )
        format_elements = driver.find_elements(
            By.CSS_SELECTOR, ".PokemonPage-StrategySelector ul li a"
        )
        for element in format_elements:
            href = element.get_attribute("href")
            url_format = href.split("/")[-2]
            if format.lower() == url_format.lower():
                return True
        selected_format = driver.find_element(
            By.CSS_SELECTOR, ".PokemonPage-StrategySelector ul li span.is-selected"
        )
        current_url = driver.current_url
        url_format = current_url.split("/")[-2]
        return format.lower() == url_format.lower()
    except Exception as e:
        print(f"Error checking format: {str(e)}")
        return False


def has_export_buttons(driver: webdriver.Chrome) -> bool:
    # Checks if there are any export buttons on the page.
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "ExportButton"))
        )
        return True
    except Exception as e:
        print(f"No Export Buttons Found: {str(e)}")
        return False


def format_name(pokemon: str) -> str:
    # Format the Pokémon name to have each word (split by hyphen) start with a capital letter and the rest lowercase, except for single letters after hyphen which should remain lowercase.
    formatted_parts = []
    for part in pokemon.split("-"):
        if len(part) > 1:
            formatted_parts.append(part.capitalize())
        else:
            formatted_parts.append(part.lower())
    return "-".join(formatted_parts)


def disable_buttons(view, unique_id, pokemon, set_index, pokemon_data):
    # Disables the button the set is currently on, and also maintains disability of first buttons of each row for multiple Pokemon.
    for index, item in enumerate(view.children):
        item.style = ButtonStyle.secondary
    for item in view.children:
        if item.custom_id == f"set_{unique_id}_{pokemon}_{set_index}":
            item.style = ButtonStyle.primary
            break


async def update_message(context, interaction, unique_id, pokemon, set_index, set_data):
    # Updates the set message and original prompt view with both set content and disabling of buttons after a button is selected.
    if "sets" not in context:
        context["sets"] = {}
    context["sets"][pokemon] = f"{set_data}\n\n"
    sets_message = "".join(context["sets"].values())
    message_content = f"```{sets_message}```"
    channel = interaction.client.get_channel(interaction.channel_id)
    prompt = interaction.message.id
    view = context["views"].get(prompt)
    if not view:
        await interaction.followup.send(
            "Original message view not found.", ephemeral=True
        )
    disable_buttons(view, unique_id, pokemon, set_index, context["pokemon_data"])
    original_message = await channel.fetch_message(prompt)
    await original_message.edit(view=view)
    if "final_message" in context:
        message_id = context["final_message"]
        message = await channel.fetch_message(message_id)
        await message.edit(content=message_content)
    else:
        message = await channel.send(message_content)
        context["final_message"] = message.id
