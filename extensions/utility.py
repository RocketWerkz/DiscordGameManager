import discord
from discord.ext import commands
import platform
from bot import get_git_info
from bot import BOT_DIRECTORY
import logging


class UtilityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            logging.error(f"Error in command {ctx.command}, {error}")
            await ctx.send('Something went wrong while running the command.')

    @commands.command(name='ping', description='Checks the latency between the bot and the server.')
    async def ping(self, ctx):
        try:
            await ctx.send(f'Pong! {round(self.bot.latency * 1000)}ms')
        except Exception as e:
            logging.error(f"Error in ping: {e}")
            await ctx.send("Couldn't complete the ping command.")

    @commands.command(name='info', description='Shows information about the bot.')
    async def info(self, ctx):
        try:
            commit, branch = get_git_info(BOT_DIRECTORY)
            if ctx.guild:
                embed = discord.Embed(title=f"{ctx.guild.name}", description="Utility Information",
                                      timestamp=ctx.message.created_at, color=discord.Color.brand_green())
                embed.add_field(name="Github Commit", value=commit)
                embed.add_field(name="Github Branch", value=branch, inline=False)
                embed.add_field(name="Discord.py Version", value=discord.__version__)
                embed.add_field(name="Python Version", value=platform.python_version(), inline=False)
                embed.add_field(name="Members", value=len(ctx.guild.members))
                embed.add_field(name="Text Channels", value=len(ctx.guild.text_channels))
                embed.add_field(name="Voice Channels", value=len(ctx.guild.voice_channels))

                if ctx.channel.permissions_for(ctx.guild.me).embed_links:
                    await ctx.send(embed=embed)
                else:
                    await ctx.send('I do not have permission to send embeds.')
            else:
                await ctx.send("This command is not available in DMs.")
        except Exception as e:
            logging.error(f"Error in info: {e}")
            await ctx.send("An error occurred while fetching the bot info.")


async def setup(bot):
    await bot.add_cog(UtilityCog(bot))
