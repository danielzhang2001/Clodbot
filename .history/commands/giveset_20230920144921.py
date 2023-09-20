from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from smogon.set import *

class GiveSet:
    
    @staticmethod
    async def fetch_set(pokemon_name: str, generation: str, format: str, set_name: str) -> str:
        """Fetch the set from Smogon for the given Pokemon name, generation, format, and set name."""
        # Check if generation exists
        url = f"https://www.smogon.com/dex/{get_gen(generation)}/pokemon/{pokemon_name.lower()}/{format.lower()}/"
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--log-level=3")
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        # Check if Pokemon is valid
        if not is_valid_pokemon(driver, pokemon_name):
            driver.quit()
            return f"Pokemon {pokemon_name} Not Found."
        # Check if Generation is valid
        if generation.lower() not in get_gen_dict():
            driver.quit()
            return f"Generation {generation} Not Found."
        # Check if Format is valid
        if driver.current_url != url:
            driver.quit()
            return f"Format {format} Not Found."
        # Check if Set is valid
        if not get_export_btn(driver, set_name):
            driver.quit()
            return f"Set Type {set_name} Not Found."
        set_data = get_textarea(driver, pokemon_name)
        driver.quit()
        return set_data
