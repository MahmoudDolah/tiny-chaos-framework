# service_discovery.py
import requests
import logging
from typing import Dict, List, Set

class ServiceDiscovery:
    """Service discovery integration for identifying protected services."""

    def __init__(self, config: Dict):
        """
        Initialize service discovery with configuration.

        Args:
            config: Configuration dictionary from safety config YAML
        """
        self.config = config.get("service_discovery", {})
        self.logger = logging.getLogger(__name__)

    def get_protected_services(self) -> Set[str]:
        """
        Get list of protected services from all enabled service discovery systems.

        Returns:
            Set of protected service names
        """
        protected_services = set()

        # Add services from Kubernetes if enabled
        if self.config.get("kubernetes", {}).get("enabled", False):
            k8s_services = self._get_kubernetes_protected_services()
            protected_services.update(k8s_services)

        # Add services from Consul if enabled
        if self.config.get("consul", {}).get("enabled", False):
            consul_services = self._get_consul_protected_services()
            protected_services.update(consul_services)

        return protected_services

    def _get_kubernetes_protected_services(self) -> List[str]:
        """Get protected services from Kubernetes service discovery."""
        protected_services = []

        try:
            # In a real implementation, this would use the Kubernetes API
            # and check namespace_patterns from config
            # For now, we'll simulate by checking if we're in a K8s environment
            if self._is_kubernetes_environment():
                # These would be discovered via K8s API calls
                protected_services.extend([
                    "kube-dns",
                    "kube-proxy",
                    "kubernetes-dashboard",
                    "monitoring-prometheus",
                    "monitoring-grafana"
                ])

                self.logger.debug(f"Kubernetes protected services: {protected_services}")

        except Exception as e:
            self.logger.warning(f"Failed to get Kubernetes protected services: {e}")

        return protected_services

    def _get_consul_protected_services(self) -> List[str]:
        """Get protected services from Consul service discovery."""
        protected_services = []

        try:
            consul_config = self.config.get("consul", {})
            consul_url = consul_config.get("url", "http://localhost:8500")
            protected_tags = consul_config.get("protected_service_tags", [])

            # Query Consul catalog for services
            response = requests.get(f"{consul_url}/v1/catalog/services", timeout=5)

            if response.status_code == 200:
                services = response.json()

                for service_name, tags in services.items():
                    # Check if service has any protected tags
                    if any(tag in protected_tags for tag in tags):
                        protected_services.append(service_name)

                self.logger.debug(f"Consul protected services: {protected_services}")

        except Exception as e:
            self.logger.warning(f"Failed to get Consul protected services: {e}")

        return protected_services

    def _is_kubernetes_environment(self) -> bool:
        """Check if we're running in a Kubernetes environment."""
        import os
        return (
            os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount") or
            os.environ.get("KUBERNETES_SERVICE_HOST") is not None
        )

    def is_service_protected_by_discovery(self, service_name: str) -> bool:
        """
        Check if a service is protected according to service discovery.

        Args:
            service_name: Name of the service to check

        Returns:
            True if service is protected by service discovery
        """
        protected_services = self.get_protected_services()
        return service_name in protected_services