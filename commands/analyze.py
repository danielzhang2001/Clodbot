
"""
The functions to analyze a Pokemon Showdown replay link and display stats.
"""

# pylint: disable=import-error
# pylint: disable=wildcard-import,unused-wildcard-import
import requests  # type: ignore
import json
from showdown.replay import *
from errors import *


class Analyze:
    @staticmethod
    async def analyze_replay(replay_link: str) -> str:
        # Analyzes a replay link and returns its formatted message.
        result = await Analyze.get_replay_details(replay_link)
        return result["message"]
    
    @staticmethod
    async def get_replay_details(replay_link: str) -> dict:
        # Analyzes a replay and returns its message and underlying statistics.
        try:
            response = requests.get(replay_link + ".json")
            response.raise_for_status()
            json_data = json.loads(response.text)
        except requests.exceptions.RequestException:
            raise InvalidReplay(replay_link)
        players = get_replay_players(json_data)
        revives = get_revives(json_data)
        winner = get_winner(json_data)
        loser = get_loser(json_data)
        stats, passive_kills = get_stats(json_data)
        difference = get_difference(players, winner, revives, stats)
        message = create_message(
            players, winner, loser, difference, stats, passive_kills
        )
        return {
            "message": message,
            "players": players,
            "winner": winner,
            "stats": stats,
        }

    @staticmethod
    def aggregate_replays(results: list) -> str:
        # Combines replay outcomes and Pokemon statistics by player.
        players = {}
        matchups = {}
        for result in results:
            replay_players = result["players"]
            winner = result["winner"]
            stats = result["stats"]
            player_keys = {
                player_key: name.casefold()
                for player_key, name in replay_players.items()
            }
            matchup_key = tuple(sorted(player_keys.values()))
            if matchup_key not in matchups:
                matchups[matchup_key] = {
                    "players": list(player_keys.values()),
                    "wins": {key: 0 for key in player_keys.values()},
                }
            matchups[matchup_key]["wins"][winner.casefold()] += 1
            for player_key, name in replay_players.items():
                normalized_name = player_keys[player_key]
                if normalized_name not in players:
                    players[normalized_name] = {
                        "name": name,
                        "pokemon": {},
                    }
                aggregated_pokemon = players[normalized_name]["pokemon"]
                for pokemon, data in stats[player_key].items():
                    pokemon_key = pokemon.casefold()
                    if pokemon_key not in aggregated_pokemon:
                        aggregated_pokemon[pokemon_key] = {
                            "name": pokemon,
                            "kills": 0,
                            "deaths": 0,
                        }
                    aggregated_pokemon[pokemon_key]["kills"] += data["kills"]
                    aggregated_pokemon[pokemon_key]["deaths"] += data["deaths"]
        message = "**AGGREGATED RESULTS:**\n\n"
        for matchup in matchups.values():
            first_key, second_key = matchup["players"]
            first_wins = matchup["wins"][first_key]
            second_wins = matchup["wins"][second_key]
            if second_wins > first_wins:
                first_key, second_key = second_key, first_key
                first_wins, second_wins = second_wins, first_wins
            first_name = players[first_key]["name"]
            second_name = players[second_key]["name"]
            message += (
                f"**OUTCOME: ||{first_name} "
                f"{first_wins}-{second_wins} {second_name}||**\n"
            )
        message += "\n"
        for player in players.values():
            message += f"**{player['name']}'s Pokemon:**\n"
            pokemon_lines = []
            for pokemon in player["pokemon"].values():
                pokemon_lines.append(
                    f"{pokemon['name']} "
                    f"(Kills: {pokemon['kills']}, "
                    f"Deaths: {pokemon['deaths']})"
                )
            pokemon_message = "\n".join(pokemon_lines)
            message += f"||```\n{pokemon_message}\n```||\n"
        return message