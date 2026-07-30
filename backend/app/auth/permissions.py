"""RBAC permission codes, role names, and the role -> permission matrix.

These constants are the single source of truth for both the JWT-embedded
permission claims and the `seed_roles_and_permissions` migration - keep them
in sync with any future permission additions.
"""


class PermissionCode:
    FOLDER_READ = "folder.read"
    FOLDER_CREATE = "folder.create"
    FOLDER_DELETE = "folder.delete"
    FOLDER_SCAN = "folder.scan"
    FILE_READ = "file.read"
    FILE_DOWNLOAD = "file.download"
    FILE_SUMMARY = "file.summary"
    FILE_ENTITIES = "file.entities"
    SEARCH_EXECUTE = "search.execute"
    CHAT_EXECUTE = "chat.execute"
    ADMIN_USERS = "admin.users"
    ADMIN_ROLES = "admin.roles"
    ADMIN_SETTINGS = "admin.settings"


ALL_PERMISSIONS: list[tuple[str, str]] = [
    (PermissionCode.FOLDER_READ, "View monitored folders"),
    (PermissionCode.FOLDER_CREATE, "Add a new monitored folder"),
    (PermissionCode.FOLDER_DELETE, "Remove a monitored folder"),
    (PermissionCode.FOLDER_SCAN, "Trigger or view a folder scan"),
    (PermissionCode.FILE_READ, "View indexed file listings and details"),
    (PermissionCode.FILE_DOWNLOAD, "Download original file content"),
    (PermissionCode.FILE_SUMMARY, "View or generate AI file summaries"),
    (PermissionCode.FILE_ENTITIES, "View extracted document entities"),
    (PermissionCode.SEARCH_EXECUTE, "Run search queries"),
    (PermissionCode.CHAT_EXECUTE, "Use the AI chat/assistant feature"),
    (PermissionCode.ADMIN_USERS, "Manage users"),
    (PermissionCode.ADMIN_ROLES, "Manage roles and permission assignments"),
    (PermissionCode.ADMIN_SETTINGS, "Manage organization/application settings"),
]

ROLE_NAMES = ["Super Admin", "Organization Admin", "Manager", "Employee", "Viewer"]

ROLE_PERMISSION_MATRIX: dict[str, list[str]] = {
    "Super Admin": [code for code, _ in ALL_PERMISSIONS],
    "Organization Admin": [
        PermissionCode.FOLDER_READ,
        PermissionCode.FOLDER_CREATE,
        PermissionCode.FOLDER_DELETE,
        PermissionCode.FOLDER_SCAN,
        PermissionCode.FILE_READ,
        PermissionCode.FILE_DOWNLOAD,
        PermissionCode.FILE_SUMMARY,
        PermissionCode.FILE_ENTITIES,
        PermissionCode.SEARCH_EXECUTE,
        PermissionCode.CHAT_EXECUTE,
        PermissionCode.ADMIN_USERS,
        PermissionCode.ADMIN_ROLES,
        PermissionCode.ADMIN_SETTINGS,
    ],
    "Manager": [
        PermissionCode.FOLDER_READ,
        PermissionCode.FOLDER_CREATE,
        PermissionCode.FOLDER_SCAN,
        PermissionCode.FILE_READ,
        PermissionCode.FILE_DOWNLOAD,
        PermissionCode.FILE_SUMMARY,
        PermissionCode.FILE_ENTITIES,
        PermissionCode.SEARCH_EXECUTE,
        PermissionCode.CHAT_EXECUTE,
    ],
    "Employee": [
        PermissionCode.FOLDER_READ,
        PermissionCode.FILE_READ,
        PermissionCode.FILE_DOWNLOAD,
        PermissionCode.FILE_SUMMARY,
        PermissionCode.FILE_ENTITIES,
        PermissionCode.SEARCH_EXECUTE,
        PermissionCode.CHAT_EXECUTE,
    ],
    "Viewer": [
        PermissionCode.FOLDER_READ,
        PermissionCode.FILE_READ,
        PermissionCode.SEARCH_EXECUTE,
    ],
}
