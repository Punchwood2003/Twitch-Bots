"""
Modular Twitch Bot Application

Main application that demonstrates the modular bot system with
feature flags, database management, and module lifecycle management.
"""

import asyncio
import logging
import os
import threading
from pathlib import Path
from dotenv import load_dotenv

# Twitch API imports
from twitchAPI.chat import Chat, EventData
from twitchAPI.type import AuthScope, ChatEvent
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.twitch import Twitch

# Local imports
from feature_flags.feature_flags_manager import FeatureFlagManager
from db.schema_manager import SchemaManager
from module_manager.module_manager import ModuleManager
from process_monitoring import ProcessMonitor
from modules.charity_gambling import CharityGamblingModule

# Setup logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Twitch API configuration
BROADCASTER_ACCESS_TOKEN = os.getenv('BROADCASTER_ACCESS_TOKEN')
BROADCASTER_REFRESH_TOKEN = os.getenv('BROADCASTER_REFRESH_TOKEN')
APP_ID = os.getenv('BOT_CLIENT_ID')
APP_SECRET = os.getenv('BOT_CLIENT_SECRET')
USER_SCOPE = [
    AuthScope.CHAT_READ, 
    AuthScope.CHAT_EDIT, 
    AuthScope.CHANNEL_MANAGE_BROADCAST, 
    AuthScope.CHANNEL_READ_SUBSCRIPTIONS, 
    AuthScope.MODERATOR_READ_CHATTERS, 
    AuthScope.MODERATOR_READ_FOLLOWERS,
]
TARGET_CHANNEL = os.getenv('TWITCH_CHANNEL')
BOT_NAME = os.getenv('BOT_NAME')
COMMAND_PREFIX = os.getenv('COMMAND_PREFIX', '!')


