"""
RBACService — Role-Based Access Control.

Manages roles, permissions, and access checks. In-memory implementation
for testing; production uses database-backed role assignments.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.logging import get_logger

logger = get_logger(__name__)

# Default permissions per role
_DEFAULT_ROLES: dict[str, list[str]] = {
    "user": ["trade:read", "account:read"],
    "trader": [
        "trade:create",
        "trade:read",
        "trade:delete",
        "grid:manage",
        "account:read",
    ],
    "admin": [
        "trade:create",
        "trade:read",
        "trade:delete",
        "grid:manage",
        "risk:manage",
        "account:read",
        "account:manage",
        "user:read",
        "billing:read",
    ],
    "super_admin": [
        "trade:create",
        "trade:read",
        "trade:delete",
        "grid:manage",
        "risk:manage",
        "account:read",
        "account:manage",
        "user:read",
        "user:manage",
        "billing:read",
        "billing:manage",
        "system:manage",
        "affiliate:manage",
    ],
}


@dataclass
class Role:
    name: str
    permissions: list[str]
    description: str = ""


class RBACService:
    """Role-based access control service."""

    def __init__(self) -> None:
        self._roles: dict[str, Role] = {}
        self._user_roles: dict[str, set[str]] = {}
        self._metrics: dict[str, int] = {
            "roles_defined": 0,
            "roles_assigned": 0,
            "roles_revoked": 0,
            "permission_checks": 0,
            "permission_granted": 0,
            "permission_denied": 0,
        }
        self._register_defaults()

    def define_role(
        self, role_name: str, permissions: list[str], description: str = ""
    ) -> None:
        self._roles[role_name] = Role(
            name=role_name,
            permissions=list(permissions),
            description=description,
        )
        self._metrics["roles_defined"] += 1
        logger.info("Role defined", extra={"role_name": role_name})

    def assign_role(self, user_id: str, role_name: str) -> None:
        if role_name not in self._roles:
            raise ValueError(f"Role not defined: {role_name}")
        if user_id not in self._user_roles:
            self._user_roles[user_id] = set()
        self._user_roles[user_id].add(role_name)
        self._metrics["roles_assigned"] += 1
        logger.info("Role assigned", extra={"user_id": user_id, "role_name": role_name})

    def revoke_role(self, user_id: str, role_name: str) -> bool:
        roles = self._user_roles.get(user_id)
        if roles is None or role_name not in roles:
            return False
        roles.discard(role_name)
        self._metrics["roles_revoked"] += 1
        return True

    def has_permission(self, user_id: str, permission: str) -> bool:
        self._metrics["permission_checks"] += 1
        roles = self._user_roles.get(user_id, set())
        for role_name in roles:
            role = self._roles.get(role_name)
            if role and permission in role.permissions:
                self._metrics["permission_granted"] += 1
                return True
        self._metrics["permission_denied"] += 1
        return False

    def get_user_permissions(self, user_id: str) -> list[str]:
        roles = self._user_roles.get(user_id, set())
        permissions: set[str] = set()
        for role_name in roles:
            role = self._roles.get(role_name)
            if role:
                permissions.update(role.permissions)
        return sorted(permissions)

    def get_user_roles(self, user_id: str) -> list[str]:
        return sorted(self._user_roles.get(user_id, set()))

    def get_role_permissions(self, role_name: str) -> list[str]:
        role = self._roles.get(role_name)
        if role is None:
            return []
        return list(role.permissions)

    def get_all_roles(self) -> list[Role]:
        return list(self._roles.values())

    def get_metrics(self) -> dict[str, int]:
        return dict(self._metrics)

    def _register_defaults(self) -> None:
        for role_name, permissions in _DEFAULT_ROLES.items():
            self._roles[role_name] = Role(
                name=role_name,
                permissions=list(permissions),
            )
