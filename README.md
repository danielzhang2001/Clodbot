# Your Pokemon Utility Bot

## About:

A Pokemon bot to keep track of stats from Showdown, update those stats into Google Sheets and give sets from Smogon.

## Bot Usage:

- **Clodbot, analyze (Pokemon Showdown Replay Link)** to display the stats from the replay on Discord.

- **Clodbot, sheet set (Google Sheets Link)** to set the default Google Sheets link for future "sheet" commands.

- **Clodbot, sheet default** to display the default sheet link on Discord.

- **Clodbot, sheet update (Optional Google Sheets Link) (Pokemon Showdown Replay Link)** to update the stats from the replay onto a "Stats" sheet in the link. Uses default link if Google Sheets link not provided.

- **Clodbot, sheet delete (Optional Google Sheets Link) (Player Name)** to delete the stats section with Player Name from the "Stats" sheet in the link. Uses default link if Google Sheets link not provided.

- **Clodbot, sheet list (Optional Google Sheets Link) ["Players" OR "Pokemon"]** to display either all Player stats (if "Players") or all Pokemon stats (if "Pokemon") from the "Stats" sheet in the link on Discord. Uses default link if Google Sheets link not provided.

- **Clodbot, giveset (Pokemon) (Optional Generation) (Optional Format) [Multiple Using Commas]** to display prompt(s) for set selection based on the provided parameters. Uses first format found if format not provided and latest generation if generation not provided.

- **Clodbot, giveset random (Optional Number)** to display random set(s) for the specified amount of random Pokemon. Displays one if no number given. 
