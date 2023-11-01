from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from smogon.set import *

class GiveSet:
    
    @staticmethod
async def fetch_set(pokemon_name: str, generation: str, format: str, set_name: str) -> str:
    """Fetch the set from Smogon for the given Pokemon name, generation, format, and set name."""
    url = f"https://www.smogon.com/dex/{get_gen(generation)}/pokemon/{pokemon_name.lower()}/{format.lower()}/"
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--log-level=3")
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)
    if driver.current_url != url:
        print(f"format not found") 
        driver.quit()
        return None
    if not get_set_export_btn(driver, set_name):
        driver.quit()
        return None
    set_data = get_textarea(driver, pokemon_name)
    driver.quit()
    return set_data