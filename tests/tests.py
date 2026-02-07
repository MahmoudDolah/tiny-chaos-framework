#!/usr/bin/env python3
# tests/test_safety.py
import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# Add parent directory to path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from safety import SafetyChecker


class TestSafetyChecker:
    def setup_method(self):
        self.safety = SafetyChecker()

    def test_production_environment_detection(self):
        """Test that production environments are correctly identified"""
        prod_envs = ["production", "prod", "prd", "prod-east", "production-west"]
        non_prod_envs = ["test", "staging", "dev", "development", "uat"]

        for env in prod_envs:
            assert self.safety._is_production_environment(env) == True, (
                f"Failed to identify '{env}' as production"
            )

        for env in non_prod_envs:
            assert self.safety._is_production_environment(env) == False, (
                f"Incorrectly identified '{env}' as production"
            )

    def test_protected_service_detection(self):
        """Test that protected services are correctly identified"""
        protected = ["database-server", "auth-service", "payment-processor"]
        unprotected = ["web-server", "cache", "monitoring"]

        for service in protected:
            assert self.safety._is_protected_service(service) == True, (
                f"Failed to protect '{service}'"
            )

        for service in unprotected:
            assert self.safety._is_protected_service(service) == False, (
                f"Incorrectly protected '{service}'"
            )

    def test_safe_parameters(self):
        """Test that experiment parameters are validated correctly"""
        # Valid experiment
        valid_experiment = {
            "duration": 300,  # 5 minutes
            "intensity": 50,
        }

        # Invalid experiment (too long)
        invalid_experiment = {
            "duration": 7200,  # 2 hours
            "intensity": 50,
        }

        assert self.safety._has_safe_parameters(valid_experiment) == True
        assert self.safety._has_safe_parameters(invalid_experiment) == False

    def test_is_safe_to_run(self):
        """Test overall safety check"""
        # Safe experiment
        safe_experiment = {
            "target": {"environment": "test", "service": "web-server"},
            "duration": 300,
        }

        # Unsafe experiment (production)
        prod_experiment = {
            "target": {"environment": "production", "service": "web-server"},
            "duration": 300,
        }

        # Unsafe experiment (protected service)
        protected_service_experiment = {
            "target": {"environment": "test", "service": "database"},
            "duration": 300,
        }

        # Unsafe experiment (too long)
        long_experiment = {
            "target": {"environment": "test", "service": "web-server"},
            "duration": 7200,
        }

        assert self.safety.is_safe_to_run(safe_experiment) == True
        assert self.safety.is_safe_to_run(prod_experiment) == False
        assert self.safety.is_safe_to_run(protected_service_experiment) == False
        assert self.safety.is_safe_to_run(long_experiment) == False


# tests/test_experiments.py
import pytest
import sys
import os
from unittest.mock import patch, MagicMock, call

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments import ExperimentRunner


