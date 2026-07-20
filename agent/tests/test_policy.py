"""Tests de policy.py: no llaman a ninguna API, solo ejercitan fnmatch contra los
patrones reales de agent.config.yaml."""
import pytest

import policy


def test_read_denies_env_file():
    with pytest.raises(policy.PolicyError):
        policy.check_read(".env")


def test_read_denies_pem_anywhere():
    with pytest.raises(policy.PolicyError):
        policy.check_read("secrets/keys/server.pem")


def test_read_allows_normal_source_file():
    policy.check_read("app.py")  # no debe tirar


def test_write_denies_instance_folder():
    with pytest.raises(policy.PolicyError):
        policy.check_write("instance/database.db")


def test_write_denies_git_internals():
    with pytest.raises(policy.PolicyError):
        policy.check_write(".git/config")


def test_write_allows_normal_source_file():
    policy.check_write("app.py")  # no debe tirar


def test_command_denies_rm_rf():
    with pytest.raises(policy.PolicyError):
        policy.check_command("rm -rf instance/")


def test_command_denies_git_push():
    with pytest.raises(policy.PolicyError):
        policy.check_command("git push origin main")


def test_command_allows_pytest():
    policy.check_command("pytest -q")  # no debe tirar


def test_pip_install_requires_approval():
    assert policy.command_requires_approval("pip install flask") is True


def test_pytest_does_not_require_approval():
    assert policy.command_requires_approval("pytest -q") is False
