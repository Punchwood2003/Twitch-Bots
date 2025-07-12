# Twitch API Imports
from twitchAPI.chat import Chat 
from twitchAPI.twitch import Twitch
from twitchAPI.type import ChatRoom
from twitchAPI.object.api import Chatter, BroadcasterSubscription

# Local Imports
import feature_flags

# External Imports
from typing import List
from os import getenv
from dotenv import load_dotenv
from time import sleep
import random


# Set up constants
load_dotenv()
TIME_BETWEEN_ACTIONS = int(getenv('TIME_BETWEEN_ACTIONS'))
CHARITY_CHANCE = float(getenv('CHARITY_CHANCE', 0.1))
SUB_CHANCE = float(getenv('SUB_CHANCE', 0.7))
ALL_IN_CHANCE = float(getenv('ALL_IN_CHANCE', 0.1))
LOW_GAMBLE_CHANCE = float(getenv('LOW_GAMBLE_CHANCE', 0.8))
MEDIUM_GAMBLE_CHANCE = float(getenv('MEDIUM_GAMBLE_CHANCE', 0.1))
AUTOMATIC_RESET = bool(getenv('AUTOMATIC_RESET', False))

TWITCH_CHANNEL = getenv('TWITCH_CHANNEL')
BOT_NAME = getenv('BOT_NAME')
DEFAULT_POINTS = int(getenv('DEFAULT_POINTS', 1000))


# Main business logic for the charity/gambling bot
async def main_loop(broadcaster: Twitch, chat: Chat, broadcaster_id: str, moderator_id: str):
    global RUNNING
    print('Beginning charity gambling logic...')
    sleep(3) # Allow time for the bot to connect to the channel and set RUNNING to True

    room = chat.room_cache.get(TWITCH_CHANNEL)
    while feature_flags.RUNNING:
        # Wait for the next available action/time slot 
        elapsed = 0.0
        step = 0.1
        while elapsed < TIME_BETWEEN_ACTIONS and feature_flags.RUNNING and feature_flags.CHARITY_ENABLED:
            elapsed += step
            sleep(step)
        
        # If charity is not enabled, skip the action
        if not feature_flags.CHARITY_ENABLED:
            continue

        # Make sure that the bot is still running...
        if not feature_flags.RUNNING:
            break

        # Determine which action to take
        if random.random() <= CHARITY_CHANCE:
            print('Performing charity action...')
            await handle_charity(broadcaster, chat, room, broadcaster_id, moderator_id)
        else:
            print('Performing gambling action...')
            await handle_gambling(chat, room)

    print('Terminated charity gambling logic.')


# Main business logic for the charity event
async def handle_charity(broadcaster: Twitch, chat: Chat, room: ChatRoom, broadcaster_id: str, moderator_id: str):
    # Make sure that the bot is in the channel
    if room is None:
        print('\tBot is not in the channel or room not cached yet. Skipping charity event...')
        return

    # Determine whether the points are going to a subscriber in chat or a random chatter
    chatters = await get_active_chatters(chat.twitch, broadcaster_id, moderator_id)
    active_subscribers = None
    isSub = False
    if random.random() <= SUB_CHANCE:
        subscribers = await get_current_subscribers(broadcaster, broadcaster_id)
        active_subscribers = get_active_subscribers(chatters, subscribers)
        if len(active_subscribers) != 0:
            print('\tGiving points to a subscriber...')
            isSub = True
        else:
            print('\tNo active subscribers found in chat. Defaulting to random chatter...')
    else:
        print('\tGiving points to a crandom chatter...')
    
    # Give the points to a random subscriber
    if isSub:
        winner = active_subscribers[random.randint(0, len(active_subscribers) - 1)]

        # Send the charity message
        await chat.send_message(room, 'Hmmmmmm... I think I am feeling a little charitable today...')
        sleep(2)
        await chat.send_message(room, 'Maybe I should give some points to chat?')
        sleep(2)
        await chat.send_message(room, f'@{winner.user_name}, thank you for stopping by the stream today! Here are some points to show my appreciation!')
        sleep(2)
        await chat.send_message(room, f'!givepoints {winner.user_name} all')
    
    # Give the points to a random chatter
    else:
        winner = chatters[random.randint(0, len(chatters) - 1)]

        # Send the charity message
        await chat.send_message(room, 'Hmmmmmm... I think I am feeling a little charitable today...')
        sleep(2)
        await chat.send_message(room, 'Maybe I should give some points to chat?')
        sleep(2)
        await chat.send_message(room, f'@{winner.user_name}, thank you for being a loyal subscriber! Here are some points to show my appreciation!')
        sleep(2)
        await chat.send_message(room, f'!givepoints {winner.user_name} all')

    # If the bot is set to automatically reset the points after a charity action, do so
    if AUTOMATIC_RESET:
        print('\tResetting points to default value...')
        await chat.send_message(room, f'!setpoints {BOT_NAME} {DEFAULT_POINTS}')
        sleep(2)


# Returns the list of all current users in the chat
async def get_active_chatters(twitch: Twitch, broadcaster_id: str, moderator_id: str) -> List[Chatter]:
    resp = await twitch.get_chatters(broadcaster_id=broadcaster_id, moderator_id=moderator_id)
    return resp.data


# Returns the list of all current subscribers to the channel
async def get_current_subscribers(twitch: Twitch, broadcaster_id: str) -> List[BroadcasterSubscription]:
    resp = await twitch.get_broadcaster_subscriptions(broadcaster_id=broadcaster_id)
    return resp.data


# Returns the list of subscribers that are currently in the chat
def get_active_subscribers(active_chatters: List[Chatter], current_subscribers: List[BroadcasterSubscription]) -> List[Chatter]:
    subscriber_ids = {sub.user_id.lower() for sub in current_subscribers}
    return [chatter for chatter in active_chatters if chatter.user_id in subscriber_ids]


# Main business logic for the gambling event
async def handle_gambling(chat: Chat, room: ChatRoom):
    # Detemrine whether the bot is going all-in or just a standard gamble action
    if random.random() <= ALL_IN_CHANCE:
        await chat.send_message(room, 'Chat, we are going ALL IN!')
        await chat.send_message(room, '!gamble all')
        print('\tWent all in')
        return

    # Determine the type of bet to place
    rand = random.random()
    if rand <= LOW_GAMBLE_CHANCE:
        rand = random.randint(1, 25)
    elif rand <= LOW_GAMBLE_CHANCE + MEDIUM_GAMBLE_CHANCE:
        rand = random.randint(26, 50)
    else:
        rand = random.randint(51, 99)
    await chat.send_message(room, f'!gamble {rand}%')
    print(f'\tGambled {rand}%')
