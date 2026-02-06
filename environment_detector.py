# environment_detector.py
import os
import socket
import requests
import logging
import re
from typing import Dict, Optional, Tuple

class EnvironmentDetector:
    """Detects the current environment type using various detection methods."""

    def __init__(self, config: Dict):
        """
        Initialize environment detector with configuration.

        Args:
            config: Configuration dictionary from safety config YAML
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

    def detect_environment(self) -> Tuple[str, Dict]:
        """
        Detect the current environment type and return details.

        Returns:
            Tuple of (environment_type, detection_details)
        """
        detection_details = {
            "hostname": socket.gethostname(),
            "environment_variables": {},
            "cloud_provider": None,
            "cloud_metadata": {},
            "matched_rules": []
        }

        # Try cloud provider detection first
        cloud_info = self._detect_cloud_provider()
        if cloud_info:
            detection_details["cloud_provider"] = cloud_info["provider"]
            detection_details["cloud_metadata"] = cloud_info.get("metadata", {})

        # Check environment classification rules
        environment_type = self._classify_environment(detection_details)

        return environment_type, detection_details

    def _detect_cloud_provider(self) -> Optional[Dict]:
        """Detect if running on a cloud provider and gather metadata."""
        if not self.config.get("environment_detection", {}).get("cloud_providers"):
            return None

        cloud_providers = self.config["environment_detection"]["cloud_providers"]

        for provider, config in cloud_providers.items():
            try:
                metadata_url = config["metadata_url"]
                timeout = config.get("timeout", 2)

                if provider == "aws":
                    return self._detect_aws(metadata_url, timeout)
                elif provider == "gcp":
                    return self._detect_gcp(metadata_url, timeout)
                elif provider == "azure":
                    return self._detect_azure(metadata_url, timeout)

            except Exception as e:
                self.logger.debug(f"Failed to detect {provider}: {e}")
                continue

        return None

    def _detect_aws(self, metadata_url: str, timeout: int) -> Optional[Dict]:
        """Detect AWS environment and gather metadata."""
        try:
            # Check if we can reach AWS metadata service
            response = requests.get(f"{metadata_url}instance-id", timeout=timeout)
            if response.status_code == 200:
                metadata = {"instance_id": response.text.strip()}

                # Try to get additional metadata
                try:
                    # Get instance type
                    resp = requests.get(f"{metadata_url}instance-type", timeout=timeout)
                    if resp.status_code == 200:
                        metadata["instance_type"] = resp.text.strip()

                    # Get tags (requires IAM permissions)
                    resp = requests.get(f"{metadata_url}tags/instance/", timeout=timeout)
                    if resp.status_code == 200:
                        tags = {}
                        for tag in resp.text.strip().split('\n'):
                            if tag:
                                tag_resp = requests.get(f"{metadata_url}tags/instance/{tag}", timeout=timeout)
                                if tag_resp.status_code == 200:
                                    tags[tag] = tag_resp.text.strip()
                        metadata["tags"] = tags

                except Exception:
                    pass  # Some metadata might not be accessible

                return {"provider": "aws", "metadata": metadata}

        except Exception as e:
            self.logger.debug(f"AWS detection failed: {e}")

        return None

    def _detect_gcp(self, metadata_url: str, timeout: int) -> Optional[Dict]:
        """Detect GCP environment and gather metadata."""
        try:
            headers = {"Metadata-Flavor": "Google"}
            response = requests.get(f"{metadata_url}instance/id",
                                  headers=headers, timeout=timeout)

            if response.status_code == 200:
                metadata = {"instance_id": response.text.strip()}

                # Try to get additional metadata
                try:
                    # Get instance name
                    resp = requests.get(f"{metadata_url}instance/name",
                                      headers=headers, timeout=timeout)
                    if resp.status_code == 200:
                        metadata["instance_name"] = resp.text.strip()

                    # Get project ID
                    resp = requests.get(f"{metadata_url}project/project-id",
                                      headers=headers, timeout=timeout)
                    if resp.status_code == 200:
                        metadata["project_id"] = resp.text.strip()

                except Exception:
                    pass

                return {"provider": "gcp", "metadata": metadata}

        except Exception as e:
            self.logger.debug(f"GCP detection failed: {e}")

        return None

    def _detect_azure(self, metadata_url: str, timeout: int) -> Optional[Dict]:
        """Detect Azure environment and gather metadata."""
        try:
            headers = {"Metadata": "true"}
            response = requests.get(f"{metadata_url}compute/vmId",
                                  headers=headers, timeout=timeout,
                                  params={"api-version": "2021-02-01", "format": "text"})

            if response.status_code == 200:
                metadata = {"vm_id": response.text.strip()}

                # Try to get additional metadata
                try:
                    # Get VM name
                    resp = requests.get(f"{metadata_url}compute/name",
                                      headers=headers, timeout=timeout,
                                      params={"api-version": "2021-02-01", "format": "text"})
                    if resp.status_code == 200:
                        metadata["vm_name"] = resp.text.strip()

                    # Get resource group
                    resp = requests.get(f"{metadata_url}compute/resourceGroupName",
                                      headers=headers, timeout=timeout,
                                      params={"api-version": "2021-02-01", "format": "text"})
                    if resp.status_code == 200:
                        metadata["resource_group"] = resp.text.strip()

                except Exception:
                    pass

                return {"provider": "azure", "metadata": metadata}

        except Exception as e:
            self.logger.debug(f"Azure detection failed: {e}")

        return None

    def _classify_environment(self, detection_details: Dict) -> str:
        """Classify environment based on detection rules."""
        if not self.config.get("environment_detection", {}).get("classification_rules"):
            return "default"

        classification_rules = self.config["environment_detection"]["classification_rules"]
        hostname = detection_details["hostname"]

        # Collect environment variables for matching
        env_vars = {}
        for rule in classification_rules:
            if "environment_vars" in rule.get("patterns", {}):
                for env_pattern in rule["patterns"]["environment_vars"]:
                    if "=" in env_pattern:
                        key, expected_value = env_pattern.split("=", 1)
                        actual_value = os.environ.get(key)
                        env_vars[key] = actual_value

        detection_details["environment_variables"] = env_vars

        # Check each rule in order
        for rule in classification_rules:
            rule_name = rule["name"]
            patterns = rule.get("patterns", {})
            matched = False

            # Check hostname patterns
            if "hostname" in patterns:
                for pattern in patterns["hostname"]:
                    if self._match_pattern(hostname, pattern):
                        detection_details["matched_rules"].append({
                            "rule": rule_name,
                            "type": "hostname",
                            "pattern": pattern,
                            "value": hostname
                        })
                        matched = True
                        break

            # Check environment variable patterns
            if not matched and "environment_vars" in patterns:
                for env_pattern in patterns["environment_vars"]:
                    if "=" in env_pattern:
                        key, expected_value = env_pattern.split("=", 1)
                        actual_value = os.environ.get(key)
                        if actual_value == expected_value:
                            detection_details["matched_rules"].append({
                                "rule": rule_name,
                                "type": "environment_var",
                                "pattern": env_pattern,
                                "value": f"{key}={actual_value}"
                            })
                            matched = True
                            break

            # Check cloud tag patterns
            if not matched and "cloud_tags" in patterns:
                cloud_metadata = detection_details.get("cloud_metadata", {})
                tags = cloud_metadata.get("tags", {})

                for tag_pattern in patterns["cloud_tags"]:
                    if "=" in tag_pattern:
                        key, expected_value = tag_pattern.split("=", 1)
                        if key in tags and tags[key] == expected_value:
                            detection_details["matched_rules"].append({
                                "rule": rule_name,
                                "type": "cloud_tag",
                                "pattern": tag_pattern,
                                "value": f"{key}={tags[key]}"
                            })
                            matched = True
                            break

            if matched:
                return rule_name

        # No rules matched, return default
        return "default"

    def _match_pattern(self, text: str, pattern: str) -> bool:
        """Match text against a glob-like pattern."""
        # Convert glob pattern to regex
        regex_pattern = pattern.replace("*", ".*").replace("?", ".")
        regex_pattern = f"^{regex_pattern}$"

        try:
            return bool(re.match(regex_pattern, text, re.IGNORECASE))
        except re.error:
            self.logger.warning(f"Invalid pattern: {pattern}")
            return False