"""Unit tests for RBACService."""

import pytest
from services.saas.rbac import RBACService


class TestRoles:

    def test_default_roles_loaded(self) -> None:
        svc = RBACService()
        roles = svc.get_all_roles()
        role_names = [r.name for r in roles]
        assert "user" in role_names
        assert "trader" in role_names
        assert "admin" in role_names
        assert "super_admin" in role_names

    def test_define_custom_role(self) -> None:
        svc = RBACService()
        svc.define_role("viewer", ["trade:read"])
        perms = svc.get_role_permissions("viewer")
        assert "trade:read" in perms

    def test_get_nonexistent_role(self) -> None:
        svc = RBACService()
        assert svc.get_role_permissions("nonexistent") == []


class TestAssignRevoke:

    def test_assign_role(self) -> None:
        svc = RBACService()
        svc.assign_role("user-1", "trader")
        roles = svc.get_user_roles("user-1")
        assert "trader" in roles

    def test_assign_nonexistent_role(self) -> None:
        svc = RBACService()
        with pytest.raises(ValueError):
            svc.assign_role("user-1", "nonexistent")

    def test_revoke_role(self) -> None:
        svc = RBACService()
        svc.assign_role("user-1", "trader")
        assert svc.revoke_role("user-1", "trader") is True
        assert "trader" not in svc.get_user_roles("user-1")

    def test_revoke_nonexistent(self) -> None:
        svc = RBACService()
        assert svc.revoke_role("user-1", "trader") is False


class TestPermissions:

    def test_has_permission(self) -> None:
        svc = RBACService()
        svc.assign_role("user-1", "trader")
        assert svc.has_permission("user-1", "trade:create") is True
        assert svc.has_permission("user-1", "trade:read") is True

    def test_no_permission(self) -> None:
        svc = RBACService()
        svc.assign_role("user-1", "user")
        assert svc.has_permission("user-1", "trade:create") is False

    def test_no_role(self) -> None:
        svc = RBACService()
        assert svc.has_permission("user-1", "trade:read") is False

    def test_super_admin_all_permissions(self) -> None:
        svc = RBACService()
        svc.assign_role("user-1", "super_admin")
        assert svc.has_permission("user-1", "system:manage") is True
        assert svc.has_permission("user-1", "billing:manage") is True
        assert svc.has_permission("user-1", "affiliate:manage") is True

    def test_get_user_permissions(self) -> None:
        svc = RBACService()
        svc.assign_role("user-1", "trader")
        perms = svc.get_user_permissions("user-1")
        assert "trade:create" in perms
        assert "grid:manage" in perms

    def test_multiple_roles(self) -> None:
        svc = RBACService()
        svc.assign_role("user-1", "user")
        svc.assign_role("user-1", "admin")
        perms = svc.get_user_permissions("user-1")
        assert "trade:create" in perms
        assert "user:read" in perms

    def test_metrics(self) -> None:
        svc = RBACService()
        svc.assign_role("user-1", "trader")
        svc.has_permission("user-1", "trade:create")
        svc.has_permission("user-1", "system:manage")
        m = svc.get_metrics()
        assert m["permission_checks"] == 2
        assert m["permission_granted"] == 1
        assert m["permission_denied"] == 1
