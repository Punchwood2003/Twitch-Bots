# Modular Twitch Bot System

## Overview

This system provides:

- **Modular Architecture**: Each bot feature is a self-contained module
- **Feature Flag Integration**: Each module can declare its own feature flags with permissions
- **Database Schema Management**: Modules can define their own database schemas
- **Lifecycle Management**: Start, stop, and restart modules independently
- **Dependency Resolution**: Modules can depend on other modules
- **Command Registration**: Modules can register chat commands dynamically
- **Runtime Configuration**: Enable/disable modules without restarting the bot

## Architecture

### Core Components

1. **Module Manager** (`module_manager/`): Core orchestration system
   - `ModuleManager`: Main orchestrator for module lifecycle
   - `ModuleRegistry`: Handles module discovery and registration
   - `ModuleDefinition`: Defines the structure of a module

2. **Feature Flags** (`feature_flags/`): Permission-based feature flag system
3. **Database Management** (`db/`): Modular database schema management  
4. **Modules** (`modules/`): Individual bot modules

### Module Structure

Each module must inherit from `TwitchModule` and implement:

```python
class MyModule(TwitchModule):
    @property
    def module_name(self) -> str:
        return "my_module"
    
    @property 
    def module_description(self) -> str:
        return "Description of what this module does"
    
    @property
    def module_version(self) -> str:
        return "1.0.0"
    
    def get_feature_flags(self) -> List[tuple[FeatureFlag, PermissionLevel]]:
        # Define feature flags this module owns
        pass
    
    def get_database_schema(self) -> Optional[ModuleSchema]:
        # Define database tables this module needs
        pass
    
    def get_commands(self) -> List[CommandDefinition]:
        # Define chat commands this module provides
        pass
    
    def get_config(self) -> ModuleConfig:
        # Define module configuration
        pass
```

## Usage

### Running the Modular Bot

```bash
python modular_bot.py
```

### Managing Modules via CLI

```bash
# List all modules
python module_cli.py list

# Show module information
python module_cli.py info charity_gambling

# Enable/disable modules
python module_cli.py enable charity_gambling
python module_cli.py disable charity_gambling

# Start/stop modules
python module_cli.py start charity_gambling
python module_cli.py stop charity_gambling

# Set auto-start
python module_cli.py autostart charity_gambling on

# Show system status
python module_cli.py status
```

## Creating New Modules

1. Create a new directory under `modules/`
2. Implement a class inheriting from `TwitchModule`
3. Define feature flags, database schema, commands, and configuration
4. Register the module in your main application

Example module structure:
```
modules/
  my_new_module/
    __init__.py
    my_module.py
```

### Module Configuration

```python
def get_config(self) -> ModuleConfig:
    return ModuleConfig(
        enabled_by_default=True,    # Should module be enabled when first registered?
        auto_start=True,            # Should module start when bot starts?
        dependencies=["other_mod"], # Modules this depends on
        config_schema={             # Configuration schema
            "setting1": {"type": "string", "default": "value"}
        }
    )
```

### Feature Flag Declaration

```python
def get_feature_flags(self) -> List[tuple[FeatureFlag, PermissionLevel]]:
    return [
        (FeatureFlag(
            name="my_feature_enabled",
            description="Enable my feature",
            default_value=False,
            flag_type=bool
        ), PermissionLevel.MODERATOR)
    ]
```

### Database Schema Declaration

```python
def get_database_schema(self) -> Optional[ModuleSchema]:
    return ModuleSchema(
        module_name=self.module_name,
        tables=[
            TableDefinition(
                name="my_table",
                module=self.module_name,
                sql="CREATE TABLE IF NOT EXISTS my_table (id SERIAL PRIMARY KEY, ...)"
            )
        ],
        indexes=["CREATE INDEX IF NOT EXISTS idx_my_table_id ON my_table(id);"]
    )
```

### Command Declaration

```python
def get_commands(self) -> List[CommandDefinition]:
    return [
        CommandDefinition(
            name="mycommand",
            handler=self._my_command_handler,
            description="Does something cool",
            permission_required=True,
            aliases=["mc"],
            cooldown_seconds=30.0
        )
    ]

async def _my_command_handler(self, cmd: ChatCommand):
    await cmd.reply("Hello from my module!")
```

## Module States

- **INACTIVE**: Module is registered but not running
- **STARTING**: Module is in the process of starting
- **ACTIVE**: Module is running normally
- **STOPPING**: Module is in the process of stopping  
- **ERROR**: Module encountered an error

## Dependency Management

Modules can declare dependencies on other modules. The system will:

1. Automatically start dependencies before starting a module
2. Prevent stopping modules that other running modules depend on
3. Resolve circular dependencies and provide clear error messages

## Integration with Existing Systems

### Feature Flags

Each module can declare feature flags with specific permissions:
- **READ_ONLY**: Modules other than owning module can view value of flag
- **READ_WRITE**: Modules other than owning module can read and modify value of flag
- **OWNER_ONLY**: Only the owning module can view or modify the flag

### Database

Modules declare their database schema requirements. The system will:
- Create tables and indexes automatically
- Handle schema updates and migrations
- Provide database connection management

## Configuration Files

- `module_registry.json`: Stores module states and configuration
- `feature_flags.json`: Stores feature flag values
- Database configuration in `db/config.py`

## Future Enhancements

- **Web UI**: Browser-based module and feature flag management
- **Hot Reloading**: Update module code without restarting
- **Module Marketplace**: Share modules between bot instances
- **Advanced Dependencies**: Version constraints and optional dependencies
- **Health Monitoring**: Module health checks and automatic recovery
- **Configuration Validation**: Schema validation for module configurations

## Error Handling

The system provides comprehensive error handling:
- Module errors don't crash the entire bot
- Automatic error reporting and logging
- Module isolation prevents cascading failures
- Recovery mechanisms for transient errors

## Performance Considerations

- Modules run in the same event loop for efficiency
- Database connections are pooled and shared
- Feature flag lookups are cached for performance
- Module state is persisted for quick restarts
