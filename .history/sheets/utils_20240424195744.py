"""
General utility functions for loading
"""

import json


def save_default_links(default_links):
    """Saves the default sheet links to a JSON file."""
    try:
        with open("default_links.json", "w") as file:
            json.dump(default_links, file)
    except IOError as e:
        print(f"Error saving default links: {e}")


def load_default_links():
    """Loads the default sheet links from a JSON file."""
    try:
        with open("default_links.json", "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading default links: {e}")
        return {}  # Return an empty dictionary if the file does not exist or is corrupt
