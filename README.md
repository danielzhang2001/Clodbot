---------------------------------------------------------
# Clodbot
Your friendly amphibian Pokemon Showdown Stat Tracker
---------------------------------------------------------

About:

A Pokemon Showdown bot to keep track of stats.
As of right now, it displays the winner of a match, point differential and kill/death ratios for each Pokemon by feeding it a Pokemon Showdown replay.

---------------------------------------------------------

Setup:

Inviting the bot into your server locally:

1) Go into https://discord.com/developers/applications
2) Create a bot and go into it
3) Click on OAuth2
4) Go into URL Generator
5) Check the “bot” checkbox in Scopes
6) Check the “Send Messages” checkbox in Text Permissions
7) Copy the generated URL and select the server you want to add the bot into

Starting up the bot:

1) Clone this repository through an IDE of your choice
2) Go into the .env file and replace the token with the token from the bot you created
3) Under the Bot settings in the Discord developer app portal, also activate "Message Content Intent"
4) Run clodbot.py in your IDE

Using the bot:

1) In the channel the bot is in, type “Clodbot, analyze (Pokemon Showdown Replay Link)” to display the stats!
