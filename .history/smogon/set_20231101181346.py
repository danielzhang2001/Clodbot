"""
General functions in scraping Pokemon Smogon sets.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_gen_dict() -> dict:
    """Returns generation dictionary."""
    return {
        "gen1": "rb",
        "gen2": "gs",
        "gen3": "rs",
        "gen4": "dp",
        "gen5": "bw",
        "gen6": "xy",
        "gen7": "sm",
        "gen8": "ss",
        "gen9": "sv"
    }

def get_gen(generation: str) -> str:
    """Retrieves generation dictionary."""
    return get_gen_dict().get(generation.lower())

def is_valid_pokemon(driver: webdriver.Chrome, pokemon: str) -> bool:
    """Check if the Pokemon name exists on the page."""
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, 
                f"//h1[translate(text(), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ')='{pokemon.upper().replace('-', ' ')}']"))
        )
        return True
    except:
        return False

def get_export_btn(driver: webdriver.Chrome, set: str) -> bool:
    """Finds and clicks export button for the specific set."""
    try:
        set_header = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, f"//h1[translate(text(),'abcdefghijklmnopqrstuvwxyz','ABCDEFGHIJKLMNOPQRSTUVWXYZ') = '{set.upper()}']"))
        )
        export_button = WebDriverWait(set_header, 10).until(
            EC.presence_of_element_located((By.XPATH, "./preceding-sibling::button[contains(@class, 'ExportButton')][1]"))
        )
        export_button.click()
        return True
    except Exception as e:
        print(f"Export Button Error: {str(e)}")
        return False

def get_first_set_name(driver: webdriver.Chrome) -> str:
    """Finds the first available set name."""
    try:
        # Find the first export button
        export_button = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//button[contains(@class, 'ExportButton')]"))
        )[0]
        # Get the set name, which is the element right below the export button
        set_name = WebDriverWait(export_button, 10).until(
            EC.presence_of_element_located((By.XPATH, "./following-sibling::h1"))
        )
        return set_name.text
    except Exception as e:
        print(f"Could not find the first set name: {str(e)}")
        return ""

def get_textarea(driver: webdriver.Chrome, pokemon: str) -> str:
    """Finds and returns text area contents."""
    try:
        textarea = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "textarea"))
        )
        print(f"Textarea found for {pokemon}!")
        return textarea.text
    except Exception as e_textarea:
        print(f"Textarea Error: {str(e_textarea)}")
        return None