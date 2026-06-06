import discord
from discord.ext import commands

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)
embed = discord.Embed()

token = ['M', 'T', 'I', '5', 'N', 'z', 'U', 'y', 'M', 'D', 'U', '0', 'M', 'z', 'Q', 'x', 'O', 'D', 'g', 'x', 'N', 'D', 'U', 'w', 'N', 'Q', '.', 'G', 'f', 'P', 'T', 'Z', 'S', '.', 'Q', 'h', '1', '4', 'p', 'K', 'i', 'f', 'J', 'r', 'l', 'o', 'k', 'v', '1', '4', 'k', 'g', 'Q', 'R', 'T', 'H', 'f', 'b', 'U', 'c', 'a', 'C', 'p', 'l', 'L', 'r', 'w', 'U', '9', 'R', 'x', 'A']
for i in token:
    TOKEN = ''.join(token)
print(TOKEN)

MCF_ID = 993457171759120424
guild = bot.get_guild(MCF_ID)


