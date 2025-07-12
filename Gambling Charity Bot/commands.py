# Twitch API Imports
from twitchAPI.chat import ChatCommand, ChatUser

# Local Imports
import feature_flags

# External Imports
from os import getenv
from dotenv import load_dotenv


# Set up constants
load_dotenv()
DEFAULT_POINTS = int(getenv('DEFAULT_POINTS', 1000))
BOT_NAME = getenv('BOT_NAME')


# Used to verify permissions for commands
def is_allowed_user(user: ChatUser):
    return user.user_type == 'mod' or user.user_type == 'broadcaster'


# Defines the behavior of the "!charityenable" command
async def charity_enable_handler(cmd: ChatCommand):
    # Ensure that the message is from a moderator or the broadcaster
    if not is_allowed_user(cmd.user):
        await cmd.reply('You do not have permission to enable charity features.')
        return

    if feature_flags.CHARITY_ENABLED:
        await cmd.reply('Charity feature is already enabled...')
        return
    feature_flags.CHARITY_ENABLED = True
    await cmd.reply('Charity feature enabled...')


# Defines the behavior of the "!charitydisable" command
async def charity_disable_handler(cmd: ChatCommand):
    # Ensure that the message is from a moderator or the broadcaster
    if not is_allowed_user(cmd.user):
        await cmd.reply('You do not have permission to disable charity features.')
        return

    if not feature_flags.CHARITY_ENABLED:
        await cmd.reply('Charity feature is already disabled...')
        return
    feature_flags.CHARITY_ENABLED = False
    await cmd.reply('Charity feature disabled...')


# Defines the behavior of the "!charityreset" command
async def charity_reset_handler(cmd: ChatCommand):
    # Ensure that the message is from a moderator or the broadcaster
    if not is_allowed_user(cmd.user):
        await cmd.reply('You do not have permission to use charity features.')
        return

    if not feature_flags.CHARITY_ENABLED:
        await cmd.reply('Charity feature must be active to reset...')
        return
    
    # Set the points of the bot back to the default value 
    await cmd.send(f'!setpoints {BOT_NAME} {DEFAULT_POINTS}')
    await cmd.reply(f'Points reset to {DEFAULT_POINTS}.')
