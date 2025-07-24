"""
Permission types and data structures for feature flag management.

This module contains the permission levels, declarations, and ownership
information used throughout the feature flag system.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Any
from .feature_flag import FeatureFlag


class PermissionLevel(Enum):
    """Defines the access level for non-owner modules."""
    READ_ONLY = "read_only"
    """Non-owners can only read the flag value."""
    READ_WRITE = "read_write"
    """Non-owners can read and modify the flag value."""
    OWNER_ONLY = "owner_only"
    """Only the owner can read or modify the flag value (others cannot access at all)."""


@dataclass
class FlagDeclaration:
    """Represents a module's declaration of intent to use a feature flag."""
    flag: FeatureFlag
    permission: PermissionLevel
    default_value: Any
    description: str


@dataclass
class FlagOwnership:
    """Represents ownership and permission information for a flag."""
    owner_module: str
    access_permissions: PermissionLevel
