import secrets
import string
import re
from database import get_db

COMMON_PATTERNS = [
    "password", "123456", "qwerty", "abc123", "letmein", "welcome",
    "monkey", "dragon", "master", "admin", "login", "passw0rd",
    "iloveyou", "sunshine", "trustno1", "princess", "football",
    "shadow", "michael", "superman", "batman", "access",
]


def get_policy_value(key, default=""):
    with get_db() as db:
        row = db.execute(
            "SELECT policy_value FROM security_policies WHERE policy_key = ?", (key,)
        ).fetchone()
        return row["policy_value"] if row else default


def check_password_strength(password, username=""):
    score = 0
    feedback = []
    is_valid = True

    min_len = int(get_policy_value("min_password_length", "8"))
    require_upper = get_policy_value("require_uppercase", "true") == "true"
    require_lower = get_policy_value("require_lowercase", "true") == "true"
    require_number = get_policy_value("require_number", "true") == "true"
    require_special = get_policy_value("require_special", "true") == "true"

    if len(password) < min_len:
        feedback.append(f"Password must be at least {min_len} characters.")
        is_valid = False
    elif len(password) >= min_len + 4:
        score += 2
    elif len(password) >= min_len:
        score += 1

    if require_upper:
        if re.search(r"[A-Z]", password):
            score += 1
        else:
            feedback.append("Password must contain an uppercase letter.")
            is_valid = False

    if require_lower:
        if re.search(r"[a-z]", password):
            score += 1
        else:
            feedback.append("Password must contain a lowercase letter.")
            is_valid = False

    if require_number:
        if re.search(r"[0-9]", password):
            score += 1
        else:
            feedback.append("Password must contain a number.")
            is_valid = False

    if require_special:
        if re.search(r"[!@#$%^&*(),.?\":{}|<>_\-\[\]\\;'/`~]", password):
            score += 1
        else:
            feedback.append("Password must contain a special character.")
            is_valid = False

    if re.search(r"(.)\1{2,}", password):
        feedback.append("Password contains repeated characters.")
        is_valid = False

    lower_pass = password.lower()
    for pattern in COMMON_PATTERNS:
        if pattern in lower_pass:
            feedback.append("Password contains a common pattern.")
            is_valid = False
            break

    if username and username.lower() in lower_pass:
        feedback.append("Password should not contain the username.")
        is_valid = False

    if len(set(password)) < 4:
        feedback.append("Password needs more variety.")
        is_valid = False

    if score >= 5:
        strength = "strong"
    elif score >= 3:
        strength = "medium"
    else:
        strength = "weak"

    return {
        "valid": is_valid,
        "strength": strength,
        "score": score,
        "feedback": feedback,
    }


def generate_password(length=16):
    upper = string.ascii_uppercase
    lower = string.ascii_lowercase
    digits = string.digits
    special = "!@#$%^&*()_+-=[]{}|;:,.<>?"

    all_chars = upper + lower + digits + special

    password = [
        secrets.choice(upper),
        secrets.choice(lower),
        secrets.choice(digits),
        secrets.choice(special),
    ]

    password += [secrets.choice(all_chars) for _ in range(length - 4)]
    secrets.SystemRandom().shuffle(password)

    return "".join(password)
