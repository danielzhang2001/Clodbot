import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
from commands.analyze import Analyze

intents = discord.Intents.default()
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix="Clodbot, ", intents=intents)

#


@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")


# Analyze command
@bot.command(name='analyze')
async def analyze_replay(ctx, *args):
    replay_link = ' '.join(args)
    message = await Analyze.analyze_replay(replay_link)
    if message:
        await ctx.send(message)
    else:
        await ctx.send("No data found in this replay.")

# Running Discord bot
load_dotenv()
bot_token = os.environ['DISCORD_BOT_TOKEN']
bot.run(bot_token)
