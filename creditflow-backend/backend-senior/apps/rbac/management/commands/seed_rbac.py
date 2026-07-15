from django.core.management.base import BaseCommand
from django.db import transaction

from apps.rbac.models import Permission, Role, RolePermission

ROLES = [
    {"code": "CLIENT", "name": "Client", "description": "Registered borrower."},
    {"code": "SUPPORT", "name": "Support", "description": "Read-mostly support operator."},
    {"code": "UNDERWRITER", "name": "Underwriter", "description": "Manual application review."},
    {"code": "ADMIN", "name": "Admin", "description": "Full platform access."},
]

PERMISSIONS = [
    {"code": "product.view", "description": "View credit products."},
    {"code": "product.manage", "description": "Create/update/deactivate credit products."},
    {"code": "application.view_own", "description": "View own credit applications."},
    {"code": "application.view_all", "description": "View all credit applications."},
    {"code": "application.approve", "description": "Approve a credit application."},
    {"code": "application.reject", "description": "Reject a credit application."},
    {"code": "loan.view_own", "description": "View own loans."},
    {"code": "user.manage", "description": "Manage users and their roles."},
    {"code": "audit.view", "description": "View the audit log."},
    {"code": "feature_flag.manage", "description": "View/change feature flags."},
]

# Doc 3 §5.2 — permission matrix.
ROLE_PERMISSIONS = {
    "CLIENT": ["product.view", "application.view_own", "loan.view_own"],
    "SUPPORT": ["product.view", "application.view_all"],
    "UNDERWRITER": ["product.view", "application.view_all", "application.approve", "application.reject"],
    "ADMIN": [
        "product.view",
        "product.manage",
        "application.view_own",
        "application.view_all",
        "application.approve",
        "application.reject",
        "loan.view_own",
        "user.manage",
        "audit.view",
        "feature_flag.manage",
    ],
}


class Command(BaseCommand):
    help = "Seeds RBAC roles, permissions and the role-permission matrix (Doc 3 §5.2, idempotent)."

    @transaction.atomic
    def handle(self, *args, **options):
        roles = {}
        for data in ROLES:
            role, _ = Role.objects.update_or_create(code=data["code"], defaults=data)
            roles[role.code] = role

        permissions = {}
        for data in PERMISSIONS:
            perm, _ = Permission.objects.update_or_create(code=data["code"], defaults=data)
            permissions[perm.code] = perm

        created_links = 0
        for role_code, perm_codes in ROLE_PERMISSIONS.items():
            for perm_code in perm_codes:
                _, created = RolePermission.objects.get_or_create(
                    role=roles[role_code], permission=permissions[perm_code]
                )
                created_links += int(created)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(ROLES)} roles, {len(PERMISSIONS)} permissions, "
                f"{created_links} new role-permission links."
            )
        )