class ModularTwitchBot:
    """
    Main Twitch bot application with modular architecture.
    """
    
    def __init__(self):
        self.bot = None
        self.broadcaster = None
        self.chat = None
        self.broadcaster_id = None
        self.moderator_id = None
        self.process_monitor = ProcessMonitor()
        
        # Initialize core systems
        self.feature_flag_manager = FeatureFlagManager(
            config_path="feature_flags.json",
            module_name="main_bot"
        )
        self.schema_manager = SchemaManager()
        self.module_manager = ModuleManager(
            self.feature_flag_manager,
            self.schema_manager,
            "module_registry.json"
        )
        
        # Register event callbacks
        self.module_manager.on_module_started(self._on_module_started)
        self.module_manager.on_module_stopped(self._on_module_stopped)
        self.module_manager.on_module_error(self._on_module_error)
    
    async def initialize(self):
        """Initialize the bot and all systems."""
        logger.info("Initializing Modular Twitch Bot...")
        
        # Capture initial process state for monitoring
        self.process_monitor.capture_initial_state()
        
        # Initialize core systems
        await self.module_manager.initialize()
        
        # Register built-in modules
        await self._register_builtin_modules()
        
        # Initialize Twitch API
        await self._initialize_twitch_api()
        
        logger.info("Bot initialization complete")
    
    async def _register_builtin_modules(self):
        """Register built-in modules."""
        logger.info("Registering built-in modules...")
        
        # Register charity gambling module
        charity_module = CharityGamblingModule()
        self.module_manager.register_module(charity_module)
        
        logger.info("Built-in modules registered")
    
    async def _initialize_twitch_api(self):
        """Initialize Twitch API connections."""
        logger.info("Initializing Twitch API...")
        
        # Load broadcaster tokens
        if not BROADCASTER_ACCESS_TOKEN or not BROADCASTER_REFRESH_TOKEN:
            raise ValueError("Broadcaster tokens not found. Please run authentication first.")
        
        # Initialize broadcaster API
        self.broadcaster = await Twitch(APP_ID, APP_SECRET)
        await self.broadcaster.set_user_authentication(
            BROADCASTER_ACCESS_TOKEN, 
            [AuthScope.CHANNEL_READ_SUBSCRIPTIONS], 
            BROADCASTER_REFRESH_TOKEN
        )
        
        # Initialize bot API (this may spawn OAuth subprocess)
        logger.debug("Starting OAuth authentication process...")
        self.process_monitor.track_child_processes()  # Track processes before OAuth
        self.bot = await Twitch(APP_ID, APP_SECRET)
        auth = UserAuthenticator(self.bot, USER_SCOPE)
        token, refresh_token = await auth.authenticate()
        await self.bot.set_user_authentication(token, USER_SCOPE, refresh_token)
        self.process_monitor.track_child_processes()  # Track any new processes after OAuth
        self.process_monitor.track_new_threads()      # Track any new threads
        logger.debug("OAuth authentication completed")
        
        # Get broadcaster and moderator IDs
        await self._get_user_ids()
        
        # Initialize chat
        self.chat = await Chat(self.bot)
        self.chat.register_event(ChatEvent.READY, self._on_chat_ready)
        
        logger.info("Twitch API initialized")
    
    async def _get_user_ids(self):
        """Get broadcaster and moderator user IDs."""
        # Get broadcaster ID
        async for info in self.bot.get_users(logins=[TARGET_CHANNEL]):
            self.broadcaster_id = info.id
            break
        
        if not self.broadcaster_id:
            raise ValueError(f"Failed to get broadcaster ID for channel: {TARGET_CHANNEL}")
        
        # Get moderator ID
        async for info in self.bot.get_users(logins=[BOT_NAME]):
            self.moderator_id = info.id
            break
        
        if not self.moderator_id:
            raise ValueError(f"Failed to get moderator ID for user: {BOT_NAME}")
        
        logger.info(f"Retrieved user IDs - Broadcaster: {self.broadcaster_id}, Moderator: {self.moderator_id}")
    
    async def _on_chat_ready(self, ready_event: EventData):
        """Handle chat ready event."""
        await ready_event.chat.join_room(TARGET_CHANNEL)
        logger.info(f"Bot connected to channel: {TARGET_CHANNEL}")
        
        # Provide Twitch context to modules that need it
        await self._provide_twitch_context_to_modules()
    
    async def _provide_twitch_context_to_modules(self):
        """Provide Twitch API context to modules that need it."""
        for module_name in self.module_manager.get_running_modules():
            module_def = self.module_manager.registry.get_module(module_name)
            if module_def and hasattr(module_def.module, 'set_twitch_context'):
                module_def.module.set_twitch_context(
                    self.broadcaster,
                    self.chat,
                    self.broadcaster_id,
                    self.moderator_id
                )
                logger.debug(f"Provided Twitch context to module: {module_name}")
    
    async def start(self):
        """Start the bot and all auto-start modules."""
        logger.info("Starting Modular Twitch Bot...")
        
        # Start auto-start modules
        started_modules = await self.module_manager.start_auto_start_modules()
        logger.info(f"Started modules: {started_modules}")
        
        # Register module commands with chat
        self._register_module_commands()
        
        # Start chat
        self.chat.start()
        
        logger.info("Bot started successfully")
    
    def _register_module_commands(self):
        """Register all module commands with the chat system."""
        commands = self.module_manager.get_registered_commands()
        registered_count = 0
        
        for command_name, command_def in commands.items():
            # Skip aliases - they're handled by the main command
            if command_name in [alias for cmd in commands.values() for alias in cmd.aliases]:
                continue
                
            self.chat.register_command(command_name, command_def.handler)
            logger.debug(f"Registered command: {command_name}")
            registered_count += 1
        
        logger.info(f"Registered {registered_count} commands from modules")
    
    def _register_module_commands_for_module(self, module_name: str, module_def):
        """Register commands for a specific module only."""
        commands = self.module_manager.registry.get_module(module_name).commands
        
        for command in commands:
            # Register main command
            self.chat.register_command(command.name, command.handler)
            logger.debug(f"Registered command: {command.name} for module: {module_name}")
            
            # Register aliases
            for alias in command.aliases:
                self.chat.register_command(alias, command.handler)
                logger.debug(f"Registered alias: {alias} for command: {command.name} in module: {module_name}")
        
        logger.info(f"Registered {len(commands)} commands for module: {module_name}")
    
    async def stop(self):
        """Stop the bot and all modules."""
        logger.info("Stopping Modular Twitch Bot...")
        
        try:
            # Stop chat first to prevent new messages
            if self.chat:
                logger.debug("Stopping chat connection...")
                self.chat.stop()
            
            # Stop all modules and their background tasks
            logger.debug("Shutting down Module Manager...")
            await self.module_manager.shutdown()
            
            # Close Twitch API connections
            if self.bot:
                logger.debug("Closing bot API connection...")
                await self.bot.close()
            
            if self.broadcaster:
                logger.debug("Closing broadcaster API connection...")
                await self.broadcaster.close()
            
            # Cancel any remaining background tasks
            await self._cancel_remaining_tasks()
            
            # Cleanup all monitored processes and threads
            if hasattr(self, 'process_monitor') and self.process_monitor:
                logger.debug("Cleaning up monitored processes and threads...")
                self.process_monitor.cleanup_all()
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        
        logger.info("Bot stopped")
    
    async def _cancel_remaining_tasks(self):
        """Cancel any remaining asyncio tasks."""
        try:
            # Get all tasks except the current one
            current_task = asyncio.current_task()
            all_tasks = [task for task in asyncio.all_tasks() if task is not current_task]
            
            if all_tasks:
                logger.debug(f"Cancelling {len(all_tasks)} remaining background tasks...")
                
                # Cancel all tasks
                for task in all_tasks:
                    if not task.done():
                        task.cancel()
                
                # Wait for tasks to complete cancellation with timeout
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*all_tasks, return_exceptions=True),
                        timeout=5.0  # 5 second timeout
                    )
                    logger.debug("All background tasks cancelled")
                except asyncio.TimeoutError:
                    logger.warning("Some background tasks did not respond to cancellation within 5 seconds")
            
        except Exception as e:
            logger.warning(f"Error cancelling background tasks: {e}")
    
    async def _on_module_started(self, module_name: str, module_def):
        """Handle module started event."""
        logger.info(f"Module started: {module_name}")
        
        # Provide Twitch context if chat is ready
        if self.chat and hasattr(module_def.module, 'set_twitch_context'):
            module_def.module.set_twitch_context(
                self.broadcaster,
                self.chat,
                self.broadcaster_id,
                self.moderator_id
            )
        
        # Register commands only for this specific module (not all modules)
        if self.chat:
            self._register_module_commands_for_module(module_name, module_def)
    
    async def _on_module_stopped(self, module_name: str, module_def):
        """Handle module stopped event."""
        logger.info(f"Module stopped: {module_name}")
        
        # Commands are automatically unregistered by the module manager
        # We might need to refresh the chat command registration here
        # if we want to support dynamic command removal
    
    async def _on_module_error(self, module_name: str, module_def, error: Exception):
        """Handle module error event."""
        logger.error(f"Module error in {module_name}: {error}")
    
    def get_status(self) -> dict:
        """Get comprehensive bot status."""
        return {
            'running_modules': self.module_manager.get_running_modules(),
            'all_modules': self.module_manager.get_all_modules_info(),
            'registered_commands': list(self.module_manager.get_registered_commands().keys()),
            'chat_connected': self.chat is not None and self.chat.is_ready if self.chat else False
        }


async def main():
    """Main application entry point."""
    bot = ModularTwitchBot()
    
    def signal_handler():
        """Handle shutdown signals gracefully."""
        logger.info("Shutdown signal received...")
        # Create a task to stop the bot
        asyncio.create_task(bot.stop())
    
    try:
        # Initialize the bot
        await bot.initialize()
        
        # Start the bot
        await bot.start()
        
        # Keep the bot running
        logger.debug("Gambling Charity Bot is running. Press Ctrl+C to stop...")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("\nShutdown signal received...")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
    finally:
        # Ensure cleanup always happens
        try:
            await bot.stop()
        except Exception as e:
            logger.error(f"Error during final cleanup: {e}")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutdown complete")
