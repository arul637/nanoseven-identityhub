# Linux User and Group Management Automation with Security Policies

A secure, Flask-based web application for managing Linux users and groups through a modern administration dashboard. Provides a GUI layer over standard Linux administration tools with built-in security policies, audit logging, and system synchronization.

## Overview

This application acts as a secure, GUI-based management layer over existing Linux user and group administration tools (`useradd`, `usermod`, `userdel`, `groupadd`, `groupmod`, `groupdel`, `passwd`, `chage`, `gpasswd`). It enforces security policies, maintains an audit trail, and prevents unsafe operations through validation and confirmation workflows.

## Features

- **Authentication** — Secure administrator login with password hashing, session management, account lockout, and login attempt tracking
- **Dashboard** — Real-time overview of users, groups, locked/expired accounts, recent activity, and shell usage
- **User Management** — Create, view, edit, lock, unlock, delete users; change passwords; manage group memberships; set account and password expiration
- **Group Management** — Create, rename, delete groups; add/remove members; privileged group detection with confirmation warnings
- **Security Policies** — Configurable password policies, account policies, username policies, and group policies stored in SQLite
- **Password Security** — Real-time password strength checking, policy validation, and secure password generation using Python `secrets`
- **System Sync** — Synchronize users and groups from `/etc/passwd` and `/etc/group` into the local database with full history tracking
- **Audit Logging** — Comprehensive logging of all administrative actions with search, filtering, and pagination
- **System Information** — Display Linux distribution, kernel version, hostname, architecture, and sync status
- **Mock Mode** — Safe development mode using simulated command execution for testing without modifying the actual system

## Architecture

```
app.py
  |
  +-- auth.py              Authentication routes
  +-- dashboard.py         Dashboard routes
  +-- user_management.py   User CRUD and management
  +-- group_management.py  Group CRUD and management
  +-- security_policy.py   Security policy configuration
  +-- password_security.py Password strength and generation
  +-- system_sync.py       /etc/passwd and /etc/group sync
  +-- audit_logs.py        Activity logging and queries
  +-- system_info.py       System information display
  +-- command_executor.py  Secure Linux command execution
  +-- database.py          SQLite database layer
  +-- config.py            Application configuration
```

## Project Structure

```
project/
  app.py
  auth.py | dashboard.py | user_management.py
  group_management.py | security_policy.py
  system_sync.py | audit_logs.py | system_info.py
  command_executor.py | password_security.py
  config.py | database.py
  templates/          Jinja2 HTML templates
  static/css/         Stylesheet
  static/js/          JavaScript modules
  database/           SQLite database storage
  requirements.txt
  .env.example
  .gitignore
  README.md
```

## Technology Stack

- **Backend:** Flask 3.0 (Python 3.9+)
- **Database:** SQLite with parameterized queries
- **Authentication:** Werkzeug password hashing
- **Frontend:** Vanilla JavaScript, CSS custom properties
- **Templates:** Jinja2 with template inheritance

## Installation

### Prerequisites

- Python 3.9 or higher
- pip
- Virtual environment (recommended)
- Linux system (for production use) or any OS (for development/mock mode)

### Setup

```bash
# Clone the repository
git clone <repo-url>
cd linux-user-group-manager

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
```

### Database Initialization

The SQLite database is created automatically on first run. The file is stored at `database/linux_manager.db`.

Tables are created automatically:
- `admins` — Administrator accounts
- `linux_users` — Linux user records
- `linux_groups` — Linux group records
- `user_group_memberships` — User-group associations
- `security_policies` — Policy configuration
- `audit_logs` — Activity log entries
- `sync_history` — Sync operation history
- `login_attempts` — Login attempt tracking
- `system_settings` — System configuration

### Administrator Setup

On first run, you will be redirected to a setup page to create the initial administrator account.

### Running the Application

#### Development Mode (Mock)

```bash
export MOCK_MODE=True
export FLASK_DEBUG=True
python app.py
```

The application will start at `http://0.0.0.0:5000`. In mock mode, no system commands are executed — all operations are simulated.

#### Production Mode

```bash
export MOCK_MODE=False
export FLASK_DEBUG=False
export SECRET_KEY=your-strong-secret-key
python app.py
```

**Important:** In production mode, the application requires appropriate Linux permissions (root or sudo) to execute user/group management commands.

## Linux Permissions

The application executes Linux administration commands through a secure executor. The Flask process needs:

- Root privileges **or** passwordless sudo access for user/group management commands
- Read access to `/etc/passwd` and `/etc/group` for synchronization

**Recommendation:** Run behind a reverse proxy (nginx) with SSL termination. Restrict network access to trusted administrators only.

## Security Considerations

- **Command Injection** — All commands use `subprocess.run()` with `shell=False`. Commands and arguments are validated against an allowlist
- **SQL Injection** — All queries use parameterized SQL. No raw string interpolation
- **Password Storage** — Administrator passwords hashed with Werkzeug's `generate_password_hash`
- **Session Security** — HTTP-only, SameSite=Lax cookies; session timeout after 1 hour
- **Account Lockout** — Accounts locked after 5 failed login attempts for 15 minutes
- **Audit Logging** — All administrative actions are logged and searchable
- **Privileged Groups** — Adding users to privileged groups (sudo, wheel, docker) requires explicit confirmation
- **CSRF** — CSRF protection enabled via Flask-WTF / Flask session-based token validation

## System Synchronization

The Sync feature reads from `/etc/passwd` and `/etc/group` and merges data into the local database. It detects new users, updated users, and missing users (without auto-deleting records). Sync history is maintained for auditing.

## Testing

The application includes a comprehensive mock mode that simulates all Linux commands without affecting the actual system. This is enabled by default.

```bash
# Run with mock mode (default, safe for testing)
python app.py

# The banner will show: "MOCK MODE"
```

To test against a live system, set `MOCK_MODE=False` in your `.env` file.

## Future Enhancements

- SSH key management
- Password policy enforcement on password change
- Bulk user import/export (CSV)
- Two-factor authentication
- LDAP/Active Directory integration
- REST API for external automation
- User session monitoring and force-logout
- Automated password rotation

## License

MIT
