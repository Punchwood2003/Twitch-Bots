# Twitch API Imports
from twitchAPI.chat import Chat, EventData
from twitchAPI.type import AuthScope, ChatEvent
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.twitch import Twitch

# Local Imports
from commands import charity_enable_handler, charity_disable_handler, charity_reset_handler
from charity_algo import main_loop
import feature_flags

# External Imports
from os import getenv
from dotenv import load_dotenv
from threading import Thread
import asyncio
import json


# Set up auth-related constants
load_dotenv()
APP_ID = getenv('BOT_CLIENT_ID')
APP_SECRET = getenv('BOT_CLIENT_SECRET')
USER_SCOPE = [
    AuthScope.CHAT_READ, 
    AuthScope.CHAT_EDIT, 
    AuthScope.CHANNEL_MANAGE_BROADCAST, 
    AuthScope.CHANNEL_READ_SUBSCRIPTIONS, 
    AuthScope.MODERATOR_READ_CHATTERS, 
    AuthScope.MODERATOR_READ_FOLLOWERS,
]
TARGET_CHANNEL = getenv('TWITCH_CHANNEL')
BOT_NAME = getenv('BOT_NAME')

# Command-Specific Constants
COMMAND_PREFIX = getenv('COMMAND_PREFIX', '!')
CHARITY_ENABLE_COMMAND = getenv('CHARITY_ENABLE_COMMAND', 'charityenable')
CHARITY_DISABLE_COMMAND = getenv('CHARITY_DISABLE_COMMAND', 'charitydisable')
CHARITY_RESET_COMMAND = getenv('CHARITY_RESET_COMMAND', 'charityreset')


# Bot connected successfully
async def on_ready(ready_event: EventData): 
    # Connect to TARGET_CHANNEL
    await ready_event.chat.join_room(TARGET_CHANNEL)

    # Print ready message
    print('Bot Ready!')


# Thread definition to run the charity/gambling logic
def charity_gamble_thread(broadcaster: Twitch, chat: Chat, broadcaster_id: str, moderator_id: str):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.run_until_complete(main_loop(broadcaster, chat, broadcaster_id, moderator_id))
    loop.close()


# Loads broadcaster tokens from a file
def load_broadcaster_tokens():
    with open('Gambling Charity Bot/broadcaster_token.json', 'r') as f:
        data = json.load(f)
    return data['access_token'], data['refresh_token']


# Main function to run the bot
async def run_bot():
    # Load broadcaster tokens
    broadcaster_token, broadcaster_refresh = load_broadcaster_tokens()
    if not broadcaster_token or not broadcaster_refresh:
        raise ValueError("Broadcaster tokens not found or invalid. Please run the authentication script first.")
    broadcaster = await Twitch(APP_ID, APP_SECRET)
    await broadcaster.set_user_authentication(broadcaster_token, [AuthScope.CHANNEL_READ_SUBSCRIPTIONS], broadcaster_refresh)

    # Authenticate application
    bot = await Twitch(APP_ID, APP_SECRET)
    auth = UserAuthenticator(bot, USER_SCOPE)
    token, refresh_token = await auth.authenticate()
    await bot.set_user_authentication(token, USER_SCOPE, refresh_token)

    # Get the broadcaster ID for the channel
    broadcaster_id = None
    async for info in bot.get_users(logins=[TARGET_CHANNEL]):
        broadcaster_id = info.id
        break
    if broadcaster_id is None:
        raise ValueError("Failed to retrieve broadcaster ID for the channel.")

    # Get the moderator ID for the user
    moderator_id = None
    async for info in bot.get_users(logins=[BOT_NAME]):
        moderator_id = info.id
    if moderator_id is None:
        raise ValueError("Failed to retrieve moderator ID for the authenticated user.")

    # Initialize chat class
    chat = await Chat(bot)

    # Prepare the thread responsible for hanlding the charity/gambling logic
    feature_flags.RUNNING = True
    charity_thread = Thread(target= charity_gamble_thread, kwargs={"broadcaster": broadcaster, "chat": chat, "broadcaster_id": broadcaster_id, "moderator_id": moderator_id})
    charity_thread.start()

    # Register events 
    chat.register_command(name=CHARITY_ENABLE_COMMAND, handler=charity_enable_handler)
    chat.register_command(name=CHARITY_DISABLE_COMMAND, handler=charity_disable_handler)
    chat.register_command(name=CHARITY_RESET_COMMAND, handler=charity_reset_handler)
    chat.register_event(ChatEvent.READY, on_ready)

    # Start the chat bot
    chat.start()

    try:
        input('Press ENTER to stop the bot...\n')
        feature_flags.RUNNING = False
    finally:
        # Stop the chat bot
        chat.stop()
        charity_thread.join()
        await bot.close()


if __name__ == '__main__':
    # Run the bot
    asyncio.run(run_bot())
