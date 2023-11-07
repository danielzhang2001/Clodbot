from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from smogon.set import *


class GiveSet:
    @staticmethod
    async def fetch_set(
        pokemon: str, generation: str = None, format: str = None, set: str = None
    ) -> str:
        """Fetch the set from Smogon for the given Pokemon name, generation, format, and set name.
        If only Pokemon given, assume most recent generation and first format found."""
        driver = None
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--log-level=3")
            if generation is None and format is None and set is None:
                driver = webdriver.Chrome(options=chrome_options)
                for gen in reversed(get_gen_dict().values()):
                    url = f"https://www.smogon.com/dex/{gen}/pokemon/{pokemon.lower()}/"
                    driver.get(url)
                    if is_valid_pokemon(driver, pokemon):
                        sets = get_set_names(driver)
                        return sets if sets else "No sets found"
                return f'Pokemon "{pokemon}" not found in any generation.'
            else:
                if generation.lower() not in get_gen_dict():
                    return f'Generation "{generation}" not found.'
                url = f"https://www.smogon.com/dex/{get_gen(generation)}/pokemon/{pokemon.lower()}/{format.lower()}/"
                driver = webdriver.Chrome(options=chrome_options)
                driver.get(url)
                if not is_valid_pokemon(driver, pokemon):
                    return f'Pokemon "{pokemon}" not found or doesn\'t exist in Generation "{generation}".'
                if driver.current_url != url:
                    return f'Format "{format}" not found.'
                if not get_export_btn(driver, set):
                    return f'Set "{set}" not found.'
                set_data = get_textarea(driver, pokemon)
                return set_data
        except Exception as e:
            return f"An error occurred: {str(e)}"
        finally:
            if driver:
                driver.quit()
