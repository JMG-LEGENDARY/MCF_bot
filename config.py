import discord
from discord.ext import commands

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)
embed = discord.Embed()

token = ['M', 'T', 'I', '5', 'N', 'z', 'U', 'y', 'M', 'D', 'U', '0', 'M', 'z', 'Q', 'x', 'O', 'D', 'g', 'x', 'N', 'D', 'U', 'w', 'N', 'Q', '.', 'G', 'f', 'P', 'T', 'Z', 'S', '.', 'Q', 'h', '1', '4', 'p', 'K', 'i', 'f', 'J', 'r', 'l', 'o', 'k', 'v', '1', '4', 'k', 'g', 'Q', 'R', 'T', 'H', 'f', 'b', 'U', 'c', 'a', 'C', 'p', 'l', 'L', 'r', 'w', 'U', '9', 'R', 'x', 'A']
for i in token:
    TOKEN = ''.join(token)

MCF_ID = 993457171759120424
guild = bot.get_guild(MCF_ID)

gestion_mc_id = 1302323091002626170
gestion_console_id = 1512030104690102412
gestion_debian_id = 1512030347586441226

logs_channel_id = 1324057375845646408
commands_channel_id = 1315286059189534771

boutique_channel_id = 1325807725422317618
economie_channel_id = 1325416392379334727

quetes_channel_id = 1303751988630257674
info_channel_id = 1258468979433934969

signalement_channel_id = 1308826785563152414
modo_only_channel_id = 1258297452763680799

