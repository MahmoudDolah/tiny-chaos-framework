import pytest

from environment_detector import EnvironmentDetector


def classify(config, hostname="workstation", tags=None):
    detector = EnvironmentDetector(config)
    details = {
        "hostname": hostname,
        "environment_variables": {},
        "cloud_metadata": {"tags": tags or {}},
        "matched_rules": [],
    }
    return detector._classify_environment(details), details


class TestMatchPattern:
    @pytest.mark.parametrize(
        "text, pattern",
        [
            ("prod-web-01", "prod-*"),
            ("web-prod", "*-prod"),
            ("my-prd-box", "*prd*"),
            ("PROD-WEB-01", "prod-*"),
            ("test-1", "test-?"),
        ],
    )
    def test_matches(self, text, pattern):
        assert EnvironmentDetector({})._match_pattern(text, pattern)

    @pytest.mark.parametrize(
        "text, pattern",
        [
            ("web-prod-01", "prod-*"),
            ("production", "*-prod"),
            ("test-12", "test-?"),
            # Glob dots are literal, not regex wildcards
            ("dbxprod", "db.prod"),
        ],
    )
    def test_does_not_match(self, text, pattern):
        assert not EnvironmentDetector({})._match_pattern(text, pattern)


class TestClassifyEnvironment:
    def test_no_rules_returns_default(self):
        env, _ = classify({})
        assert env == "default"

    def test_unmatched_returns_default(self, config):
        env, details = classify(config)
        assert env == "default"
        assert details["matched_rules"] == []

    def test_hostname_match(self, config):
        env, details = classify(config, hostname="prod-api-01")
        assert env == "production"
        assert details["matched_rules"][0]["type"] == "hostname"

    @pytest.mark.parametrize("value", ["production", "Production", "PRODUCTION"])
    def test_env_var_match_is_case_insensitive(self, config, monkeypatch, value):
        monkeypatch.setenv("ENVIRONMENT", value)
        env, details = classify(config)
        assert env == "production"
        assert details["matched_rules"][0]["type"] == "environment_var"

    def test_cloud_tag_match(self, config):
        env, details = classify(config, tags={"environment": "production"})
        assert env == "production"
        assert details["matched_rules"][0]["type"] == "cloud_tag"

    def test_rules_checked_in_order(self, config, monkeypatch):
        # A test-looking host with a production env var must classify as production
        monkeypatch.setenv("ENVIRONMENT", "production")
        env, _ = classify(config, hostname="test-box")
        assert env == "production"


class TestShippedConfigDetection:
    """The shipped configs must recognize every common way of saying 'production'."""

    @pytest.mark.parametrize(
        "var, value",
        [
            ("ENVIRONMENT", "prod"),
            ("ENVIRONMENT", "production"),
            ("STAGE", "prod"),
            ("STAGE", "production"),
            ("ENV", "prod"),
            ("ENV", "prd"),
            ("ENV", "production"),
        ],
    )
    def test_production_env_vars(self, shipped_config, monkeypatch, var, value):
        monkeypatch.setenv(var, value)
        env, _ = classify(shipped_config)
        assert env == "production"


class TestCloudProviderDetection:
    def test_no_cloud_config_returns_none(self):
        assert EnvironmentDetector({})._detect_cloud_provider() is None

    def test_falls_through_to_next_provider(self):
        detector = EnvironmentDetector(
            {
                "environment_detection": {
                    "cloud_providers": {
                        "aws": {"metadata_url": "http://aws/"},
                        "gcp": {"metadata_url": "http://gcp/"},
                        "azure": {"metadata_url": "http://azure/"},
                    }
                }
            }
        )
        detector._detect_aws = lambda url, timeout: None
        detector._detect_gcp = lambda url, timeout: None
        detector._detect_azure = lambda url, timeout: {"provider": "azure"}

        assert detector._detect_cloud_provider() == {"provider": "azure"}

    def test_unreachable_metadata_returns_none(self, config):
        config["environment_detection"]["cloud_providers"] = {
            "aws": {"metadata_url": "http://169.254.169.254/latest/meta-data/"}
        }
        # requests.get raises in tests, simulating an off-cloud machine
        env, details = EnvironmentDetector(config).detect_environment()
        assert details["cloud_provider"] is None
        assert env == "default"
