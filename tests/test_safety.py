import json
from datetime import datetime

import pytest

from safety import SafetyChecker


def violation_types(violations):
    return {v.violation_type for v in violations}


@pytest.fixture
def checker(config, write_config):
    def _checker(cfg=None):
        return SafetyChecker(write_config(cfg if cfg is not None else config))

    return _checker


@pytest.fixture
def in_test_env(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")


class TestIsSafeToRun:
    def test_returns_bool_and_violations(self, checker, experiment, in_test_env):
        # Guards against the old chaos_controller bug: a tuple is always truthy
        result = checker().is_safe_to_run(experiment)
        assert isinstance(result, tuple)
        assert result == (True, [])

    def test_unknown_environment_uses_default_policy(self, checker, experiment):
        is_safe, violations = checker().is_safe_to_run(experiment)
        assert not is_safe
        assert "environment_disabled" in violation_types(violations)

    def test_production_is_blocked(self, checker, experiment, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        is_safe, violations = checker().is_safe_to_run(experiment)
        assert not is_safe
        assert {"environment_disabled", "protected_service"} <= violation_types(
            violations
        )

    def test_forbidden_experiment_type(self, checker, experiment, in_test_env):
        experiment["type"] = "memory_exhaust"
        is_safe, violations = checker().is_safe_to_run(experiment)
        assert not is_safe
        assert violation_types(violations) == {"experiment_type_forbidden"}

    def test_wildcard_allows_any_type(self, checker, config, experiment, in_test_env):
        config["environment_policies"]["test"]["allowed_experiment_types"] = ["*"]
        experiment["type"] = "memory_exhaust"
        is_safe, _ = checker(config).is_safe_to_run(experiment)
        assert is_safe

    def test_duration_exceeded(self, checker, experiment, in_test_env):
        experiment["duration"] = 601
        is_safe, violations = checker().is_safe_to_run(experiment)
        assert not is_safe
        assert violation_types(violations) == {"duration_exceeded"}

    def test_duration_at_limit_is_allowed(self, checker, experiment, in_test_env):
        experiment["duration"] = 600
        assert checker().is_safe_to_run(experiment)[0]

    @pytest.mark.parametrize("service", ["payment", "payment-api", "oauth-proxy"])
    def test_protected_service_substring(
        self, checker, experiment, in_test_env, service
    ):
        experiment["target"]["service"] = service
        is_safe, violations = checker().is_safe_to_run(experiment)
        assert not is_safe
        assert violation_types(violations) == {"protected_service"}

    def test_protected_service_case_insensitive(self, checker, experiment, in_test_env):
        experiment["target"]["service"] = "Payment-API"
        assert not checker().is_safe_to_run(experiment)[0]

    def test_service_discovery_protection(
        self, checker, experiment, in_test_env, monkeypatch
    ):
        safety = checker()
        monkeypatch.setattr(
            safety.service_discovery,
            "get_protected_services",
            lambda: {"web-server"},
        )
        is_safe, violations = safety.is_safe_to_run(experiment)
        assert not is_safe
        assert violation_types(violations) == {"protected_service"}


class TestExperimentParameters:
    def test_cpu_intensity_exceeded(self, checker, experiment, in_test_env):
        experiment["intensity"] = 95
        is_safe, violations = checker().is_safe_to_run(experiment)
        assert not is_safe
        assert violation_types(violations) == {"cpu_intensity_exceeded"}

    def test_network_latency_exceeded(self, checker, experiment, in_test_env):
        experiment.update(type="network_latency", latency_ms=2000, interface="eth0")
        _, violations = checker().is_safe_to_run(experiment)
        assert violation_types(violations) == {"network_latency_exceeded"}

    def test_network_interface_not_allowed(self, checker, experiment, in_test_env):
        experiment.update(type="network_latency", latency_ms=100, interface="wlan0")
        _, violations = checker().is_safe_to_run(experiment)
        assert violation_types(violations) == {"interface_not_allowed"}

    def test_excessive_memory(self, checker, config, experiment, in_test_env):
        config["environment_policies"]["test"]["allowed_experiment_types"] = ["*"]
        config["experiment_safety"]["memory_exhaust"] = {}
        experiment.update(type="memory_exhaust", memory_mb=65536)
        _, violations = checker(config).is_safe_to_run(experiment)
        assert violation_types(violations) == {"memory_amount_excessive"}


class TestConfigLoading:
    def test_missing_config_file_blocks_everything(self, experiment, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "test")
        # cwd is an empty temp dir, so no default config file is found
        safety = SafetyChecker()
        is_safe, violations = safety.is_safe_to_run(experiment)
        assert not is_safe
        assert {"environment_disabled", "protected_service"} <= violation_types(
            violations
        )

    def test_unknown_policy_falls_back_to_default(self, checker):
        safety = checker()
        assert (
            safety._get_environment_policy("nonexistent")
            == (safety.config["environment_policies"]["default"])
        )

    def test_no_policies_falls_back_to_restrictive(self, checker):
        policy = checker({"environment_policies": {}})._get_environment_policy("x")
        assert policy["enabled"] is False
        assert policy["protected_services"] == ["*"]

    def test_environment_is_cached(self, checker, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "test")
        safety = checker()
        assert safety._get_environment_info()[0] == "test"
        monkeypatch.setenv("ENVIRONMENT", "production")
        assert safety._get_environment_info()[0] == "test"


class TestValidateConfig:
    def test_shipped_configs_are_valid(self, shipped_config_path):
        assert SafetyChecker(shipped_config_path).validate_config() == []

    def test_shipped_configs_block_production(
        self, shipped_config_path, experiment, monkeypatch
    ):
        monkeypatch.setenv("ENVIRONMENT", "production")
        is_safe, _ = SafetyChecker(shipped_config_path).is_safe_to_run(experiment)
        assert not is_safe

    def test_missing_sections(self, checker):
        issues = checker({"global": {}}).validate_config()
        assert "Missing 'environment_policies' section" in issues
        assert "Missing 'default' environment policy" in issues

    def test_missing_policy_fields(self, checker):
        issues = checker({"environment_policies": {"default": {}}}).validate_config()
        assert "Missing 'enabled' field in default policy" in issues
        assert "Missing 'max_duration' field in default policy" in issues


class TestAuditLog:
    def test_writes_json_line(self, checker, config, experiment, tmp_path):
        log_file = tmp_path / "audit" / "safety.log"
        config["audit"] = {"log_safety_decisions": True, "log_file": str(log_file)}

        checker(config).is_safe_to_run(experiment)

        entry = json.loads(log_file.read_text().strip())
        assert entry["experiment_name"] == "CPU Stress Test"
        assert entry["safe"] is False
        assert entry["violations"]
        assert "experiment" not in entry
        assert datetime.fromisoformat(entry["timestamp"]).tzinfo is not None

    def test_includes_experiment_details_when_enabled(
        self, checker, config, experiment, tmp_path
    ):
        log_file = tmp_path / "safety.log"
        config["audit"] = {
            "log_safety_decisions": True,
            "log_file": str(log_file),
            "include_experiment_details": True,
        }

        checker(config).is_safe_to_run(experiment)

        entry = json.loads(log_file.read_text())
        assert entry["experiment"] == experiment
