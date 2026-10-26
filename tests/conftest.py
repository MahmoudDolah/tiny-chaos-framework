import copy
from pathlib import Path

import pytest
import requests

REPO_ROOT = Path(__file__).resolve().parent.parent

SHIPPED_CONFIGS = [
    REPO_ROOT / "safety_config_default.yaml",
    REPO_ROOT / "safety_config_dev.yaml",
    REPO_ROOT / "safety_config_enterprise.yaml",
]

ENV_VARS = ["ENVIRONMENT", "ENV", "STAGE"]

BASE_CONFIG = {
    "global": {"max_duration": 600, "auto_detect_environment": True},
    "environment_detection": {
        "classification_rules": [
            {
                "name": "production",
                "patterns": {
                    "hostname": ["prod-*", "*-prod"],
                    "environment_vars": ["ENVIRONMENT=production"],
                    "cloud_tags": ["environment=production"],
                },
            },
            {
                "name": "test",
                "patterns": {
                    "hostname": ["test-*"],
                    "environment_vars": ["ENVIRONMENT=test"],
                },
            },
        ]
    },
    "environment_policies": {
        "production": {
            "enabled": False,
            "max_duration": 0,
            "allowed_experiment_types": [],
            "protected_services": ["*"],
        },
        "test": {
            "enabled": True,
            "max_duration": 600,
            "allowed_experiment_types": ["cpu_stress", "network_latency"],
            "protected_services": ["payment", "auth"],
        },
        "default": {
            "enabled": False,
            "max_duration": 300,
            "allowed_experiment_types": ["cpu_stress"],
            "protected_services": ["*"],
        },
    },
    "experiment_safety": {
        "cpu_stress": {"max_intensity": 90},
        "network_latency": {"max_latency_ms": 1000, "allowed_interfaces": ["eth0"]},
    },
    "audit": {"log_safety_decisions": False},
}


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch, tmp_path):
    """Keep every test hermetic: no env-var leakage, no network, no repo writes."""
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.delenv("KUBERNETES_SERVICE_HOST", raising=False)

    # A neutral hostname that matches no classification rule
    monkeypatch.setattr("socket.gethostname", lambda: "workstation")

    def no_network(*args, **kwargs):
        raise requests.ConnectionError("network disabled in tests")

    monkeypatch.setattr(requests, "get", no_network)

    # Relative paths (audit logs, reports) land in a temp dir
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def config():
    """A fresh copy of the base config that tests can mutate freely."""
    return copy.deepcopy(BASE_CONFIG)


@pytest.fixture(params=SHIPPED_CONFIGS, ids=lambda p: p.stem)
def shipped_config_path(request):
    return str(request.param)


@pytest.fixture
def shipped_config(shipped_config_path):
    import yaml

    with open(shipped_config_path) as f:
        return yaml.safe_load(f)


@pytest.fixture
def write_config(tmp_path):
    """Write a config dict to a YAML file and return its path."""
    import yaml

    def _write(data, name="safety_config.yaml"):
        path = tmp_path / name
        path.write_text(yaml.safe_dump(data))
        return str(path)

    return _write


@pytest.fixture
def experiment():
    return {
        "name": "CPU Stress Test",
        "type": "cpu_stress",
        "description": "Simulate high CPU load",
        "target": {"environment": "test", "service": "web-server"},
        "duration": 300,
        "intensity": 80,
    }
