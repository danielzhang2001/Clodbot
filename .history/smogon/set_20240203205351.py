"""
General functions in scraping Pokemon Smogon sets.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


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
        selected_format_element = driver.find_element(
            By.CSS_SELECTOR, ".PokemonPage-StrategySelector ul li span.is-selected"
        )
        current_url = driver.current_url
        url_format = current_url.split("/")[-2]
        return format.lower() == url_format.lower()
    except Exception as e:
        print(f"Error checking format: {str(e)}")
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


def get_set_names(driver: webdriver.Chrome) -> list:
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


def fetch_set_pokemon(driver: webdriver.Chrome, pokemon: str) -> tuple:
    # Finds all Pokemon set names for a given Pokemon assuming most recent Generation and first Format found.
    for gen in reversed(get_gen_dict().values()):
        url = f"https://www.smogon.com/dex/{gen}/pokemon/{pokemon.lower()}/"
        driver.get(url)
        if is_valid_pokemon(driver, pokemon) and has_export_buttons(driver):
            sets = get_set_names(driver)
            if sets:
                return sets, url
            else:
                return None, None
    return None, None


def fetch_set_generation(
    driver: webdriver.Chrome, pokemon: str, generation: str
) -> tuple:
    # Finds all Pokemon set names for a given Pokemon and given Generation assuming first Format found.
    gen_code = get_gen_dict().get(generation.lower())
    if gen_code:
        url = f"https://www.smogon.com/dex/{gen_code}/pokemon/{pokemon.lower()}/"
        driver.get(url)
        if is_valid_pokemon(driver, pokemon):
            sets = get_set_names(driver)
            if sets:
                return sets, url
            else:
                return None, None
    else:
        return None, None


def fetch_set_format(
    driver: webdriver.Chrome, pokemon: str, generation: str, format: str
) -> tuple:
    # Finds all Pokemon set names for a given Pokemon, given Generation and given Format.
    gen_code = get_gen_dict().get(generation.lower())
    if gen_code:
        url = f"https://www.smogon.com/dex/{gen_code}/pokemon/{pokemon.lower()}/{format.lower()}/"
        driver.get(url)
        if is_valid_pokemon(driver, pokemon) and is_valid_format(driver, format):
            sets = get_set_names(driver)
            return sets, url
        else:
            return None, None
    else:
        return None, None


def fetch_sets(
    driver: webdriver.Chrome, pokemon: str, generation: str = None, format: str = None
) -> tuple:
    """
    Fetches all Pokemon set names based on provided criteria.
    - Validates Pokemon name, generation, and format sequentially.
    - Fetches sets based on the combination of criteria provided.
    """
    # Check if the Pokemon is valid
    if not is_valid_pokemon(driver, pokemon):
        return None, None  # Pokemon is not valid

    # Determine the URL for the generation or use the latest generation if not specified
    gen_code = None
    if generation:
        gen_code = get_gen(generation)
    if not gen_code:
        return None, None  # Generation is not valid or sets not found in any generation

    url = f"https://www.smogon.com/dex/{gen_code}/pokemon/{pokemon.lower()}/"

    # If format is specified, append it to the URL and check if it's valid
    if format:
        url += f"{format.lower()}/"
        if not is_valid_format(driver, format):
            return None, None  # Format is not valid

    # Navigate to the URL
    driver.get(url)

    # Ensure there are export buttons (sets are available)
    if not has_export_buttons(driver):
        return None, None  # No sets found

    # Fetch set names
    sets = get_set_names(driver)
    return sets, url


def find_latest_generation_with_sets(driver: webdriver.Chrome, pokemon: str) -> str:
    """
    Finds the most recent generation that has sets available for the given Pokemon.
    Returns the generation code if found, else None.
    """
    for gen, code in reversed(get_gen_dict().items()):
        url = f"https://www.smogon.com/dex/{code}/pokemon/{pokemon.lower()}/"
        driver.get(url)
        if is_valid_pokemon(driver, pokemon) and has_export_buttons(driver):
            return code
    return None
