import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import logging
import git
import py_compile
import aiohttp
import filecmp
import sys
import time
import subprocess
import requests

# Initialize logging
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
ADMIN_ROLE_NAME = os.getenv('ADMIN_ROLE_NAME')
GIT_REPO_URL = os.getenv('GIT_REPO_URL')
BOT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
STAGING_DIRECTORY = os.path.join(BOT_DIRECTORY, 'staging')
EXTENSIONS_DIRECTORY = os.path.join(BOT_DIRECTORY, 'extensions')
COGS_DIRECTORY = os.path.join(BOT_DIRECTORY, 'cogs')
# Random hash included in UNSET_VALUE_ to prevent accidental use of UNSET_VALUE_
unset = "UNSET_BRANCH_5f3a2b1"

# Create directories if they don't exist
if not os.path.exists(STAGING_DIRECTORY):
    os.makedirs(STAGING_DIRECTORY)
if not os.path.exists(EXTENSIONS_DIRECTORY):
    os.makedirs(EXTENSIONS_DIRECTORY)
if not os.path.exists(COGS_DIRECTORY):
    os.makedirs(COGS_DIRECTORY)

# Set up Discord intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# Initialize the bot
bot = commands.Bot(command_prefix='*', intents=intents)


# Fetch current info as git commit and branch, or commit of a provided branch
def get_github_default_branch(repo_url):
    user_repo = "/".join(repo_url.split('/')[-2:])
    url = f"https://api.github.com/repos/{user_repo}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()["default_branch"]
    except Exception as e:
        logger.error(f"Could not get default branch: {e}")
        return None


def get_git_info(repo_path, target_branch=unset):
    try:
        if repo_path.startswith('http') or repo_path.startswith('https'):
            if target_branch == unset:
                target_branch = get_github_default_branch(repo_path)
                if target_branch is None:
                    raise ValueError("Could not determine the default branch.")

            logger.info(f"Targeting remote repository {repo_path} {target_branch}")
            cmd = ['git', 'ls-remote', repo_path, f'refs/heads/{target_branch}']
            result = subprocess.run(cmd, stdout=subprocess.PIPE)
            output = result.stdout.decode('utf-8').strip()

            if output:
                commit_hash = output.split()[0]
                commit = commit_hash[:7]  # Shorten to 7 characters
                branch = target_branch
        else:
            repo = git.Repo(repo_path)
            if target_branch != unset:
                logger.info(f"Targeting local repository {repo_path} {target_branch}")
                branch_commit = repo.refs[f"refs/remotes/origin/{target_branch}"].commit
                commit = branch_commit.hexsha[:7]
                branch = target_branch
            else:
                logger.info(f"Targeting local repository {repo_path} {repo.active_branch.name}")
                repo.git.fetch()
                commit = repo.head.object.hexsha[:7]
                branch = repo.active_branch.name

        return commit, branch

    except git.exc.GitCommandError as e:
        logger.error(f"GitCommandError: {str(e)}. Status: {e.status}, Command: {e.command}, Stderr: {e.stderr}")
        raise e

    except Exception as e:
        logger.error(f"Returning exception: {e} Type: {type(e).__name__}")
        raise e


# Function to pull from GIT_REPO_URL repo into STAGING_DIRECTORY
def pull_repo(repo_url, target_branch, target_commit):
    try:
        if not os.path.exists(STAGING_DIRECTORY):
            os.makedirs(STAGING_DIRECTORY)
            logger.info(f"Created directory {STAGING_DIRECTORY}.")
            git.Repo.clone_from(repo_url, STAGING_DIRECTORY)
            logger.info(f"Cloned repository {repo_url} to {STAGING_DIRECTORY}.")

        repo = git.Repo(STAGING_DIRECTORY)
        if repo.is_dirty(untracked_files=True):
            logger.error("The repository is dirty; aborting pull.")
            return False

        if target_branch and target_commit:
            repo.git.checkout(target_branch)
            repo.git.checkout(target_commit)
            logger.info(f"Switched to branch {target_branch} and pulled commit {target_commit}.")

        elif target_commit:
            repo.git.checkout(target_commit)
            logger.info(f"Switched to commit {target_commit}.")

        elif target_branch:
            repo.git.checkout(target_branch)
            repo.git.pull()
            logger.info(f"Switched to branch {target_branch} and pulled latest commit.")

        else:
            current_branch = repo.active_branch.name
            repo.git.pull()
            logger.info(f"Pulled latest commit from current branch {current_branch}.")

        return True

    except git.exc.GitCommandError as e:
        logger.error(f"GitCommandError: {str(e)}. Status: {e.status}, Command: {e.command}, Stderr: {e.stderr}")
        raise e

    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}. Type: {type(e).__name__}")
        raise e


# Function to test new code from GIT_REPO_URL repo in STAGING_DIRECTORY using py_compile
def test_new_code():
    try:
        # Compile the code
        py_compile.compile(STAGING_DIRECTORY, doraise=True)

        # If we get here, the code compiled successfully
        return True

    except py_compile.PyCompileError as e:
        logger.error(f"PyCompileError: {str(e)}")
        raise e  # Raising the exception to the caller

    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}. Type: {type(e).__name__}")
        raise e  # Raising the exception to the caller


# Function to process all extensions in the EXTENSIONS_DIRECTORY
def process_all_extensions():
    for filename in os.listdir(EXTENSIONS_DIRECTORY):
        if filename.endswith('.py'):
            extension_name = f'extensions.{filename[:-3]}'

            # Check if extension is already loaded
            if extension_name in bot.extensions:
                try:
                    bot.reload_extension(extension_name)
                    logger.info(f"Reloaded extension: {extension_name}")
                except (commands.ExtensionNotFound, commands.ExtensionFailed) as e:
                    logger.error(f"Failed to reload extension {extension_name}: {e}")
            else:
                try:
                    bot.load_extension(extension_name)
                    logger.info(f"Loaded extension: {extension_name}")
                except (commands.ExtensionNotFound, commands.ExtensionFailed) as e:
                    logger.error(f"Failed to load extension {extension_name}: {e}")


