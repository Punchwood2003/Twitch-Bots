from twitchAPI.chat import Chat, EventData, ChatMessage, ChatSub, ChatCommand
from twitchAPI.type import AuthScope, ChatEvent
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.twitch import Twitch

from os import getenv
from dotenv import load_dotenv
import asyncio
import random
import time

# Set up auth-related constants
load_dotenv()
APP_ID = getenv('BOT_CLIENT_ID')
APP_SECRET = getenv('BOT_CLIENT_SECRET')
USER_SCOPE = [
    AuthScope.CHAT_READ, 
    AuthScope.CHAT_EDIT, 
    AuthScope.CHANNEL_MANAGE_BROADCAST
]
TARGET_CHANNEL = getenv('TWITCH_CHANNEL')

# Used for the copy-pasta
SLEEP_TIME = float(getenv('SLEEP_TIME', 2.5))
MSGS = [
    "Crazy?",
    "I was crazy once.",
    "They locked me in a room.",
    "A rubber room.",
    "A rubber room with rats.",
    "And rats make me crazy."
]

# Listen for chat messages
async def on_message(msg: ChatMessage):
    # Check to see if the message contains the string "that's crazy"
    if 'that\'s crazy' in msg.text.lower() or msg.text.lower() == "crazy?":
        # Get a random number between 1 and 10
        random_number = random.randint(1, 3)
        # 33% chance to respond with copy-pasta
        if random_number != 1:
            return
        
        # Respond with the copy-pasta
        for line in MSGS:
            await msg.reply(line)
            time.sleep(SLEEP_TIME)


# Bot connected successfully
async def on_ready(ready_event: EventData): 
    # Connect to TARGET_CHANNEL
    await ready_event.chat.join_room(TARGET_CHANNEL)

    # Print ready message
    print('Bot Ready!')

async def run_bot():
    # Authenticate application
    bot = await Twitch(APP_ID, APP_SECRET)
    auth = UserAuthenticator(bot, USER_SCOPE)
    token, refresh_token = await auth.authenticate()
    await bot.set_user_authentication(token, USER_SCOPE, refresh_token)

    # Initialize chat class
    chat = await Chat(bot)

    # Register events 
    chat.register_event(ChatEvent.READY, on_ready)
    chat.register_event(ChatEvent.MESSAGE, on_message)
    chat.register_event(ChatEvent.)

    # Start the chat bot
    chat.start()

    try:
        input('Press ENTER to stop the bot...\n')
    finally:
        # Stop the chat bot
        chat.stop()
        await bot.close()

if __name__ == '__main__':
    # Run the bot
    asyncio.run(run_bot())