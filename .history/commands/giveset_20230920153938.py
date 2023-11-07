"""
The function to give a Pokemon set from Smogon.
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from smogon.set import *

class GiveSet:
    
    @staticmethod
    async def fetch_set(pokemon: str, generation: str, format: str, set: str) -> str:
        """Fetch the set from Smogon for the given Pokemon name, generation, format, and set name."""
        
        url = f"https://www.smogon.com/dex/{get_gen(generation)}/pokemon/{pokemon.lower()}/{format.lower()}/"
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--log-level=3")
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        if generation.lower() not in get_gen_dict():
            driver.quit()
            return f"Generation \"{generation}\" not found."
        if not is_valid_pokemon(driver, pokemon):
            driver.quit()
            return f"Pokemon \"{pokemon}\" not found or doesn't exist in Generation \"{generation}\"."
        if driver.current_url != url:
            driver.quit()
            return f"Format \"{format}\" not found."
        if not get_export_btn(driver, set):
            driver.quit()
            return f"Set \"{set}\" not found."
        set_data = get_textarea(driver, pokemon)
        driver.quit()
        return set_data
