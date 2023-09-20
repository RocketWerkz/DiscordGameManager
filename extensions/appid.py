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
        logging.info(f"Fetching info for AppID: {app_id}")
        try:
            app_id = int(app_id)  # Convert app_id to an integer
            with gevent.Timeout(self.timeout):
                client.anonymous_login()
                client.verbose_debug = False
                data = client.get_product_info(apps=[app_id], timeout=1)

                if data:
                    logging.debug(f"Data fetched for AppID {app_id}: {data}")
                    service_name = data.get('common', {}).get('name')
                    build_id = data.get('depots', {}).get('branches', {}).get('public', {}).get('buildid')
                    branches = data.get('depots', {}).get('branches', {})
                    if service_name and build_id:
                        password_required = {key: branches[key].get('pwdrequired', "0") == "1" for key in branches}
                        return {
                            "name": service_name,
                            "build_id": build_id,
                            "branch": 'public',
                            "branches": list(branches.keys()),
                            "password_required": password_required,
                        }
                else:
                    raise Exception(f"Exception occurred while getting game info for AppID {app_id}")
        except gevent.Timeout as e:
            logging.error(f"Timeout error: {str(e)}")
            raise e
        except Exception as e:
            logging.error(f"An unexpected error occurred: {str(e)}. Type: {type(e).__name__}")
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
            current_app_ids = set(str(app_id) for app_id in APP_ID_LIST.split(','))
            if os.path.exists('server_info.json'):
                server_info = read_server_info('server_info.json')
                existing_app_ids = set(server_info.get(COMPUTER_NAME, {}).keys())
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

        new_app_ids = current_app_ids.difference(existing_app_ids)
        removed_app_ids = existing_app_ids.difference(current_app_ids)
        client = SteamClient()

        if new_app_ids:
            for app_id in new_app_ids:
                try:
                    steam_data = self.app_info_fetcher.fetch_info(app_id, client)
                    if steam_data:  # Only add it if it's not None or empty
                        server_info[COMPUTER_NAME][app_id] = steam_data
                        logging.info(f"Added AppID {app_id} to server info")
                except Exception as e:
                    logging.error(f"An unexpected error occurred while processing AppID {app_id}: {str(e)}. Type: {type(e).__name__}")
                    raise e
            write_server_info('server_info.json', server_info)

        if removed_app_ids:
            for app_id in removed_app_ids:
                del server_info[COMPUTER_NAME][str(app_id)]
                logging.info(f"Removed AppID {app_id} from server info")
            write_server_info('server_info.json', server_info)

        logging.info("AppIDCog on_ready completed")


async def setup(bot):
    await bot.add_cog(AppIDCog(bot))
    logging.info("AppIDCog added to bot")
