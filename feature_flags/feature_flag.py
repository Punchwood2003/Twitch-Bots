"""
Feature flag identifier for the feature flags system.

This module defines the core FeatureFlag class that represents a feature flag
identifier. FeatureFlags are lightweight objects that hold just the name of
a flag, not its value. The actual values are managed by the FeatureFlagManager.
"""

from pydantic import BaseModel, Field


class FeatureFlag(BaseModel):
    """
    Feature flag identifier with unique name.
    
    FeatureFlag represents the name associated with a feature flag, not the value 
    of the flag itself. FeatureFlags should have unique names across the system.
    They are used to specify configuration values for features, ranging from 
    simple on/off toggles to complex behavioral parameters.
    
    Examples:
        ```python
        # Simple boolean flags:
        DEBUG_MODE = FeatureFlag("debug_mode")
        ENABLE_LOGGING = FeatureFlag("enable_logging")
        
        # Configuration flags:
        MAX_CONNECTIONS = FeatureFlag("max_connections")
        TIMEOUT_SECONDS = FeatureFlag("timeout_seconds")
        
        # Feature toggles:
        NEW_UI_ENABLED = FeatureFlag("new_ui_enabled")
        BETA_FEATURES = FeatureFlag("beta_features")
        ```
    
    Attributes:
        name: The unique identifier for this feature flag
    """

    name: str = Field(alias="name", description="The unique identifier for this feature flag")

    def __init__(self, name: str):
        """
        Initialize a new FeatureFlag.
        
        Args:
            name: The unique identifier for this feature flag
        """
        super().__init__(name=name)

    def __eq__(self, other) -> bool:
        """
        Check equality with another FeatureFlag.
        
        Args:
            other: Another object to compare with
            
        Returns:
            True if both are FeatureFlags with the same name
        """
        if isinstance(other, FeatureFlag):
            return self.name == other.name
        return False

    def __hash__(self) -> int:
        """
        Generate hash based on the flag name.
        
        Returns:
            Hash value for this FeatureFlag
        """
        return hash(self.name)

    def __repr__(self) -> str:
        """
        String representation of the FeatureFlag.
        
        Returns:
            Developer-friendly string representation
        """
        return f"FeatureFlag(name={self.name!r})"

    def __str__(self) -> str:
        """
        User-friendly string representation.
        
        Returns:
            The flag name as a string
        """
        return self.name

    @property
    def identifier(self) -> str:
        """
        Get the flag identifier.
        
        Returns:
            The flag name/identifier
        """
        return self.name

    def is_valid_name(self) -> bool:
        """
        Check if the flag name follows naming conventions.
        
        Returns:
            True if the name is valid (non-empty, reasonable length)
        """
        return (
            isinstance(self.name, str) and 
            len(self.name.strip()) > 0 and 
            len(self.name) <= 100 and
            not self.name.isspace()
        )
