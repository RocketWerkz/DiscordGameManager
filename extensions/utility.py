import discord
from discord.ext import commands
import platform


class UtilityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send('Something went wrong while running the command.')

    @commands.command(name='ping', description='Checks the latency between the bot and the server.')
    async def ping(self, ctx):
        await ctx.send(f'Pong! {round(self.bot.latency * 1000)}ms')

    @commands.guild_only()
    @commands.command(name='info', description='Shows information about the bot.')
    async def info(self, ctx):
        embed = discord.Embed(title=f"{ctx.guild.name}", description="Utility Information",
                              timestamp=ctx.message.created_at, color=discord.Color.blue())
        embed.add_field(name="Bot Version", value="1.0")
        embed.add_field(name="Discord.py Version", value=discord.__version__)
        embed.add_field(name="Python Version", value=platform.python_version())
        embed.add_field(name="Total Members", value=len(ctx.guild.members))
        embed.add_field(name="Total Text Channels", value=len(ctx.guild.text_channels))
        embed.add_field(name="Total Voice Channels", value=len(ctx.guild.voice_channels))

        if ctx.channel.permissions_for(ctx.guild.me).embed_links:
            await ctx.send(embed=embed)
        else:
            await ctx.send('I do not have permission to send embeds.')


async def setup(bot):
    await bot.add_cog(UtilityCog(bot))
