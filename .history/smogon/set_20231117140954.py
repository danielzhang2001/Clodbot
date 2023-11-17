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
    # Check if the Pokemon name exists on the page (with and without hyphen replaced by space).
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


def format_name(pokemon: str) -> str:
    # Format the Pokémon name to have each word (split by hyphen) start with a capital letter and the rest lowercase.
    return "-".join(word.capitalize() for word in pokemon.split("-"))


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
        print(f"Get All Set Names Error: {str(e)}")
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


def fetch_general_sets(driver: webdriver.Chrome, pokemon: str) -> tuple:
    # Finds all pokemon set names with the url of the page given the most recent generation if only Pokemon name is provided
    for gen in reversed(get_gen_dict().values()):
        url = f"https://www.smogon.com/dex/{gen}/pokemon/{pokemon.lower()}/"
        driver.get(url)
        if is_valid_pokemon(driver, pokemon):
            sets = get_set_names(driver)
            if sets:
                return sets, url
            else:
                return None, None
    return None, f'Pokemon "{pokemon}" not found in any generation.'


def fetch_specific_set(
    driver: webdriver.Chrome, pokemon: str, generation: str, format: str, set_name: str
) -> str:
    # Finds specific pokemon set names with the url of the page given the most recent generation if only Pokemon name is provided
    if generation.lower() not in get_gen_dict():
        return f'Generation "{generation}" not found.'

    url = f"https://www.smogon.com/dex/{get_gen(generation)}/pokemon/{pokemon.lower()}/{format.lower()}/"
    driver.get(url)

    if not is_valid_pokemon(driver, pokemon):
        return f'Pokemon "{pokemon}" not found or doesn’t exist in Generation "{generation}".'

    if driver.current_url != url:
        return f'Format "{format}" not found.'

    if not get_export_btn(driver, set_name):
        return f'Set "{set_name}" not found.'

    set_data = get_textarea(driver, pokemon)
    return f"```{set_data}```" if set_data else None
