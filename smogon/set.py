"""
General functions in scraping Pokemon Smogon sets.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_gen(generation: str) -> str:
    """Retrieves generation dictionary."""
    gen_dict = {
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
    return gen_dict[generation.lower()]

def get_export_btn(driver: webdriver.Chrome, pokemon_name: str) -> bool:
    """Finds and clicks export button."""
    try:
        export_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "ExportButton"))
        )
        print(f"Export button found for {pokemon_name}!")
        export_button.click()
        return True
    except Exception as e:
        print(f"No Export button found for {pokemon_name}.")
        print(f"Error: {str(e)}")
        return False

def get_textarea(driver: webdriver.Chrome, pokemon_name: str) -> str:
    """Finds and returns text area contents."""
    try:
        textarea = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "textarea"))
        )
        print(f"Textarea found for {pokemon_name}!")
        return textarea.text
    except Exception as e_textarea:
        print(f"No Textarea found for {pokemon_name}.")
        print(f"Textarea Error: {str(e_textarea)}")
        return None