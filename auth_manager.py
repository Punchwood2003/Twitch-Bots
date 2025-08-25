"""
Enhanced Twitch Authentication Manager

This module handles authentication for both the broadcaster and bot accounts.
It checks for existing tokens in the environment file and only prompts for
authentication if tokens are missing or invalid.

Usage:
    python auth_manager.py --broadcaster  # Authenticate broadcaster only
    python auth_manager.py --bot         # Authenticate bot only
    python auth_manager.py --all         # Authenticate both (default)
    python auth_manager.py --check       # Check current token status
"""

import argparse
import asyncio
import json
import os
import re
from pathlib import Path
from typing import Tuple, Optional

from dotenv import load_dotenv, set_key
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.twitch import Twitch
from twitchAPI.type import AuthScope


class TwitchAuthManager:
    """Manages Twitch authentication for broadcaster and bot accounts."""
    
    def __init__(self):
        load_dotenv()
        self.app_id = os.getenv('BOT_CLIENT_ID')
        self.app_secret = os.getenv('BOT_CLIENT_SECRET')
        self.env_file = Path('.env')
        
        # Define scopes for each account type
        self.broadcaster_scopes = [
            AuthScope.CHANNEL_READ_SUBSCRIPTIONS,  # Only what's actually needed for broadcaster
        ]
        
        self.bot_scopes = [
            AuthScope.CHAT_READ,                    # Read chat messages
            AuthScope.CHAT_EDIT,                    # Send chat messages
            AuthScope.CHANNEL_MANAGE_BROADCAST,     # Manage channel broadcast settings
            AuthScope.CHANNEL_READ_SUBSCRIPTIONS,   # Read subscription info
            AuthScope.MODERATOR_READ_CHATTERS,      # Read chatters list
            AuthScope.MODERATOR_READ_FOLLOWERS,     # Read followers list
        ]
        
        if not self.app_id or not self.app_secret:
            raise ValueError("BOT_CLIENT_ID and BOT_CLIENT_SECRET must be set in .env file")
    
    def _check_tokens_in_env(self, account_type: str) -> bool:
        """Check if tokens exist in environment variables."""
        if account_type == 'broadcaster':
            access_token = os.getenv('BROADCASTER_ACCESS_TOKEN')
            refresh_token = os.getenv('BROADCASTER_REFRESH_TOKEN')
        elif account_type == 'bot':
            access_token = os.getenv('BOT_ACCESS_TOKEN')
            refresh_token = os.getenv('BOT_REFRESH_TOKEN')
        else:
            raise ValueError("account_type must be 'broadcaster' or 'bot'")
        
        return bool(access_token and refresh_token and 
                   access_token.strip() and refresh_token.strip())
    
    async def _validate_token(self, access_token: str, refresh_token: str = None, account_type: str = 'broadcaster') -> bool:
        """Validate if a token is still valid by making a test API call."""
        try:
            twitch = await Twitch(self.app_id, self.app_secret)
            
            # Get the appropriate scopes for the account type
            scopes = self.broadcaster_scopes if account_type == 'broadcaster' else self.bot_scopes
            
            # Set user authentication with refresh token if available for auto-refresh
            if refresh_token:
                await twitch.set_user_authentication(access_token, scopes, refresh_token)
            else:
                await twitch.set_user_authentication(access_token, scopes)
            
            # Test the token with a simple API call
            await twitch.close()
            return True
        except Exception as e:
            print(f"Error validating token: {e}")
            return False
    
    async def _authenticate_account(self, account_type: str) -> Tuple[str, str]:
        """Authenticate an account and return access and refresh tokens."""
        scopes = self.broadcaster_scopes if account_type == 'broadcaster' else self.bot_scopes
        
        print(f"\n🔐 Starting {account_type} authentication...")
        print(f"Required scopes: {', '.join([scope.value for scope in scopes])}")
        print(f"Please log in as the {account_type} account when prompted.")
        
        twitch = await Twitch(self.app_id, self.app_secret)
        auth = UserAuthenticator(twitch, scopes)
        
        try:
            access_token, refresh_token = await auth.authenticate()
            
            # Set the user authentication with refresh token for proper auto-refresh setup
            await twitch.set_user_authentication(access_token, scopes, refresh_token)
            
            await twitch.close()
            return access_token, refresh_token
        except Exception as e:
            await twitch.close()
            raise Exception(f"Authentication failed for {account_type}: {e}")
    
    def _update_env_file(self, account_type: str, access_token: str, refresh_token: str):
        """Update the .env file with new tokens."""
        if account_type == 'broadcaster':
            access_key = 'BROADCASTER_ACCESS_TOKEN'
            refresh_key = 'BROADCASTER_REFRESH_TOKEN'
        else:
            access_key = 'BOT_ACCESS_TOKEN'
            refresh_key = 'BOT_REFRESH_TOKEN'
        
        set_key(self.env_file, access_key, access_token)
        set_key(self.env_file, refresh_key, refresh_token)
        print(f"✅ {account_type.title()} tokens updated in .env file")
    
    async def authenticate_broadcaster(self, force: bool = False) -> bool:
        """Authenticate broadcaster account if needed."""
        if not force and self._check_tokens_in_env('broadcaster'):
            print("✅ Broadcaster tokens already exist in .env file")
            
            # Validate existing token
            access_token = os.getenv('BROADCASTER_ACCESS_TOKEN')
            refresh_token = os.getenv('BROADCASTER_REFRESH_TOKEN')
            if await self._validate_token(access_token, refresh_token, 'broadcaster'):
                print("✅ Broadcaster tokens are valid")
                return True
            else:
                print("⚠️  Broadcaster tokens are invalid, re-authenticating...")
        
        try:
            access_token, refresh_token = await self._authenticate_account('broadcaster')
            self._update_env_file('broadcaster', access_token, refresh_token)
            
            # Also save to legacy file for backwards compatibility
            with open('broadcaster_token.json', 'w') as f:
                json.dump({
                    'access_token': access_token, 
                    'refresh_token': refresh_token
                }, f, indent=2)
            print("✅ Broadcaster tokens also saved to broadcaster_token.json")
            
            return True
        except Exception as e:
            print(f"❌ Broadcaster authentication failed: {e}")
            return False
    
    async def authenticate_bot(self, force: bool = False) -> bool:
        """Authenticate bot account if needed."""
        if not force and self._check_tokens_in_env('bot'):
            print("✅ Bot tokens already exist in .env file")
            
            # Validate existing token
            access_token = os.getenv('BOT_ACCESS_TOKEN')
            refresh_token = os.getenv('BOT_REFRESH_TOKEN')
            if await self._validate_token(access_token, refresh_token, 'bot'):
                print("✅ Bot tokens are valid")
                return True
            else:
                print("⚠️  Bot tokens are invalid, re-authenticating...")
        
        try:
            access_token, refresh_token = await self._authenticate_account('bot')
            self._update_env_file('bot', access_token, refresh_token)
            return True
        except Exception as e:
            print(f"❌ Bot authentication failed: {e}")
            return False
    
    async def check_all_tokens(self):
        """Check the status of all tokens."""
        print("🔍 Checking authentication status...\n")
        
        # Check broadcaster tokens
        if self._check_tokens_in_env('broadcaster'):
            access_token = os.getenv('BROADCASTER_ACCESS_TOKEN')
            refresh_token = os.getenv('BROADCASTER_REFRESH_TOKEN')
            is_valid = await self._validate_token(access_token, refresh_token, 'broadcaster')
            status = "✅ Valid" if is_valid else "❌ Invalid"
            print(f"Broadcaster tokens: {status}")
        else:
            print("Broadcaster tokens: ❌ Missing")
        
        # Check bot tokens
        if self._check_tokens_in_env('bot'):
            access_token = os.getenv('BOT_ACCESS_TOKEN')
            refresh_token = os.getenv('BOT_REFRESH_TOKEN')
            is_valid = await self._validate_token(access_token, refresh_token, 'bot')
            status = "✅ Valid" if is_valid else "❌ Invalid"
            print(f"Bot tokens: {status}")
        else:
            print("Bot tokens: ❌ Missing")
    
    async def authenticate_all(self, force: bool = False) -> bool:
        """Authenticate both broadcaster and bot accounts."""
        print("🚀 Starting complete authentication process...\n")
        
        broadcaster_success = await self.authenticate_broadcaster(force)
        print()  # Add spacing
        bot_success = await self.authenticate_bot(force)
        
        if broadcaster_success and bot_success:
            print("\n🎉 All authentication completed successfully!")
            return True
        else:
            print(f"\n⚠️  Authentication completed with issues:")
            print(f"   Broadcaster: {'✅' if broadcaster_success else '❌'}")
            print(f"   Bot: {'✅' if bot_success else '❌'}")
            return False


async def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(
        description="Twitch Authentication Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python auth_manager.py                    # Authenticate both accounts
  python auth_manager.py --broadcaster     # Authenticate broadcaster only
  python auth_manager.py --bot             # Authenticate bot only
  python auth_manager.py --check           # Check token status
  python auth_manager.py --all --force     # Force re-authentication
        """
    )
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--broadcaster', action='store_true', 
                      help='Authenticate broadcaster account only')
    group.add_argument('--bot', action='store_true', 
                      help='Authenticate bot account only')
    group.add_argument('--check', action='store_true', 
                      help='Check current token status')
    group.add_argument('--all', action='store_true', 
                      help='Authenticate both accounts (default)')
    
    parser.add_argument('--force', action='store_true', 
                       help='Force re-authentication even if tokens exist')
    
    args = parser.parse_args()
    
    try:
        auth_manager = TwitchAuthManager()
        
        if args.check:
            await auth_manager.check_all_tokens()
        elif args.broadcaster:
            await auth_manager.authenticate_broadcaster(args.force)
        elif args.bot:
            await auth_manager.authenticate_bot(args.force)
        else:  # Default to --all
            await auth_manager.authenticate_all(args.force)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(asyncio.run(main()))
