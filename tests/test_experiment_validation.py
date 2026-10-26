import sys
from pathlib import Path

import pytest
import yaml

import chaos_framework
from experiments import validate_experiment

REPO_ROOT = Path(__file__).resolve().parent.parent


def errors_for(experiment):
    errors, _ = validate_experiment(experiment)
    return errors


def warnings_for(experiment):
    _, warnings = validate_experiment(experiment)
    return warnings


def assert_single_error(experiment, fragment):
    errors = errors_for(experiment)
    assert len(errors) == 1, errors
    assert fragment in errors[0]


def test_valid_experiment(experiment):
    assert validate_experiment(experiment) == ([], [])


def test_minimal_experiment():
    minimal = {
        "name": "Minimal",
        "type": "memory_exhaust",
        "duration": 60,
        "target": {"service": "web"},
    }
    assert validate_experiment(minimal) == ([], [])


def test_shipped_example_is_valid():
    with open(REPO_ROOT / "test_cpu_experiment.yaml") as f:
        assert validate_experiment(yaml.safe_load(f)) == ([], [])


@pytest.mark.parametrize("exp_type", ["cpu", "memory", "network"])
def test_generated_templates_are_valid(tmp_path, monkeypatch, exp_type):
    output = tmp_path / f"{exp_type}.yaml"
    monkeypatch.setattr(
        sys,
        "argv",
        ["tiny-chaos", "template", "--type", exp_type, "--output", str(output)],
    )
    assert chaos_framework.main() == 0
    assert validate_experiment(yaml.safe_load(output.read_text())) == ([], [])


@pytest.mark.parametrize("document", [None, [], "just a string", 42])
def test_non_mapping_document(document):
    assert errors_for(document) == [
        "Experiment file must contain a YAML mapping of fields"
    ]


class TestRequiredFields:
    @pytest.mark.parametrize("field", ["name", "type", "duration", "target"])
    def test_missing(self, experiment, field):
        del experiment[field]
        errors = errors_for(experiment)
        assert any(f"'{field}'" in e for e in errors), errors

    def test_missing_target_service(self, experiment):
        del experiment["target"]["service"]
        assert_single_error(experiment, "'target.service'")

    @pytest.mark.parametrize("name", ["", "   ", 123])
    def test_bad_name(self, experiment, name):
        experiment["name"] = name
        assert_single_error(experiment, "'name'")

    def test_unknown_type(self, experiment):
        experiment["type"] = "disk_fill"
        assert_single_error(experiment, "'disk_fill'")

    @pytest.mark.parametrize("duration", [0, -5, "300", 30.5, True, None])
    def test_bad_duration(self, experiment, duration):
        experiment["duration"] = duration
        assert_single_error(experiment, "'duration'")

    def test_target_not_a_mapping(self, experiment):
        experiment["target"] = "web-server"
        assert_single_error(experiment, "'target'")


class TestOptionalFields:
    def test_bad_description(self, experiment):
        experiment["description"] = ["not", "a", "string"]
        assert_single_error(experiment, "'description'")

    @pytest.mark.parametrize("criteria", ["one string", [1, 2]])
    def test_bad_success_criteria(self, experiment, criteria):
        experiment["success_criteria"] = criteria
        assert_single_error(experiment, "'success_criteria'")

    @pytest.mark.parametrize("hosts", ["host-1", ["host-1", ""], [None]])
    def test_bad_hosts(self, experiment, hosts):
        experiment["target"]["hosts"] = hosts
        assert_single_error(experiment, "'target.hosts'")

    def test_empty_target_environment(self, experiment):
        experiment["target"]["environment"] = ""
        assert_single_error(experiment, "'target.environment'")


class TestTypeParameters:
    @pytest.mark.parametrize("intensity", [1, 50, 100])
    def test_valid_intensity(self, experiment, intensity):
        experiment["intensity"] = intensity
        assert errors_for(experiment) == []

    @pytest.mark.parametrize("intensity", [0, 101, "80", 80.5])
    def test_bad_intensity(self, experiment, intensity):
        experiment["intensity"] = intensity
        assert_single_error(experiment, "'intensity' must be an integer (1-100)")

    @pytest.mark.parametrize("memory_mb", [0, -1, "1G"])
    def test_bad_memory(self, experiment, memory_mb):
        experiment.update(type="memory_exhaust", memory_mb=memory_mb)
        del experiment["intensity"]
        assert_single_error(experiment, "'memory_mb' must be an integer (>= 1)")

    @pytest.mark.parametrize("latency_ms", [0, "100ms"])
    def test_bad_latency(self, experiment, latency_ms):
        experiment.update(type="network_latency", latency_ms=latency_ms)
        del experiment["intensity"]
        assert_single_error(experiment, "'latency_ms'")

    @pytest.mark.parametrize("interface", ["eth0", "ens3", "eth0.100", "br-lan"])
    def test_valid_interface(self, experiment, interface):
        experiment.update(type="network_latency", interface=interface)
        del experiment["intensity"]
        assert errors_for(experiment) == []

    @pytest.mark.parametrize(
        "interface",
        ["", "eth0 root", "eth0;reboot", 0],
    )
    def test_bad_interface(self, experiment, interface):
        # Interface names become a tc argument, so whitespace must be rejected
        experiment.update(type="network_latency", interface=interface)
        del experiment["intensity"]
        assert_single_error(experiment, "'interface'")


class TestWarnings:
    def test_misspelled_field(self, experiment):
        experiment["durration"] = 300
        assert errors_for(experiment) == []
        assert warnings_for(experiment) == ["Unknown field 'durration' will be ignored"]

    def test_unknown_target_field(self, experiment):
        experiment["target"]["servce"] = "web"
        assert warnings_for(experiment) == [
            "Unknown target field 'servce' will be ignored"
        ]

    def test_parameter_for_other_type(self, experiment):
        experiment["latency_ms"] = 100
        assert warnings_for(experiment) == [
            "'latency_ms' does not apply to cpu_stress and will be ignored"
        ]

    def test_no_parameter_warning_when_type_invalid(self, experiment):
        experiment["type"] = "bogus"
        assert warnings_for(experiment) == []


class TestRunCommand:
    @pytest.fixture
    def run(self, monkeypatch, tmp_path, write_config, config):
        monkeypatch.setenv("ENVIRONMENT", "test")
        config_path = write_config(config)

        class ExplodingRunner:
            def __init__(self):
                raise AssertionError("runner must not be created for invalid input")

        monkeypatch.setattr(chaos_framework, "ExperimentRunner", ExplodingRunner)

        def _run(content, *extra_args):
            path = tmp_path / "experiment.yaml"
            path.write_text(content)
            monkeypatch.setattr(
                sys,
                "argv",
                [
                    "tiny-chaos",
                    "run",
                    "--experiment",
                    str(path),
                    "--safety-config",
                    config_path,
                    *extra_args,
                ],
            )
            return chaos_framework.main()

        return _run

    def test_empty_file_fails_cleanly(self, run):
        assert run("") == 1

    def test_invalid_fields_fail_cleanly(self, run, caplog):
        assert run("name: Broken\ntype: cpu_stress\nduration: '300'\n") == 1
        messages = caplog.text
        assert "'duration'" in messages
        assert "'target'" in messages

    def test_invalid_yaml_syntax_fails_cleanly(self, run):
        assert run("name: [unclosed\n") == 1

    def test_warnings_do_not_block(self, run, experiment, caplog):
        experiment["durration"] = 5
        assert run(yaml.safe_dump(experiment), "--dry-run") == 0
        assert "Unknown field 'durration' will be ignored" in caplog.text
