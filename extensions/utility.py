import discord
from discord.ext import commands
import platform


# Define a Cog for utility commands
class UtilityCog(commands.Cog):
    # Initialize the cog
    def __init__(self, bot):
        self.bot = bot

    # Ping command to check latency
    @commands.command(name='ping')
    async def ping(self, ctx):
        # Get and send the latency in milliseconds
        await ctx.send(f'Pong! {round(self.bot.latency * 1000)}ms')

    # Info command to display various information
    @commands.command(name='info')
    async def info(self, ctx):
        # Create an embed to display utility information
        embed = discord.Embed(title=f"{ctx.guild.name}", description="Utility Information",
                              timestamp=ctx.message.created_at, color=discord.Color.blue())

        # Add various fields to the embed
        embed.add_field(name="Bot Version", value="1.0")
        embed.add_field(name="Discord.py Version", value=discord.__version__)
        embed.add_field(name="Python Version", value=platform.python_version())
        embed.add_field(name="Total Members", value=len(ctx.guild.members))
        embed.add_field(name="Total Text Channels", value=len(ctx.guild.text_channels))
        embed.add_field(name="Total Voice Channels", value=len(ctx.guild.voice_channels))

        # Send the embed
        await ctx.send(embed=embed)


# Function to add the cog to the bot
async def setup(bot):
    await bot.add_cog(UtilityCog(bot))