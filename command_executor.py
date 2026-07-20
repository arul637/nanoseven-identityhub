import subprocess
import shlex
from config import Config

ALLOWED_COMMANDS = {
    "useradd": {"min_args": 2, "prefix": ["useradd"]},
    "usermod": {"min_args": 2, "prefix": ["usermod"]},
    "userdel": {"min_args": 2, "prefix": ["userdel"]},
    "passwd": {"min_args": 2, "prefix": ["passwd"]},
    "chage": {"min_args": 2, "prefix": ["chage"]},
    "groupadd": {"min_args": 2, "prefix": ["groupadd"]},
    "groupmod": {"min_args": 2, "prefix": ["groupmod"]},
    "groupdel": {"min_args": 2, "prefix": ["groupdel"]},
    "gpasswd": {"min_args": 2, "prefix": ["gpasswd"]},
    "id": {"min_args": 1, "prefix": ["id"]},
    "getent": {"min_args": 2, "prefix": ["getent"]},
    "cat": {"min_args": 2, "prefix": ["cat"]},
    "chsh": {"min_args": 2, "prefix": ["chsh"]},
    "chfn": {"min_args": 2, "prefix": ["chfn"]},
}

MOCK_RESPONSES = {
    "useradd": {"success": True, "return_code": 0, "stdout": "", "stderr": ""},
    "usermod": {"success": True, "return_code": 0, "stdout": "", "stderr": ""},
    "userdel": {"success": True, "return_code": 0, "stdout": "", "stderr": ""},
    "passwd": {"success": True, "return_code": 0, "stdout": "", "stderr": ""},
    "chage": {"success": True, "return_code": 0, "stdout": "", "stderr": ""},
    "groupadd": {"success": True, "return_code": 0, "stdout": "", "stderr": ""},
    "groupmod": {"success": True, "return_code": 0, "stdout": "", "stderr": ""},
    "groupdel": {"success": True, "return_code": 0, "stdout": "", "stderr": ""},
    "gpasswd": {"success": True, "return_code": 0, "stdout": "", "stderr": ""},
    "id": {"success": True, "return_code": 0, "stdout": "uid=1000(testuser) gid=1000(testuser) groups=1000(testuser)", "stderr": ""},
    "getent": {"success": True, "return_code": 0, "stdout": "", "stderr": ""},
    "cat": {"success": True, "return_code": 0, "stdout": "mock file content", "stderr": ""},
    "chsh": {"success": True, "return_code": 0, "stdout": "", "stderr": ""},
    "chfn": {"success": True, "return_code": 0, "stdout": "", "stderr": ""},
}


def _sanitize_args(args):
    sanitized = []
    for a in args:
        sanitized.append(a.replace("\n", "").replace("\r", ""))
    return sanitized


def execute(command_key, args, timeout=None):
    if command_key not in ALLOWED_COMMANDS:
        return {
            "success": False,
            "return_code": -1,
            "stdout": "",
            "stderr": f"Command '{command_key}' is not allowed.",
        }

    cmd_info = ALLOWED_COMMANDS[command_key]

    if isinstance(args, str):
        args_list = shlex.split(args)
    else:
        args_list = list(args)

    if len(args_list) < cmd_info["min_args"]:
        return {
            "success": False,
            "return_code": -1,
            "stdout": "",
            "stderr": f"'{command_key}' requires at least {cmd_info['min_args']} arguments.",
        }

    args_list = _sanitize_args(args_list)
    cmd = cmd_info["prefix"] + args_list

    if Config.MOCK_MODE:
        result = MOCK_RESPONSES.get(command_key, {
            "success": True,
            "return_code": 0,
            "stdout": "",
            "stderr": "",
        })
        result["cmd"] = " ".join(cmd)
        return result

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout or Config.COMMAND_TIMEOUT,
        )
        return {
            "success": proc.returncode == 0,
            "return_code": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "cmd": " ".join(cmd),
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "return_code": -1,
            "stdout": "",
            "stderr": f"Command timed out after {timeout or Config.COMMAND_TIMEOUT}s.",
        }
    except FileNotFoundError:
        return {
            "success": False,
            "return_code": -1,
            "stdout": "",
            "stderr": f"Command '{cmd[0]}' not found on the system.",
        }
    except Exception as e:
        return {
            "success": False,
            "return_code": -1,
            "stdout": "",
            "stderr": str(e),
        }


def user_exists(username):
    result = execute("id", [username])
    return result["success"]


def getent_passwd():
    result = execute("getent", ["passwd"])
    if result["success"] and result["stdout"]:
        return result["stdout"].split("\n")
    return []


def getent_group():
    result = execute("getent", ["group"])
    if result["success"] and result["stdout"]:
        return result["stdout"].split("\n")
    return []


def read_file(filepath):
    result = execute("cat", [filepath])
    if result["success"] and result["stdout"]:
        return result["stdout"].split("\n")
    return []