class TestExperimentRunner:
    def setup_method(self):
        self.runner = ExperimentRunner()

    @patch("subprocess.Popen")
    def test_start_cpu_stress(self, mock_popen):
        """Test that CPU stress experiments start correctly"""
        # Setup
        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        experiment = {"type": "cpu_stress", "duration": 60, "intensity": 80}

        # Execute
        self.runner._start_cpu_stress(experiment)

        # Assert
        mock_popen.assert_called_once()
        cmd = mock_popen.call_args[0][0]
        assert "stress-ng" in cmd
        assert "--cpu-load 80" in " ".join(cmd)
        assert len(self.runner.running_experiments) == 1

    @patch("subprocess.Popen")
    def test_start_memory_exhaust(self, mock_popen):
        """Test that memory exhaustion experiments start correctly"""
        # Setup
        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        experiment = {"type": "memory_exhaust", "duration": 60, "memory_mb": 2048}

        # Execute
        self.runner._start_memory_exhaust(experiment)

        # Assert
        mock_popen.assert_called_once()
        cmd = mock_popen.call_args[0][0]
        assert "stress-ng" in cmd
        assert "--vm-bytes 2048M" in " ".join(cmd)
        assert len(self.runner.running_experiments) == 1

    @patch("subprocess.run")
    def test_start_network_latency(self, mock_run):
        """Test that network latency experiments start correctly"""
        # Setup
        experiment = {
            "type": "network_latency",
            "duration": 60,
            "interface": "eth0",
            "latency_ms": 200,
        }

        # Execute
        self.runner._start_network_latency(experiment)

        # Assert
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "tc" in cmd
        assert "delay 200ms" in " ".join(cmd)
        assert len(self.runner.running_experiments) == 1

    @patch("subprocess.run")
    def test_stop_network_latency(self, mock_run):
        """Test that network latency experiments stop correctly"""
        # Setup
        self.runner.running_experiments = [("network_latency", "eth0")]

        # Execute
        results = self.runner.stop()

        # Assert
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "tc" in cmd
        assert "qdisc del" in " ".join(cmd)
        assert len(self.runner.running_experiments) == 0
        assert results["network_latency"] == "completed"

    def test_start_unknown_experiment(self):
        """Test handling of unknown experiment types"""
        experiment = {"type": "unknown_type", "duration": 60}

        with pytest.raises(ValueError) as excinfo:
            self.runner.start(experiment)

        assert "Unknown experiment type" in str(excinfo.value)

    @patch("experiments.ExperimentRunner._start_cpu_stress")
    @patch("experiments.ExperimentRunner._start_memory_exhaust")
    @patch("experiments.ExperimentRunner._start_network_latency")
    def test_start_routes_correctly(self, mock_network, mock_memory, mock_cpu):
        """Test that start() routes to the correct implementation"""
        # CPU experiment
        cpu_experiment = {"type": "cpu_stress", "duration": 60}
        self.runner.start(cpu_experiment)
        mock_cpu.assert_called_once_with(cpu_experiment)

        # Memory experiment
        memory_experiment = {"type": "memory_exhaust", "duration": 60}
        self.runner.start(memory_experiment)
        mock_memory.assert_called_once_with(memory_experiment)

        # Network experiment
        network_experiment = {"type": "network_latency", "duration": 60}
        self.runner.start(network_experiment)
        mock_network.assert_called_once_with(network_experiment)

    @patch("subprocess.Popen")
    def test_emergency_stop(self, mock_popen):
        """Test emergency stop functionality"""
        # Setup
        mock_process1 = MagicMock()
        mock_process2 = MagicMock()
        mock_popen.side_effect = [mock_process1, mock_process2]

        # Start two experiments
        self.runner._start_cpu_stress({"type": "cpu_stress", "duration": 60})
        self.runner._start_memory_exhaust({"type": "memory_exhaust", "duration": 60})

        # Mock process terminate to simulate process still running
        mock_process1.wait.side_effect = subprocess.TimeoutExpired("cmd", 5)

        # Execute emergency stop
        self.runner.emergency_stop()

        # Assert
        mock_process1.terminate.assert_called_once()
        mock_process1.kill.assert_called_once()
        mock_process2.terminate.assert_called_once()
        assert len(self.runner.running_experiments) == 0


# tests/test_monitoring.py
import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monitoring import MonitoringClient


