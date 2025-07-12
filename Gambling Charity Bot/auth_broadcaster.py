# Twtich API Imports
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.twitch import Twitch
from twitchAPI.type import AuthScope

# External Imports
from os import getenv
from dotenv import load_dotenv
import asyncio
import json


# Set up auth-related constants
load_dotenv()
APP_ID = getenv('BOT_CLIENT_ID')
APP_SECRET = getenv('BOT_CLIENT_SECRET')
USER_SCOPE = [AuthScope.CHANNEL_READ_SUBSCRIPTIONS]


# Retrieves broadcaster tokens and saves them to a file
async def authenticate_broadcaster():
    twitch = await Twitch(APP_ID, APP_SECRET)
    auth = UserAuthenticator(twitch, USER_SCOPE)
    token, refresh_token = await auth.authenticate()
    # Save tokens securely
    with open('Gambling Charity Bot/broadcaster_token.json', 'w') as f:
        json.dump({'access_token': token, 'refresh_token': refresh_token}, f)
    print("Broadcaster tokens saved.")

if __name__ == '__main__':
    import asyncio
    asyncio.run(authenticate_broadcaster())
