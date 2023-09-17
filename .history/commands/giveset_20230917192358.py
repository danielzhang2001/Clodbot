from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from set import Set

class GiveSet:
    
    @staticmethod
    async def fetch_set(pokemon_name: str, generation: str, format: str) -> str:
        """Fetch the first set from Smogon for the given Pokemon name, generation and format."""
        url = f"https://www.smogon.com/dex/{Set.get_gen(generation)}/pokemon/{pokemon_name.lower()}/{format.lower()}/"
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--log-level=3")  # Suppress logging
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)

        # Checks if format exists
        # Can only be the format since format is the only one that can be excluded
        if driver.current_url != url:
            print(f"format not found") 
            driver.quit()
            return None
        
        if not Set.get_export_btn(driver, pokemon_name):
            driver.quit()
            return None

        set_data = Set.get_textarea(driver, pokemon_name)
        driver.quit()

        return set_data