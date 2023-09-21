from bot import *


def read_server_info(filename):
    logging.info(f"Reading server info from {filename}")
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            logging.debug(f"Data read from {filename}: {data}")
            return data
    except FileNotFoundError as e:
        logging.error(f"FileNotFoundError: {str(e)}")
        raise e
    except json.JSONDecodeError as e:
        logging.error(f"JSONDecodeError: {str(e)}")
        raise e
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}. Type: {type(e).__name__}")
        raise e


def write_server_info(filename, data):
    logging.info(f"Writing server info to {filename}")
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
            logging.debug(f"Data written to {filename}: {data}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}. Type: {type(e).__name__}")
        raise e


class AppInfoFetcher:
    def __init__(self, retries=3, timeout=5):
        self.retries = retries
        self.timeout = timeout
        logging.debug(f"AppInfoFetcher initialized with retries: {retries}, timeout: {timeout}")

    def fetch_info(self, app_id, client):
        logging.info(f"Starting the process to fetch info for AppID: {app_id}")
        try:
            app_id = int(app_id)
            logging.debug(f"AppID {app_id} converted to integer")

            if not client.logged_on:
                logging.debug(f"Client not logged on, logging on")
                with gevent.Timeout(self.timeout):
                    client.anonymous_login()
                    logging.debug(f"Anonymous login for client successful")

            else:
                logging.debug(f"Client already logged on")

            client.verbose_debug = False
            data = client.get_product_info(apps=[app_id], timeout=1)

            if data:
                logging.debug(f"Data fetched for AppID {app_id}: {data}")
                service_name = data['apps'][app_id]['common']['name']
                branches = data['apps'][app_id]['depots']['branches']
                build_id = branches.get('public', {}).get('buildid')
                logging.debug(
                    f"Parsed values - Service Name: {service_name}, Build ID: {build_id}, Branches: {branches}")

                if service_name and build_id:
                    password_required = {key: branches[key].get('pwdrequired', "0") == "1" for key in branches}
                    logging.debug(f"Password requirement parsed for branches: {password_required}")
                    logging.debug(
                        f"Returning data for AppID {app_id}: service_name: {service_name}, build_id: {build_id}, password_required: {password_required}")
                    return {
                        "name": service_name,
                        "build_id": build_id,
                        "branch": 'public',
                        "branches": list(branches.keys()),
                        "password_required": password_required,
                    }
                else:
                    logging.warning(f"Required data (service_name or build_id) missing for AppID {app_id}")
            else:
                logging.warning(f"No data returned for AppID {app_id}")
        except gevent.Timeout as e:
            logging.error(f"Timeout error: {str(e)} while fetching info for AppID {app_id}")
            raise e
        except Exception as e:
            logging.error(
                f"An unexpected error occurred while fetching info for AppID {app_id}: {str(e)}. Type: {type(e).__name__}")
            raise e


class AppIDCog(commands.Cog):
    def __init__(self, discord_bot):
        self.bot = discord_bot
        self.app_info_fetcher = AppInfoFetcher()
        logging.info("AppIDCog initialized")

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info("AppIDCog on_ready started")
        try:
            if os.path.exists('server_info.json'):
                server_info = read_server_info('server_info.json')
                existing_app_ids = set(server_info.get(COMPUTER_NAME, {}).keys())
                logging.debug(f"Existing AppIDs: {existing_app_ids}")
            else:
                server_info = {COMPUTER_NAME: {}}
                existing_app_ids = set()
        except FileNotFoundError as e:
            logging.error(f"FileNotFoundError: {str(e)}")
            server_info = {COMPUTER_NAME: {}}
            existing_app_ids = set()
        except KeyError as e:
            logging.error(f"KeyError: {str(e)}")
            server_info = {COMPUTER_NAME: {}}
            existing_app_ids = set()
        except Exception as e:
            logging.error(f"An unexpected error occurred: {str(e)}. Type: {type(e).__name__}")
            raise e

        # Fetch the data for each AppID
        client = SteamClient()
        data_changed = False  # Track if the data has changed

        for app_id in existing_app_ids:
            try:
                steam_data = self.app_info_fetcher.fetch_info(app_id, client)
                if steam_data:
                    server_info[COMPUTER_NAME][app_id] = steam_data
                    logging.info(f'Updating AppID {app_id} info')
                    data_changed = True  # Data has changed
            except Exception as e:
                logging.error(
                    f"An unexpected error occurred while processing AppID {app_id}: {str(e)}. Type: {type(e).__name__}")
                raise e

        # Only write the data to the file if it has changed
        if data_changed:
            write_server_info('server_info.json', server_info)

        logging.info("AppIDCog on_ready completed")


async def setup(bot):
    cog = AppIDCog(bot)
    await bot.add_cog(cog)
    logging.info(f"{cog.__class__.__name__} added to bot")