# Add a check to see if the user is an admin role or administrator
def is_admin(ctx):
    return ctx.author.guild_permissions.administrator or discord.utils.get(ctx.author.roles, name=ADMIN_ROLE_NAME)


# Check if argument is a git commit hash
def is_likely_commit(arg):
    return len(arg) == 7 and all(c.isalnum() for c in arg)


# Command to update the bot
@bot.command(name='update', help='Update the bot code from a git repo')
@commands.check(is_admin)
async def update(ctx, *args):
    try:
        # Get git info of production code in BOT_DIRECTORY
        current_commit, current_branch = get_git_info(BOT_DIRECTORY)
        logger.info(f"Current commit: {current_commit}, current branch: {current_branch}")

        # Get git info of GIT_REPO_URL repo
        github_commit, github_branch = get_git_info(GIT_REPO_URL, target_branch=current_branch)
        logger.info(f"Github commit: {github_commit}, github branch: {github_branch}")

        # Parse arguments
        target_branch = unset
        target_commit = unset

        commit_count = 0
        branch_count = 0

        for arg in args:
            if is_likely_commit(arg):
                commit_count += 1
                target_commit = arg
            else:
                branch_count += 1
                target_branch = arg

        if commit_count == len(args) and len(args) > 0:
            await ctx.send("All arguments are being interpreted as commit hashes. Please provide a branch name.")
            return

        if branch_count == len(args) and len(args) > 0:
            await ctx.send(
                "All arguments are being interpreted as branch names. Please provide a commit hash if intended.")
            return

        # Compare current commit and branch to target commit and branch
        if target_branch != unset and target_commit != unset:
            if target_branch == current_branch and target_commit == current_commit:
                await ctx.send(
                    f"Current commit is already {target_commit} and branch is already {target_branch}. No action taken.")
                return

        # If only one of target commit or branch is provided, check if it's the same as the current commit or branch
        elif target_commit != unset:
            if target_commit == current_commit:
                await ctx.send(f"Current commit is already {target_commit} on {current_branch}. No action taken.")
                return

        # Uncertain of logic here
        elif target_branch != unset:
            if target_branch == current_branch and github_commit == current_commit:
                await ctx.send(f"Current branch is already {target_branch} with commit {current_commit}. No action taken.")
                return

        else:
            # Compare current commit and branch to github commit and branch
            if github_branch == current_branch and github_commit == current_commit:
                await ctx.send(
                    f"Current commit is already {github_commit} and branch is already {github_branch}. No action taken.")
                return

        # Pull from GIT_REPO_URL repo into STAGING_DIRECTORY
        if pull_repo(GIT_REPO_URL, target_branch=target_branch, target_commit=target_commit):
            await ctx.send(f"Repository at {GIT_REPO_URL} updated successfully for {STAGING_DIRECTORY}.")
        else:
            await ctx.send(f"Failed to update the repository at {GIT_REPO_URL}.")
            return

        # def test_new_code(): will return True if the code compiles successfully, False, or raise an error
        try:
            test_result = test_new_code()
            if test_result:
                await ctx.send("Code compiled successfully.")
                return
        except py_compile.PyCompileError as e:
            await ctx.send(f"A PyCompileError occurred: {str(e)}.")
            return
        except Exception as e:
            await ctx.send(f"An unexpected error occurred: {str(e)}. Type: {type(e).__name__}")
            raise e

        # Pull from GIT_REPO_URL repo into BOT_DIRECTORY
        if pull_repo(GIT_REPO_URL, target_branch=target_branch, target_commit=target_commit):
            await ctx.send(f"Repository at {GIT_REPO_URL} updated successfully for {BOT_DIRECTORY}.")
        else:
            await ctx.send(f"Failed to update the repository at {GIT_REPO_URL}.")
            return

        # Check if the bot.py file is the same or has been changed
        staging_bot_path = os.path.join(STAGING_DIRECTORY, 'bot.py')
        bot_path = os.path.join(BOT_DIRECTORY, 'bot.py')
        if os.path.exists(staging_bot_path) and os.path.exists(bot_path):
            if filecmp.cmp(staging_bot_path, bot_path, shallow=False):
                logger.info("The bot.py file is identical. Reloading extensions...")
                process_all_extensions()  # Function to reload Discord extensions
            else:
                logger.info("The bot.py file has been changed. Restarting script...")
                sys.exit()  # This will exit the script, WinSW should handle the restart

    except Exception as e:
        await ctx.send(f"An unexpected error occurred: {str(e)}. Type: {type(e).__name__}")


# Discord on ready event with logging
@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    logger.info(f'Discord.py version: {discord.__version__}')


# Command to provide a link to the source code GIT_REPO_URL, state license as AGPL-3.0, strip the .git suffix
@bot.command(name='source', help='Provide a link to the source code')
async def source(ctx):
    await ctx.send(f"Source code available at {GIT_REPO_URL} under the Affero GPL-3.0 license.")


if __name__ == '__main__':
    process_all_extensions()  # Function to load Discord extensions
    max_retries = 5
    for i in range(max_retries):
        try:
            bot.run(BOT_TOKEN)
            break
        except aiohttp.ClientConnectorError as e:
            logging.exception('Failed to connect to Discord: %s', e)
            if i < max_retries - 1:
                time.sleep(10)  # Wait for 10 seconds before next retry
            else:
                logging.error("Failed to connect after %d attempts, exiting.", max_retries)
                exit(1)

