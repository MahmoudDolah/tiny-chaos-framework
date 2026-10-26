# monitoring.py
import requests
import logging


class MonitoringClient:
    def __init__(self, monitoring_url, api_key=None, timeout=10):
        self.monitoring_url = monitoring_url
        self.api_key = api_key
        self.timeout = timeout
        self.baseline_metrics = {}

    def capture_baseline(self, target_service):
        """Capture baseline metrics before experiment"""
        self.baseline_metrics = self._get_current_metrics(target_service)
        return self.baseline_metrics

    def compare_with_baseline(self, target_service):
        """Compare current metrics with baseline"""
        current = self._get_current_metrics(target_service)
        comparison = {}

        for metric, value in current.items():
            if metric in self.baseline_metrics:
                baseline = self.baseline_metrics[metric]
                # Percent change is undefined against a zero baseline
                change = ((value - baseline) / baseline * 100) if baseline else None
                comparison[metric] = {
                    "baseline": baseline,
                    "current": value,
                    "change_percent": change,
                }

        return comparison

    def _get_current_metrics(self, target_service):
        """Get current metrics from monitoring system"""
        # This would integrate with your actual monitoring system
        # Example with Prometheus API
        try:
            response = requests.get(
                f"{self.monitoring_url}/api/v1/query",
                params={
                    "query": f'rate(http_requests_total{{service="{target_service}"}}[5m])'
                },
                headers={"Authorization": f"Bearer {self.api_key}"}
                if self.api_key
                else {},
                timeout=self.timeout,
            )

            if response.status_code == 200:
                data = response.json()
                # Process metrics data
                metrics = self._process_prometheus_response(data)
                return metrics
            else:
                logging.error(f"Failed to get metrics: {response.status_code}")
                return {}

        except Exception as e:
            logging.error(f"Error getting metrics: {e}")
            return {}

    def _process_prometheus_response(self, data):
        """Process Prometheus response into usable metrics"""
        metrics = {}

        if "data" in data and "result" in data["data"]:
            for result in data["data"]["result"]:
                metric_name = result["metric"].get("__name__", "unknown")
                if "value" in result:
                    # Prometheus format [timestamp, value]
                    metrics[metric_name] = float(result["value"][1])

        return metrics
