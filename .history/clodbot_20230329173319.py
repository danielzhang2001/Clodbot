import discord
from discord.ext import commands
import requests
import re

intents = discord.Intents.default()
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix="Clodbot, ", intents=intents)


@bot.event
async def on_ready():
print(f"{bot.user.name} has connected to Discord!")


@bot.command(name='analyze')
async def analyze_replay(ctx, *args):
replay_link = ' '.join(args)
