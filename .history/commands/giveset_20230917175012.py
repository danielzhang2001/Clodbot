# giveset.py

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class GiveSet:
    
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

    @staticmethod
    async def fetch_smogon_set(pokemon_name: str, generation: str, format: str) -> str:
        """Fetch the first set from Smogon for the given Pokemon name and generation using Selenium."""
        
        url = f"https://www.smogon.com/dex/{GiveSet.gen_dict[generation.lower()]}/pokemon/{pokemon_name.lower()}/{format.lower()}/"
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--log-level=3")  # Suppress logging
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
    
        # Print the current URL to see if we're on the right page
        print(f"Currently at URL: {driver.current_url}")

        # Checks if format exists
        # Can only be the format since format is the only one that can be excluded
        if driver.current_url != url:
            print(f"format not found") 
            driver.quit()
            return None
        
        # Explicitly wait up to 10 seconds until the ExportButton is present
        try:
            export_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "ExportButton"))
            )
            print(f"Export button found for {pokemon_name}!")
            export_button.click()

            # Now wait for the textarea to appear
            try:
                textarea = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "textarea"))
                )
                print(f"Textarea found for {pokemon_name}!")
                set_data = textarea.text
                driver.quit()
                return set_data
            except Exception as e_textarea:
                print(f"No Textarea found for {pokemon_name}.")
                print(f"Textarea Error: {str(e_textarea)}")
                driver.quit()
                return None

        except Exception as e:
            print(f"No Export button found for {pokemon_name}.")
            print(f"Error: {str(e)}")
            driver.quit()
            return None
