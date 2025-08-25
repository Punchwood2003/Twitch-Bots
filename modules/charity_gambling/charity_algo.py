# Twitch API Imports
from twitchAPI.chat import Chat 
from twitchAPI.twitch import Twitch
from twitchAPI.type import ChatRoom
from twitchAPI.object.api import Chatter, BroadcasterSubscription

# External Imports
import random
import asyncio
import logging
from typing import List
from os import getenv
from dotenv import load_dotenv
from feature_flags import FeatureFlag, FeatureFlagManager


# Set up logger
logger = logging.getLogger(__name__)

# Set up constants
load_dotenv()
TWITCH_CHANNEL = getenv('TWITCH_CHANNEL')
BOT_NAME = getenv('BOT_NAME')

# Global flag to control the main loop
_running = False


# Main business logic for the charity/gambling bot
async def main_loop(broadcaster: Twitch, chat: Chat, broadcaster_id: str, moderator_id: str, feature_flag_manager: FeatureFlagManager, 
                   charity_enabled_flag: FeatureFlag, time_between_actions_flag: FeatureFlag, charity_chance_flag: FeatureFlag,
                   sub_chance_flag: FeatureFlag, automatic_reset_flag: FeatureFlag, default_points_flag: FeatureFlag, blacklisted_users_flag: FeatureFlag,
                   all_in_chance_flag: FeatureFlag, low_gamble_chance_flag: FeatureFlag, medium_gamble_chance_flag: FeatureFlag):
    global _running
    _running = True
    logger.info('Beginning charity gambling logic...')
    await asyncio.sleep(0.5) # Allow time for the bot to connect to the channel

    room = chat.room_cache.get(TWITCH_CHANNEL)
    try:
        while _running:
            # Get configuration values from feature flags
            time_between_actions = feature_flag_manager.get_flag(time_between_actions_flag, default=60)
            charity_enabled = feature_flag_manager.get_flag(charity_enabled_flag, default=False)
                
            # Wait for the next available action/time slot 
            elapsed = 0.0
            step = 0.1
            while elapsed < time_between_actions and _running and charity_enabled:
                elapsed += step
                await asyncio.sleep(step)
            
            # If charity is not enabled, skip the action
            if not charity_enabled:
                continue

            # Make sure that the bot is still running...
            if not _running:
                break

            # Get configuration values from feature flags
            charity_chance = feature_flag_manager.get_flag(charity_chance_flag, default=0.01)

            # Determine which action to take
            if random.random() <= charity_chance:
                logger.debug('Performing charity action...')
                await handle_charity(broadcaster, chat, room, broadcaster_id, moderator_id, feature_flag_manager,
                                   sub_chance_flag, automatic_reset_flag, default_points_flag, blacklisted_users_flag)
            else:
                logger.debug('Performing gambling action...')
                await handle_gambling(chat, room, feature_flag_manager, all_in_chance_flag, low_gamble_chance_flag, medium_gamble_chance_flag)
    except asyncio.CancelledError:
        logger.info('Charity gambling loop cancelled')
    finally:
        _running = False

    logger.info('Terminated charity gambling logic.')


def stop_main_loop():
    """Stop the main loop."""
    global _running
    _running = False