class TestMonitoringClient:
    def setup_method(self):
        self.monitoring = MonitoringClient("http://test-prometheus:9090")

    @patch("requests.get")
    def test_get_current_metrics(self, mock_get):
        """Test fetching metrics from monitoring system"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "result": [
                    {
                        "metric": {"__name__": "http_requests_total"},
                        "value": [1620000000, "42.5"],
                    },
                    {
                        "metric": {"__name__": "latency_ms"},
                        "value": [1620000000, "120.3"],
                    },
                ]
            }
        }
        mock_get.return_value = mock_response

        # Execute
        metrics = self.monitoring._get_current_metrics("web-service")

        # Assert
        mock_get.assert_called_once()
        assert "http_requests_total" in metrics
        assert metrics["http_requests_total"] == 42.5
        assert "latency_ms" in metrics
        assert metrics["latency_ms"] == 120.3

    @patch("requests.get")
    def test_get_current_metrics_error(self, mock_get):
        """Test error handling when fetching metrics"""
        # Mock response
        mock_get.side_effect = Exception("Connection error")

        # Execute
        metrics = self.monitoring._get_current_metrics("web-service")

        # Assert
        assert metrics == {}

    @patch("monitoring.MonitoringClient._get_current_metrics")
    def test_capture_baseline(self, mock_get_metrics):
        """Test capturing baseline metrics"""
        # Setup
        mock_get_metrics.return_value = {
            "http_requests_total": 100.0,
            "latency_ms": 50.0,
        }

        # Execute
        baseline = self.monitoring.capture_baseline("web-service")

        # Assert
        mock_get_metrics.assert_called_once_with("web-service")
        assert baseline["http_requests_total"] == 100.0
        assert baseline["latency_ms"] == 50.0
        assert self.monitoring.baseline_metrics == baseline

    @patch("monitoring.MonitoringClient._get_current_metrics")
    def test_compare_with_baseline(self, mock_get_metrics):
        """Test comparing current metrics with baseline"""
        # Setup
        self.monitoring.baseline_metrics = {
            "http_requests_total": 100.0,
            "latency_ms": 50.0,
            "error_rate": 0.01,
        }

        mock_get_metrics.return_value = {
            "http_requests_total": 120.0,  # 20% increase
            "latency_ms": 75.0,  # 50% increase
            "error_rate": 0.03,  # 200% increase
        }

        # Execute
        comparison = self.monitoring.compare_with_baseline("web-service")

        # Assert
        mock_get_metrics.assert_called_once_with("web-service")

        assert comparison["http_requests_total"]["baseline"] == 100.0
        assert comparison["http_requests_total"]["current"] == 120.0
        assert comparison["http_requests_total"]["change_percent"] == 20.0

        assert comparison["latency_ms"]["baseline"] == 50.0
        assert comparison["latency_ms"]["current"] == 75.0
        assert comparison["latency_ms"]["change_percent"] == 50.0

        assert comparison["error_rate"]["baseline"] == 0.01
        assert comparison["error_rate"]["current"] == 0.03
        assert comparison["error_rate"]["change_percent"] == 200.0


# tests/test_reporting.py
import pytest
import sys
import os
import pandas as pd
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reporting import ExperimentReporter


class TestExperimentReporter:
    def setup_method(self):
        # Use a temp directory for test reports
        self.test_output_dir = "/tmp/chaos_test_reports"
        os.makedirs(self.test_output_dir, exist_ok=True)
        self.reporter = ExperimentReporter(output_dir=self.test_output_dir)

    def teardown_method(self):
        # Clean up test files
        import shutil

        shutil.rmtree(self.test_output_dir, ignore_errors=True)

    def test_metrics_to_dataframe(self):
        """Test conversion of metrics to DataFrame"""
        # Setup
        metrics_comparison = {
            "http_requests_total": {
                "baseline": 100.0,
                "current": 120.0,
                "change_percent": 20.0,
            },
            "latency_ms": {"baseline": 50.0, "current": 75.0, "change_percent": 50.0},
        }

        # Execute
        df = self.reporter._metrics_to_dataframe(metrics_comparison)

        # Assert
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "Metric" in df.columns
        assert "Baseline" in df.columns
        assert "During Experiment" in df.columns
        assert "Change (%)" in df.columns

        # Check values
        assert (
            df.loc[df["Metric"] == "http_requests_total", "Change (%)"].values[0]
            == 20.0
        )
        assert df.loc[df["Metric"] == "latency_ms", "Baseline"].values[0] == 50.0

    @patch("matplotlib.pyplot.savefig")
    def test_generate_plots(self, mock_savefig):
        """Test plot generation"""
        # Setup
        df = pd.DataFrame(
            [
                {
                    "Metric": "http_requests_total",
                    "Baseline": 100.0,
                    "During Experiment": 120.0,
                    "Change (%)": 20.0,
                },
                {
                    "Metric": "latency_ms",
                    "Baseline": 50.0,
                    "During Experiment": 75.0,
                    "Change (%)": 50.0,
                },
            ]
        )

        output_file = f"{self.test_output_dir}/test_plot.png"

        # Execute
        self.reporter._generate_plots(df, output_file, "Test Experiment")

        # Assert
        mock_savefig.assert_called_once_with(output_file)

    def test_generate_table_rows(self):
        """Test HTML table row generation"""
        # Setup
        df = pd.DataFrame(
            [
                {
                    "Metric": "http_requests_total",
                    "Baseline": 100.0,
                    "During Experiment": 120.0,
                    "Change (%)": 20.0,
                },
                {
                    "Metric": "latency_ms",
                    "Baseline": 50.0,
                    "During Experiment": 75.0,
                    "Change (%)": 50.0,
                },
            ]
        )

        # Execute
        html_rows = self.reporter._generate_table_rows(df)

        # Assert
        assert "http_requests_total" in html_rows
        assert "120.00" in html_rows
        assert "20.00%" in html_rows
        assert "latency_ms" in html_rows
        assert "50.00" in html_rows

    def test_generate_success_criteria_items(self):
        """Test HTML success criteria generation"""
        # Setup
        experiment = {
            "name": "Test Experiment",
            "success_criteria": [
                "System remains responsive",
                "Error rate stays below 5%",
            ],
        }

        # Execute
        html_items = self.reporter._generate_success_criteria_items(experiment)

        # Assert
        assert "System remains responsive" in html_items
        assert "Error rate stays below 5%" in html_items
        assert "Manual verification" in html_items

    @patch("reporting.ExperimentReporter._generate_plots")
    def test_generate_report(self, mock_generate_plots):
        """Test report generation"""
        # Setup
        experiment = {
            "name": "Network Latency Test",
            "type": "network_latency",
            "description": "Test network resilience",
            "duration": 300,
            "target": {"environment": "test", "service": "web-server"},
            "success_criteria": ["System remains responsive"],
        }

        metrics_comparison = {
            "http_requests_total": {
                "baseline": 100.0,
                "current": 120.0,
                "change_percent": 20.0,
            },
            "latency_ms": {"baseline": 50.0, "current": 75.0, "change_percent": 50.0},
        }

        # Execute
        report_file = self.reporter.generate_report(experiment, metrics_comparison)

        # Assert
        assert os.path.exists(report_file)

        # Check content
        with open(report_file, "r") as f:
            content = f.read()
            assert "Network Latency Test" in content
            assert "Test network resilience" in content
            assert "300 seconds" in content
            assert "System remains responsive" in content


# tests/test_integration.py
import pytest
import sys
import os
import tempfile
import yaml
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the modules - adjust paths as needed
import chaos_framework
from safety import SafetyChecker
from experiments import ExperimentRunner
from monitoring import MonitoringClient


class TestIntegration:
    def setup_method(self):
        # Create a temporary directory
        self.test_dir = tempfile.TemporaryDirectory()

        # Create a test experiment YAML
        self.experiment_data = {
            "name": "Test CPU Stress",
            "type": "cpu_stress",
            "description": "Integration test experiment",
            "target": {
                "environment": "test",
                "service": "web-server",
                "hosts": ["localhost"],
            },
            "duration": 2,  # Very short for testing
            "intensity": 50,
        }

        self.experiment_file = os.path.join(self.test_dir.name, "test_experiment.yaml")
        with open(self.experiment_file, "w") as f:
            yaml.dump(self.experiment_data, f)

    def teardown_method(self):
        # Clean up
        self.test_dir.cleanup()

    @patch("experiments.ExperimentRunner.start")
    @patch("experiments.ExperimentRunner.stop")
    @patch("time.sleep")
    def test_run_experiment_flow(self, mock_sleep, mock_stop, mock_start):
        """Test the full flow of running an experiment"""
        # Mock command line arguments
        test_args = ["chaos_framework.py", "run", "--experiment", self.experiment_file]

        # Patch sys.argv
        with patch("sys.argv", test_args):
            # Run the experiment
            result = chaos_framework.main()

            # Assert
            assert result == 0
            mock_start.assert_called_once()
            mock_sleep.assert_called_once_with(2)  # Duration from experiment
            mock_stop.assert_called_once()

    @patch.object(SafetyChecker, "is_safe_to_run", return_value=False)
    def test_safety_check_failure(self, mock_safety_check):
        """Test that safety checks block unsafe experiments"""
        # Mock command line arguments
        test_args = ["chaos_framework.py", "run", "--experiment", self.experiment_file]

        # Patch sys.argv
        with patch("sys.argv", test_args):
            # Run the experiment
            result = chaos_framework.main()

            # Assert
            assert result == 1  # Should return error code
            mock_safety_check.assert_called_once()

    def test_template_creation(self):
        """Test template creation functionality"""
        # Output file path
        output_file = os.path.join(self.test_dir.name, "new_template.yaml")

        # Mock command line arguments
        test_args = [
            "chaos_framework.py",
            "template",
            "--type",
            "memory",
            "--output",
            output_file,
        ]

        # Patch sys.argv
        with patch("sys.argv", test_args):
            # Run the experiment
            result = chaos_framework.main()

            # Assert
            assert result == 0
            assert os.path.exists(output_file)

            # Check template content
            with open(output_file, "r") as f:
                template = yaml.safe_load(f)
                assert template["type"] == "memory_exhaust"
                assert "success_criteria" in template
                assert "target" in template


# tests/test_cli.py
import pytest
import sys
import os
import yaml
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chaos_framework


class TestCLI:
    def test_version(self, capsys):
        """Test version flag"""
        with patch("sys.argv", ["chaos_framework.py", "--version"]):
            with pytest.raises(SystemExit) as e:
                chaos_framework.main()

            assert e.value.code == 0
            captured = capsys.readouterr()
            assert chaos_framework.VERSION in captured.out

    def test_help(self, capsys):
        """Test help option"""
        with patch("sys.argv", ["chaos_framework.py", "--help"]):
            with pytest.raises(SystemExit) as e:
                chaos_framework.main()

            assert e.value.code == 0
            captured = capsys.readouterr()
            assert "Chaos Engineering Mini-Framework" in captured.out

    def test_invalid_command(self):
        """Test invalid command"""
        with patch("sys.argv", ["chaos_framework.py", "invalid_command"]):
            result = chaos_framework.main()
            assert result == 0  # Should show help and exit

    def test_template_missing_args(self, capsys):
        """Test template command with missing arguments"""
        with patch("sys.argv", ["chaos_framework.py", "template"]):
            with pytest.raises(SystemExit):
                chaos_framework.main()

            captured = capsys.readouterr()
            assert "error" in captured.err.lower()

    def test_run_missing_args(self, capsys):
        """Test run command with missing arguments"""
        with patch("sys.argv", ["chaos_framework.py", "run"]):
            with pytest.raises(SystemExit):
                chaos_framework.main()

            captured = capsys.readouterr()
            assert "error" in captured.err.lower()

    @patch("chaos_framework.create_experiment_template")
    def test_template_command_routing(self, mock_create_template):
        """Test that template command routes to correct function"""
        mock_create_template.return_value = 0

        with patch(
            "sys.argv",
            [
                "chaos_framework.py",
                "template",
                "--type",
                "cpu",
                "--output",
                "test.yaml",
            ],
        ):
            result = chaos_framework.main()

            assert result == 0
            mock_create_template.assert_called_once()

    @patch("chaos_framework.run_experiment")
    def test_run_command_routing(self, mock_run_experiment):
        """Test that run command routes to correct function"""
        mock_run_experiment.return_value = 0

        with patch(
            "sys.argv", ["chaos_framework.py", "run", "--experiment", "test.yaml"]
        ):
            result = chaos_framework.main()

            assert result == 0
            mock_run_experiment.assert_called_once()


# tests/conftest.py
import pytest
import logging
import sys


# Configure logging for tests
def pytest_configure(config):
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )


# Add pytest fixtures if needed
@pytest.fixture
def sample_experiment():
    """Sample experiment configuration for tests"""
    return {
        "name": "Test CPU Stress",
        "type": "cpu_stress",
        "description": "Test experiment for unit tests",
        "target": {
            "environment": "test",
            "service": "web-server",
            "hosts": ["test-host-01"],
        },
        "duration": 30,
        "intensity": 50,
        "success_criteria": ["System remains responsive"],
    }


@pytest.fixture
def sample_metrics_comparison():
    """Sample metrics comparison for tests"""
    return {
        "http_requests_total": {
            "baseline": 100.0,
            "current": 120.0,
            "change_percent": 20.0,
        },
        "latency_ms": {"baseline": 50.0, "current": 75.0, "change_percent": 50.0},
        "error_rate": {"baseline": 0.01, "current": 0.03, "change_percent": 200.0},
    }


# Running the tests
# Execute with: python -m pytest tests/ -v
