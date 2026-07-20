import fnmatch
import os

import yaml

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "..", "agent.config.yaml")

REQUIRED_KEYS = {"workspace", "permissions", "commands"}


class PolicyError(Exception):
    """El tool call viola una regla declarada en agent.config.yaml."""


def load_config():
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    missing = REQUIRED_KEYS - config.keys()
    if missing:
        raise ValueError(f"agent.config.yaml is missing required keys: {missing}")

    config.setdefault("permissions", {})
    config["permissions"].setdefault("read", {}).setdefault("deny", [])
    config["permissions"].setdefault("write", {}).setdefault("deny", [])
    config.setdefault("commands", {})
    config["commands"].setdefault("deny", [])
    config["commands"].setdefault("require_approval", [])
    return config


# Se valida una sola vez al importar el módulo, no en medio de una tool call.
CONFIG = load_config()


def _matches_any(path, patterns):
    normalized = (path or "").replace(os.sep, "/")
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in patterns)


def check_read(path):
    deny = CONFIG["permissions"]["read"]["deny"]
    if _matches_any(path, deny):
        raise PolicyError(f"Reading '{path}' is denied by agent.config.yaml (permissions.read.deny)")


def check_write(path):
    deny = CONFIG["permissions"]["write"]["deny"]
    if _matches_any(path, deny):
        raise PolicyError(f"Writing to '{path}' is denied by agent.config.yaml (permissions.write.deny)")


def check_command(command):
    command = command or ""
    for denied in CONFIG["commands"]["deny"]:
        if denied in command:
            raise PolicyError(f"Command containing '{denied}' is denied by agent.config.yaml (commands.deny)")


def command_requires_approval(command):
    command = command or ""
    return any(marker in command for marker in CONFIG["commands"]["require_approval"])