async def handle_charity(broadcaster: Twitch, chat: Chat, room: ChatRoom, broadcaster_id: str, moderator_id: str, feature_flag_manager: FeatureFlagManager,
                        sub_chance_flag: FeatureFlag, automatic_reset_flag: FeatureFlag, default_points_flag: FeatureFlag, blacklisted_users_flag: FeatureFlag):
    """Main business logic for the charity event"""
    # Make sure that the bot is in the channel
    if room is None:
        logger.warning('Bot is not in the channel or room not cached yet. Skipping charity event...')
        return

    # Get configuration values from feature flags
    sub_chance = feature_flag_manager.get_flag(sub_chance_flag, default=0.7)
    automatic_reset = feature_flag_manager.get_flag(automatic_reset_flag, default=True)
    default_points = feature_flag_manager.get_flag(default_points_flag, default=100000)
    blacklisted_users_str = feature_flag_manager.get_flag(blacklisted_users_flag, default="")
    blacklisted_users = [user.strip() for user in blacklisted_users_str.split(',') if user.strip()]

    # Get the list of chatters
    chatters = await get_active_chatters(chat.twitch, broadcaster_id, moderator_id)
    chatters = [chatter for chatter in chatters if chatter.user_name not in blacklisted_users]
    if len(chatters) == 0:
        logger.warning('No active chatters found in chat, skipping charity event...')
        return

    # Determine whether the points are going to a subscriber in chat or a random chatter
    active_subscribers = None
    isSub = False
    if random.random() <= sub_chance:
        subscribers = await get_current_subscribers(broadcaster, broadcaster_id)
        active_subscribers = get_active_subscribers(chatters, subscribers)
        if len(active_subscribers) != 0:
            logger.info('Giving points to a subscriber...')
            isSub = True
        else:
            logger.info('No active subscribers found in chat. Defaulting to random chatter...')
    else:
        logger.info('Giving points to a random chatter...')
    
    # Give the points to a random subscriber
    if isSub:
        winner = active_subscribers[random.randint(0, len(active_subscribers) - 1)]

        # Send the charity message
        await chat.send_message(room, 'Hmmmmmm... I think I am feeling a little charitable today...')
        await asyncio.sleep(2)
        await chat.send_message(room, 'Maybe I should give some points to chat?')
        await asyncio.sleep(2)
        await chat.send_message(room, f'@{winner.user_name}, thank you for stopping by the stream today! Here are some points to show my appreciation!')
        await asyncio.sleep(2)
        await chat.send_message(room, f'!givepoints {winner.user_name} all')
        await asyncio.sleep(2)
    
    # Give the points to a random chatter
    else:
        winner = chatters[random.randint(0, len(chatters) - 1)]

        # Send the charity message
        await chat.send_message(room, 'Hmmmmmm... I think I am feeling a little charitable today...')
        await asyncio.sleep(2)
        await chat.send_message(room, 'Maybe I should give some points to chat?')
        await asyncio.sleep(2)
        await chat.send_message(room, f'@{winner.user_name}, thank you for being a loyal subscriber! Here are some points to show my appreciation!')
        await asyncio.sleep(2)
        await chat.send_message(room, f'!givepoints {winner.user_name} all')
        await asyncio.sleep(2)

    # If the bot is set to automatically reset the points after a charity action, do so
    if automatic_reset:
        logger.info('Resetting points to default value...')
        await chat.send_message(room, f'!setpoints {BOT_NAME} {default_points}')
        await asyncio.sleep(2)


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
async def handle_gambling(chat: Chat, room: ChatRoom, feature_flag_manager: FeatureFlagManager,
                         all_in_chance_flag: FeatureFlag, low_gamble_chance_flag: FeatureFlag, medium_gamble_chance_flag: FeatureFlag):
    # Get configuration values from feature flags
    all_in_chance = feature_flag_manager.get_flag(all_in_chance_flag, default=0.01)
    low_gamble_chance = feature_flag_manager.get_flag(low_gamble_chance_flag, default=0.8)
    medium_gamble_chance = feature_flag_manager.get_flag(medium_gamble_chance_flag, default=0.1)

    # Detemrine whether the bot is going all-in or just a standard gamble action
    if random.random() <= all_in_chance:
        await chat.send_message(room, 'Chat, we are going ALL IN!')
        await asyncio.sleep(2)
        await chat.send_message(room, '!gamble all')
        await asyncio.sleep(2)
        logger.info('Went all in')
        return

    # Determine the type of bet to place
    rand = random.random()
    if rand <= low_gamble_chance:
        rand = random.randint(1, 25)
    elif rand <= low_gamble_chance + medium_gamble_chance:
        rand = random.randint(26, 50)
    else:
        rand = random.randint(51, 99)
    await chat.send_message(room, f'!gamble {rand}%')
    logger.info(f'Gambled {rand}%')
