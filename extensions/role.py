from bot import *


class RoleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logging.info(f"{self.__class__.__name__} initialized")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        logging.error(f"Error encountered in command '{ctx.command}': {error}")
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send('Something went wrong while running the command.')

    @commands.command(name='query_role', description='Lists members with a specific role.')
    async def query_role(self, ctx, *, role_name):
        logging.info(f"'query_role' command invoked by {ctx.author.name}#{ctx.author.discriminator}")
        try:
            if ctx.guild:  # Check if the command is invoked in a guild and not in DMs
                role = discord.utils.get(ctx.guild.roles, name=role_name)  # Find the role
                if role:  # Check if the role exists
                    logging.info(f"Role '{role_name}' found in {ctx.guild.name}")
                    members = [member.mention for member in role.members]  # List all members with the role
                    if members:  # Check if there are members with the role
                        # Modify the response to include join date
                        response = []
                        for member in role.members:
                            join_date = member.joined_at.strftime('%Y-%m-%d %H:%M:%S')
                            response.append(f"{member.mention} (Joined: {join_date})")

                        logging.info(f"Members with '{role_name}' role in {ctx.guild.name}: {', '.join(members)}")
                        await ctx.send(f"Members with the '{role_name}' role:\n" + '\n'.join(response))
                    else:
                        logging.warning(f"No members found with '{role_name}' role in {ctx.guild.name}")
                        await ctx.send(f"No members have the '{role_name}' role.")
                else:
                    logging.warning(f"Role '{role_name}' not found in {ctx.guild.name}")
                    await ctx.send(f"The role '{role_name}' does not exist.")
            else:
                await ctx.send("This command is not available in DMs.")
        except Exception as e:
            logging.error(f"Error executing 'query_role' command: {e}")
            await ctx.send("An error occurred while listing members with the role.")


async def setup(bot):
    cog = RoleCog(bot)
    await bot.add_cog(cog)
    logging.info(f"{cog.__class__.__name__} added to bot")
