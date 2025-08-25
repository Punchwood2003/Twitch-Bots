"""
Charity Gambling Module Implementation

Provides a Twitch bot module for charity gambling functionality.
"""

import os
import asyncio
import logging
from typing import List, Optional, Any
from twitchAPI.chat import ChatCommand, ChatUser

from module_manager.module_definition import TwitchModule, CommandDefinition, ModuleConfig
from feature_flags.feature_flag import FeatureFlag
from feature_flags.permission_types import PermissionLevel
from db.schema_manager import ModuleSchema, TableDefinition

from .charity_algo import main_loop as charity_main_loop


# Setup logging
logger = logging.getLogger(__name__)

# Read in constants from env file
BOT_NAME = os.getenv('BOT_NAME')


class CharityGamblingModule(TwitchModule):
    """
    Charity Gambling Module for Twitch chat.
    
    Allows users to gamble channel points with proceeds going to charity.
    Provides commands for enabling/disabling and resetting the charity system.
    """
    
    def __init__(self):
        super().__init__()
        self._charity_task: Optional[asyncio.Task] = None
        self._broadcaster = None
        self._chat = None
        self._broadcaster_id = None
        self._moderator_id = None
        
        # Feature flags
        self._charity_enabled_flag = FeatureFlag("gcb_enabled")
        self._default_points_flag = FeatureFlag("gcb_bot_default_points")
        self._time_between_actions_flag = FeatureFlag("gcb_time_between_bot_actions")
        self._charity_chance_flag = FeatureFlag("gcb_bot_charity_chance")
        self._sub_chance_flag = FeatureFlag("gcb_charity_to_sub_chance")
        self._all_in_chance_flag = FeatureFlag("gcb_all_in_chance")
        self._low_gamble_chance_flag = FeatureFlag("gcb_low_gamble_chance")
        self._medium_gamble_chance_flag = FeatureFlag("gcb_medium_gamble_chance")
        self._automatic_reset_flag = FeatureFlag("gcb_automatic_reset")
        self._charity_blacklisted_users_flag = FeatureFlag("gcb_charity_blacklisted_users")

    
    @property
    def module_name(self) -> str:
        return "charity_gambling"
    
    @property
    def module_description(self) -> str:
        return "Automated gambling with occasional donations of points to users in chat"
    
    @property
    def module_version(self) -> str:
        return "1.1.0"
    
    
    def get_feature_flags(self) -> List[tuple[FeatureFlag, PermissionLevel, Any, str]]:
        return [
            (self._charity_enabled_flag, PermissionLevel.READ_ONLY, False, 
             "Enable/disable charity gambling functionality"),
            (self._default_points_flag, PermissionLevel.OWNER_ONLY, 100000,
             "The number of points that the gambling bot starts with (whether that be initially or after a reset)"),
            (self._time_between_actions_flag, PermissionLevel.OWNER_ONLY, 60,
             "The Number of seconds between actions (whether that be charity or gambling)"),
            (self._charity_chance_flag, PermissionLevel.OWNER_ONLY, 0.01,
             "The chance of a charity action being performed"),
            (self._sub_chance_flag, PermissionLevel.OWNER_ONLY, 0.7,
             "The chance that the charity action will go to a subscriber (if any)"),
            (self._all_in_chance_flag, PermissionLevel.OWNER_ONLY, 0.01,
             "The chance that, when performing a gambling action, the bot will go all-in"),
            (self._low_gamble_chance_flag, PermissionLevel.OWNER_ONLY, 0.8,
             "The chance that the bot will perform a low gamble action (1-25%)"),
            (self._medium_gamble_chance_flag, PermissionLevel.OWNER_ONLY, 0.1,
             "The chance that the bot will perform a medium gamble action (26-50%)"),
            (self._automatic_reset_flag, PermissionLevel.OWNER_ONLY, True,
             "Whether the bot should automatically reset its points to the default amount after a charity action"),
            (self._charity_blacklisted_users_flag, PermissionLevel.OWNER_ONLY, [
                "TangiaBot", "jarrod_spelled_bot", "jarrod_spelled_wrong", "Moobot", "Sery_Bot", "StreamElements"
             ], "A list of users that the bot will not receive charity actions (comma-separated)")
        ]
    
    
    def get_database_schema(self) -> Optional[ModuleSchema]:
        """Define database schema for charity gambling."""
        # Currently no database tables needed for charity gambling module
        return None
    
    
    def get_commands(self) -> List[CommandDefinition]:
        return [
            CommandDefinition(
                name="charity",
                handler=self._charity_command_handler,
                description="Charity gambling commands: enable, disable, reset",
                permission_required=True,
                aliases=["c"]
            )
        ]
    
    
    def get_config(self) -> ModuleConfig:
        return ModuleConfig(
            enabled_by_default=True,
            auto_start=True,
            dependencies=[],
        )
    
    
    async def on_start(self) -> None:
        """Called when the module is started."""
        logger.info(f"Starting {self.module_name} module...")
        
        # The charity main loop will be started when set_twitch_context is called
        # This separation allows the module to be started without requiring
        # immediate Twitch API access
    
    
    async def on_stop(self) -> None:
        """Called when the module is stopped."""
        logger.info(f"Stopping {self.module_name} module...")
        
        if self._charity_task and not self._charity_task.done():
            self._charity_task.cancel()
            try:
                await self._charity_task
            except asyncio.CancelledError:
                pass
        
        self._charity_task = None
    
    
    async def on_error(self, error: Exception) -> None:
        """Called when an error occurs in the module."""
        logger.error(f"Error in {self.module_name} module: {error}")
        await super().on_error(error)
    
    
    def set_twitch_context(self, broadcaster, chat, broadcaster_id: str, moderator_id: str):
        """
        Set the Twitch API context for this module.
        
        This should be called after the module is started to provide
        the necessary Twitch API objects.
        """
        self._broadcaster = broadcaster
        self._chat = chat
        self._broadcaster_id = broadcaster_id
        self._moderator_id = moderator_id
        
        # Start the charity gambling main loop if charity is enabled
        try:
            charity_enabled = self.feature_flag_manager.get_flag(self._charity_enabled_flag, default=False)
            if charity_enabled:
                self._start_charity_loop()
        except PermissionError as e:
            # This should not happen if module lifecycle is correct, but log it for debugging
            logger.error(f"Feature flags not properly declared for charity gambling module: {e}")
            logger.error("This indicates a bug in the module lifecycle - feature flags should be declared before set_twitch_context is called")
        except Exception as e:
            logger.error(f"Unexpected error checking charity enabled flag: {e}")
    
    
    def _start_charity_loop(self):
        """Start the charity gambling main loop."""
        if self._charity_task and not self._charity_task.done():
            return  # Already running
        
        if not all([self._broadcaster, self._chat, self._broadcaster_id, self._moderator_id]):
            logger.warning("Cannot start charity loop: Twitch context not set")
            return
        
        self._charity_task = asyncio.create_task(
            charity_main_loop(
                self._broadcaster, 
                self._chat, 
                self._broadcaster_id, 
                self._moderator_id,
                self.feature_flag_manager,
                self._charity_enabled_flag,
                self._time_between_actions_flag,
                self._charity_chance_flag,
                self._sub_chance_flag,
                self._automatic_reset_flag,
                self._default_points_flag,
                self._charity_blacklisted_users_flag,
                self._all_in_chance_flag,
                self._low_gamble_chance_flag,
                self._medium_gamble_chance_flag
            )
        )
    
    
    def _stop_charity_loop(self):
        """Stop the charity gambling main loop."""
        if self._charity_task and not self._charity_task.done():
            self._charity_task.cancel()
    
    
    def _is_allowed_user(self, user: ChatUser) -> bool:
        """Check if user has permission for moderator commands."""
        return user.mod or user.name == os.getenv('TWITCH_CHANNEL', '')

    
    # Command handlers
    async def _charity_command_handler(self, cmd: ChatCommand):
        """Main charity command handler that routes to subcommands."""
        parts = cmd.text.strip().split()
        
        if len(parts) < 2:
            # No subcommand provided
            await cmd.reply('Usage: !charity <enable|disable|reset>')
            return
        
        subcommand = parts[1].lower()
        
        if subcommand == 'enable':
            await self._charity_enable_handler(cmd)
        elif subcommand == 'disable':
            await self._charity_disable_handler(cmd)
        elif subcommand == 'reset':
            await self._charity_reset_handler(cmd)
        else:
            await cmd.reply(f'Unknown subcommand: {subcommand}. Use: enable, disable, or reset')

    async def _charity_enable_handler(self, cmd: ChatCommand):
        """Handle the charity enable command."""
        if not self._is_allowed_user(cmd.user):
            # TODO: This should be changed to whisper to the user instead of posting in the main chat
            await cmd.reply('You do not have permission to use this command.')
            return
        
        if not self.feature_flag_manager:
            # TODO: This should be changed to whisper to the user instead of posting in the main chat
            await cmd.reply('Feature flag manager not available.')
            return
        
        if self.feature_flag_manager.get_flag(self._charity_enabled_flag, default=False):
            await cmd.reply('Charity feature is already enabled...')
            return
        
        # Enable the feature flag
        self.feature_flag_manager.set_flag(self._charity_enabled_flag, True)
        
        # Start the charity loop
        self._start_charity_loop()
        
        await cmd.reply('Charity feature enabled...')
    
    
    async def _charity_disable_handler(self, cmd: ChatCommand):
        """Handle the charity disable command."""
        if not self._is_allowed_user(cmd.user):
            # TODO: This should be changed to whisper to the user instead of posting in the main chat
            await cmd.reply('You do not have permission to use this command.')
            return
        
        if not self.feature_flag_manager:
            # TODO: This should be changed to whisper to the user instead of posting in the main chat
            await cmd.reply('Feature flag manager not available.')
            return

        if not self.feature_flag_manager.get_flag(self._charity_enabled_flag, default=False):
            await cmd.reply('Charity feature is already disabled...')
            return
        
        # Disable the feature flag
        self.feature_flag_manager.set_flag(self._charity_enabled_flag, False)
        
        # Stop the charity loop
        self._stop_charity_loop()
        
        await cmd.reply('Charity feature disabled...')
    
    
    async def _charity_reset_handler(self, cmd: ChatCommand):
        """Handle the charity reset command."""
        if not self._is_allowed_user(cmd.user):
            # TODO: This should be changed to whisper to the user instead of posting in the main chat 
            await cmd.reply('You do not have permission to use this command.')
            return
        
        if not self.feature_flag_manager:
            # TODO: This should be changed to whisper to the user instead of posting in the main chat
            await cmd.reply('Feature flag manager not available.')
            return
        
        # Check if charity is enabled first
        if not self.feature_flag_manager.get_flag(self._charity_enabled_flag, default=False):
            await cmd.reply('Charity feature is not enabled. Use `!charity enable` first.')
            return
        
        # Get the default points from the feature flag (should be dynamically loaded)
        default_points = self.feature_flag_manager.get_flag(self._default_points_flag, default=100000)
        
        # Set the points of the bot back to the default value 
        await cmd.send(f'!setpoints {BOT_NAME} {default_points}')
        await cmd.reply(f'Points reset to {default_points}.')
    
