# experiments.py
import re
import subprocess
import logging

# Parameters each experiment type accepts, with the range of valid values
# (inclusive; None means unbounded)
EXPERIMENT_PARAMETERS = {
    "cpu_stress": {"intensity": (1, 100)},
    "memory_exhaust": {"memory_mb": (1, None)},
    "network_latency": {"latency_ms": (1, None), "interface": None},
}

COMMON_FIELDS = {
    "name",
    "type",
    "description",
    "target",
    "duration",
    "success_criteria",
}
TARGET_FIELDS = {"environment", "service", "hosts"}
ALL_PARAMETERS = {p for params in EXPERIMENT_PARAMETERS.values() for p in params}

# Interface names are passed as a tc argument, so keep them to safe characters
INTERFACE_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]+$")


def _is_int(value):
    # bool is a subclass of int, but "duration: true" is never intended
    return isinstance(value, int) and not isinstance(value, bool)


def _is_non_empty_str(value):
    return isinstance(value, str) and value.strip() != ""


def validate_experiment(experiment):
    """
    Check an experiment definition's structure before anything acts on it.

    Args:
        experiment: Experiment definition as loaded from YAML

    Returns:
        Tuple of (errors, warnings). Errors make the experiment unusable;
        warnings flag likely mistakes such as misspelled keys.
    """
    if not isinstance(experiment, dict):
        return ["Experiment file must contain a YAML mapping of fields"], []

    errors = []
    warnings = []

    if not _is_non_empty_str(experiment.get("name")):
        errors.append("'name' is required and must be a non-empty string")

    exp_type = experiment.get("type")
    if exp_type not in EXPERIMENT_PARAMETERS:
        errors.append(
            f"'type' must be one of {sorted(EXPERIMENT_PARAMETERS)}, got {exp_type!r}"
        )

    duration = experiment.get("duration")
    if not _is_int(duration) or duration <= 0:
        errors.append(
            f"'duration' is required and must be a positive integer (seconds), got {duration!r}"
        )

    if "description" in experiment and not isinstance(experiment["description"], str):
        errors.append("'description' must be a string")

    criteria = experiment.get("success_criteria")
    if criteria is not None and (
        not isinstance(criteria, list) or not all(isinstance(c, str) for c in criteria)
    ):
        errors.append("'success_criteria' must be a list of strings")

    target = experiment.get("target")
    if not isinstance(target, dict):
        errors.append("'target' is required and must be a mapping")
    else:
        if not _is_non_empty_str(target.get("service")):
            errors.append("'target.service' is required and must be a non-empty string")
        if "environment" in target and not _is_non_empty_str(target["environment"]):
            errors.append("'target.environment' must be a non-empty string")
        hosts = target.get("hosts")
        if hosts is not None and (
            not isinstance(hosts, list) or not all(_is_non_empty_str(h) for h in hosts)
        ):
            errors.append("'target.hosts' must be a list of non-empty strings")
        for key in sorted(set(target) - TARGET_FIELDS):
            warnings.append(f"Unknown target field '{key}' will be ignored")

    type_params = EXPERIMENT_PARAMETERS.get(exp_type, {})
    for param, bounds in type_params.items():
        if param not in experiment:
            continue
        value = experiment[param]
        if param == "interface":
            if not isinstance(value, str) or not INTERFACE_PATTERN.match(value):
                errors.append(
                    f"'interface' must be a network interface name, got {value!r}"
                )
            continue
        low, high = bounds
        if not _is_int(value) or value < low or (high is not None and value > high):
            allowed = f"{low}-{high}" if high is not None else f">= {low}"
            errors.append(f"'{param}' must be an integer ({allowed}), got {value!r}")

    for key in sorted(set(experiment) - COMMON_FIELDS):
        if key in ALL_PARAMETERS:
            # Only meaningful if the type is valid; otherwise the type error says enough
            if exp_type in EXPERIMENT_PARAMETERS and key not in type_params:
                warnings.append(
                    f"'{key}' does not apply to {exp_type} and will be ignored"
                )
        else:
            warnings.append(f"Unknown field '{key}' will be ignored")

    return errors, warnings


class ExperimentRunner:
    def __init__(self):
        self.running_experiments = []

    def start(self, experiment):
        experiment_type = experiment["type"]

        if experiment_type == "cpu_stress":
            self._start_cpu_stress(experiment)
        elif experiment_type == "memory_exhaust":
            self._start_memory_exhaust(experiment)
        elif experiment_type == "network_latency":
            self._start_network_latency(experiment)
        else:
            raise ValueError(f"Unknown experiment type: {experiment_type}")

        logging.info(f"Started {experiment_type} experiment")

    def _start_cpu_stress(self, experiment):
        # Example using stress-ng for CPU load
        intensity = experiment.get("intensity", 80)
        cmd = f"stress-ng --cpu 1 --cpu-load {intensity} --timeout {experiment['duration']}s"
        process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
        self.running_experiments.append(("cpu_stress", process))

    def _start_memory_exhaust(self, experiment):
        # Memory exhaustion experiment
        memory_mb = experiment.get("memory_mb", 1024)
        cmd = f"stress-ng --vm 1 --vm-bytes {memory_mb}M --timeout {experiment['duration']}s"
        process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
        self.running_experiments.append(("memory_exhaust", process))

    def _start_network_latency(self, experiment):
        # Network latency using tc
        interface = experiment.get("interface", "eth0")
        latency_ms = experiment.get("latency_ms", 100)
        cmd = f"tc qdisc add dev {interface} root netem delay {latency_ms}ms"
        subprocess.run(cmd.split(), check=True)
        self.running_experiments.append(("network_latency", interface))

    def stop(self):
        results = {}

        for exp_type, process_or_resource in self.running_experiments:
            if exp_type == "network_latency":
                # Remove network latency
                interface = process_or_resource
                cmd = f"tc qdisc del dev {interface} root"
                subprocess.run(cmd.split(), check=True)
                results[exp_type] = "completed"
            else:
                # Kill process
                process = process_or_resource
                process.terminate()
                try:
                    process.wait(timeout=5)
                    results[exp_type] = "completed"
                except subprocess.TimeoutExpired:
                    process.kill()
                    results[exp_type] = "force_killed"

        self.running_experiments = []
        return results

    def emergency_stop(self):
        logging.warning("Emergency stop initiated!")
        self.stop()
