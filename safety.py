# safety.py
import os
import yaml
import logging
from typing import Dict, List, Tuple, Optional
from environment_detector import EnvironmentDetector
from service_discovery import ServiceDiscovery

class SafetyViolation:
    """Represents a safety violation with details."""
    def __init__(self, violation_type: str, message: str, details: Dict = None):
        self.violation_type = violation_type
        self.message = message
        self.details = details or {}

class SafetyChecker:
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize SafetyChecker with configuration.

        Args:
            config_file: Path to safety configuration YAML file
        """
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_file)
        self.environment_detector = EnvironmentDetector(self.config)
        self.service_discovery = ServiceDiscovery(self.config)
        self._environment_cache = None

    def _load_config(self, config_file: Optional[str]) -> Dict:
        """Load safety configuration from YAML file."""
        if config_file is None:
            # Look for default config files in order
            for default_file in ["safety_config.yaml", "safety_config_default.yaml"]:
                if os.path.exists(default_file):
                    config_file = default_file
                    break

        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)
                self.logger.info(f"Loaded safety configuration from {config_file}")
                return config
            except Exception as e:
                self.logger.error(f"Failed to load safety config from {config_file}: {e}")

        # Return minimal default configuration
        self.logger.warning("Using minimal default safety configuration")
        return {
            "global": {"max_duration": 300, "auto_detect_environment": False},
            "environment_policies": {
                "default": {
                    "enabled": False,
                    "max_duration": 300,
                    "allowed_experiment_types": [],
                    "protected_services": ["*"],
                    "require_confirmation": True
                }
            }
        }

    def is_safe_to_run(self, experiment: Dict) -> Tuple[bool, List[SafetyViolation]]:
        """
        Check if experiment is safe to run.

        Args:
            experiment: Experiment configuration dictionary

        Returns:
            Tuple of (is_safe, list_of_violations)
        """
        violations = []

        # Get current environment
        environment_type, env_details = self._get_environment_info()

        # Get environment policy
        policy = self._get_environment_policy(environment_type)

        # Check if experiments are enabled in this environment
        if not policy.get("enabled", False):
            violations.append(SafetyViolation(
                "environment_disabled",
                f"Chaos experiments are disabled in {environment_type} environment",
                {"environment": environment_type, "policy": policy}
            ))

        # Check experiment type allowlist
        exp_type = experiment.get("type", "unknown")
        allowed_types = policy.get("allowed_experiment_types", [])
        if "*" not in allowed_types and exp_type not in allowed_types:
            violations.append(SafetyViolation(
                "experiment_type_forbidden",
                f"Experiment type '{exp_type}' not allowed in {environment_type} environment",
                {"experiment_type": exp_type, "allowed_types": allowed_types}
            ))

        # Check duration limits
        duration = experiment.get("duration", 0)
        max_duration = policy.get("max_duration", 0)
        if duration > max_duration:
            violations.append(SafetyViolation(
                "duration_exceeded",
                f"Experiment duration {duration}s exceeds maximum allowed {max_duration}s for {environment_type}",
                {"duration": duration, "max_duration": max_duration}
            ))

        # Check protected services
        target_service = experiment.get("target", {}).get("service", "unknown")
        if self._is_protected_service(target_service, policy):
            violations.append(SafetyViolation(
                "protected_service",
                f"Service '{target_service}' is protected and cannot be targeted for chaos experiments",
                {"service": target_service, "environment": environment_type}
            ))

        # Check experiment-specific parameters
        param_violations = self._check_experiment_parameters(experiment)
        violations.extend(param_violations)

        # Log safety decision
        if self.config.get("audit", {}).get("log_safety_decisions", False):
            self._log_safety_decision(experiment, environment_type, violations)

        return len(violations) == 0, violations

    def _get_environment_info(self) -> Tuple[str, Dict]:
        """Get current environment information with caching."""
        if self._environment_cache is None:
            if self.config.get("global", {}).get("auto_detect_environment", True):
                env_type, env_details = self.environment_detector.detect_environment()
            else:
                # Fallback to manual detection
                env_type = self._manual_environment_detection()
                env_details = {"detection_method": "manual"}

            self._environment_cache = (env_type, env_details)
            self.logger.info(f"Detected environment: {env_type}")

        return self._environment_cache

    def _manual_environment_detection(self) -> str:
        """Manual environment detection as fallback."""
        # Check environment variable first
        env = os.environ.get("ENVIRONMENT", os.environ.get("ENV", "")).lower()
        if env:
            return env

        # Check hostname patterns (legacy behavior)
        hostname = os.uname().nodename.lower()
        if any(prod_id in hostname for prod_id in ["prod", "production", "prd"]):
            return "production"

        return "default"

    def _get_environment_policy(self, environment_type: str) -> Dict:
        """Get safety policy for the given environment type."""
        policies = self.config.get("environment_policies", {})

        # Try exact match first
        if environment_type in policies:
            return policies[environment_type]

        # Fallback to default policy
        if "default" in policies:
            return policies["default"]

        # Ultimate fallback - very restrictive
        return {
            "enabled": False,
            "max_duration": 0,
            "allowed_experiment_types": [],
            "protected_services": ["*"],
            "require_confirmation": True
        }

    def _is_protected_service(self, service_name: str, policy: Dict) -> bool:
        """Check if a service is protected."""
        protected_services = policy.get("protected_services", [])

        # Check for wildcard protection
        if "*" in protected_services:
            return True

        # Check static list
        if any(ps in service_name.lower() for ps in protected_services):
            return True

        # Check service discovery
        if self.service_discovery.is_service_protected_by_discovery(service_name):
            return True

        return False

    def _check_experiment_parameters(self, experiment: Dict) -> List[SafetyViolation]:
        """Check experiment-specific parameter safety."""
        violations = []
        exp_type = experiment.get("type")
        exp_safety_config = self.config.get("experiment_safety", {})

        if exp_type in exp_safety_config:
            type_config = exp_safety_config[exp_type]

            if exp_type == "cpu_stress":
                intensity = experiment.get("intensity", 100)
                max_intensity = type_config.get("max_intensity", 100)
                if intensity > max_intensity:
                    violations.append(SafetyViolation(
                        "cpu_intensity_exceeded",
                        f"CPU intensity {intensity}% exceeds maximum {max_intensity}%",
                        {"intensity": intensity, "max_intensity": max_intensity}
                    ))

            elif exp_type == "memory_exhaust":
                memory_mb = experiment.get("memory_mb", 0)
                # Note: max_percentage and min_free would be used for system introspection
                # in a full implementation, but for now we do basic validation

                # Basic validation - check if memory amount seems reasonable
                if memory_mb > 32768:  # 32GB seems excessive for most tests
                    violations.append(SafetyViolation(
                        "memory_amount_excessive",
                        f"Memory allocation {memory_mb}MB seems excessive",
                        {"memory_mb": memory_mb}
                    ))

            elif exp_type == "network_latency":
                latency_ms = experiment.get("latency_ms", 0)
                max_latency = type_config.get("max_latency_ms", 5000)
                if latency_ms > max_latency:
                    violations.append(SafetyViolation(
                        "network_latency_exceeded",
                        f"Network latency {latency_ms}ms exceeds maximum {max_latency}ms",
                        {"latency_ms": latency_ms, "max_latency_ms": max_latency}
                    ))

                interface = experiment.get("interface", "")
                allowed_interfaces = type_config.get("allowed_interfaces", [])
                if allowed_interfaces and interface not in allowed_interfaces:
                    violations.append(SafetyViolation(
                        "interface_not_allowed",
                        f"Network interface '{interface}' not in allowed list",
                        {"interface": interface, "allowed_interfaces": allowed_interfaces}
                    ))

        return violations

    def _log_safety_decision(self, experiment: Dict, environment: str, violations: List[SafetyViolation]):
        """Log safety decision for audit purposes."""
        try:
            audit_config = self.config.get("audit", {})
            log_file = audit_config.get("log_file", "./logs/safety_audit.log")

            # Ensure log directory exists
            os.makedirs(os.path.dirname(log_file), exist_ok=True)

            import json
            from datetime import datetime

            audit_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "experiment_name": experiment.get("name", "unknown"),
                "experiment_type": experiment.get("type", "unknown"),
                "environment": environment,
                "safe": len(violations) == 0,
                "violations": [{
                    "type": v.violation_type,
                    "message": v.message,
                    "details": v.details
                } for v in violations]
            }

            if audit_config.get("include_experiment_details", False):
                audit_entry["experiment"] = experiment

            with open(log_file, "a") as f:
                f.write(json.dumps(audit_entry) + "\n")

        except Exception as e:
            self.logger.error(f"Failed to log safety decision: {e}")

    def get_environment_info(self) -> Dict:
        """Get detailed environment information for debugging."""
        environment_type, env_details = self._get_environment_info()
        policy = self._get_environment_policy(environment_type)

        return {
            "environment_type": environment_type,
            "environment_details": env_details,
            "policy": policy,
            "protected_services": list(self.service_discovery.get_protected_services())
        }

    def validate_config(self) -> List[str]:
        """Validate the loaded configuration and return any issues."""
        issues = []

        # Check required sections
        if "environment_policies" not in self.config:
            issues.append("Missing 'environment_policies' section")

        # Check that default policy exists
        policies = self.config.get("environment_policies", {})
        if "default" not in policies:
            issues.append("Missing 'default' environment policy")

        # Validate each policy
        for env_name, policy in policies.items():
            if "enabled" not in policy:
                issues.append(f"Missing 'enabled' field in {env_name} policy")

            if "max_duration" not in policy:
                issues.append(f"Missing 'max_duration' field in {env_name} policy")

        return issues
