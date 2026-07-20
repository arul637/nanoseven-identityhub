import sqlite3
import os
from contextlib import contextmanager
from config import Config


def get_db_path():
    db_dir = os.path.dirname(Config.DATABASE_PATH)
    os.makedirs(db_dir, exist_ok=True)
    return Config.DATABASE_PATH


@contextmanager
def get_db():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS linux_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                uid INTEGER,
                gid INTEGER,
                full_name TEXT DEFAULT '',
                home_directory TEXT DEFAULT '/home/username',
                login_shell TEXT DEFAULT '/bin/bash',
                status TEXT DEFAULT 'active',
                locked INTEGER DEFAULT 0,
                expired INTEGER DEFAULT 0,
                password_expires TEXT,
                account_expires TEXT,
                inactive_days INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS linux_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name TEXT UNIQUE NOT NULL,
                gid INTEGER,
                privileged INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_group_memberships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                group_name TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(username, group_name)
            );

            CREATE TABLE IF NOT EXISTS security_policies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                policy_key TEXT UNIQUE NOT NULL,
                policy_value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_username TEXT NOT NULL,
                action TEXT NOT NULL,
                target TEXT DEFAULT '',
                description TEXT DEFAULT '',
                result TEXT DEFAULT 'success',
                ip_address TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sync_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                users_discovered INTEGER DEFAULT 0,
                new_users INTEGER DEFAULT 0,
                updated_users INTEGER DEFAULT 0,
                missing_users INTEGER DEFAULT 0,
                groups_discovered INTEGER DEFAULT 0,
                new_groups INTEGER DEFAULT 0,
                updated_groups INTEGER DEFAULT 0,
                duration_ms INTEGER DEFAULT 0,
                result TEXT DEFAULT 'success',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS login_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                ip_address TEXT DEFAULT '',
                success INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS system_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)


def get_default_policies():
    return {
        "min_password_length": "8",
        "require_uppercase": "true",
        "require_lowercase": "true",
        "require_number": "true",
        "require_special": "true",
        "password_expiry_days": "90",
        "password_history": "5",
        "default_shell": "/bin/bash",
        "default_account_expiry_days": "0",
        "default_inactive_days": "0",
        "allowed_shells": "/bin/bash,/bin/sh,/bin/zsh,/bin/dash,/usr/bin/zsh",
        "min_username_length": "3",
        "max_username_length": "32",
        "allowed_username_chars": "a-z0-9_-",
        "reserved_usernames": "root,admin,daemon,bin,sys,sync,games,man,lp,mail,news,uucp,proxy,www-data,backup,list,irc,gnats,nobody,systemd-bus-proxy,systemd-network,systemd-resolve,systemd-timesync,_apt",
        "privileged_groups": "sudo,wheel,adm,docker,root",
        "restricted_groups": "sudo,wheel,root",
        "groups_require_confirmation": "sudo,wheel,docker,root,adm",
    }


def init_default_policies():
    defaults = get_default_policies()
    with get_db() as db:
        for key, value in defaults.items():
            db.execute(
                "INSERT OR IGNORE INTO security_policies (policy_key, policy_value) VALUES (?, ?)",
                (key, value),
            )
