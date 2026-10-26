import sys

import pytest
import yaml

import chaos_framework


class FakeRunner:
    """Stands in for ExperimentRunner so tests never run stress-ng or tc."""

    instances = []

    def __init__(self):
        self.started = False
        FakeRunner.instances.append(self)

    def start(self, experiment):
        self.started = True

    def stop(self):
        return {"fake": "completed"}

    def emergency_stop(self):
        pass


class FakeStdin:
    def __init__(self, tty):
        self._tty = tty

    def isatty(self):
        return self._tty


@pytest.fixture
def run_cli(monkeypatch, tmp_path, config, experiment):
    FakeRunner.instances = []
    monkeypatch.setattr(chaos_framework, "ExperimentRunner", FakeRunner)
    monkeypatch.setattr("time.sleep", lambda seconds: None)
    monkeypatch.setenv("ENVIRONMENT", "test")

    def _run(*extra_args, tty=True, answer=None, cfg=None):
        config_path = tmp_path / "safety.yaml"
        config_path.write_text(yaml.safe_dump(cfg if cfg is not None else config))
        experiment_path = tmp_path / "experiment.yaml"
        experiment_path.write_text(yaml.safe_dump(experiment))

        monkeypatch.setattr(sys, "stdin", FakeStdin(tty))

        def fake_input(prompt=""):
            if answer is None:
                raise AssertionError("unexpected confirmation prompt")
            if answer is EOFError:
                raise EOFError
            return answer

        monkeypatch.setattr("builtins.input", fake_input)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "tiny-chaos",
                "run",
                "--experiment",
                str(experiment_path),
                "--safety-config",
                str(config_path),
                *extra_args,
            ],
        )
        return chaos_framework.main()

    return _run


def started():
    return any(r.started for r in FakeRunner.instances)


@pytest.fixture
def confirming_config(config):
    config["environment_policies"]["test"]["require_confirmation"] = True
    return config


def test_runs_without_prompt_when_not_required(run_cli):
    assert run_cli() == 0
    assert started()


@pytest.mark.parametrize("answer", ["yes", "YES", "  yes  "])
def test_confirmed_runs(run_cli, confirming_config, answer):
    assert run_cli(cfg=confirming_config, answer=answer) == 0
    assert started()


@pytest.mark.parametrize("answer", ["no", "y", "", EOFError])
def test_declined_aborts(run_cli, confirming_config, answer):
    assert run_cli(cfg=confirming_config, answer=answer) == 1
    assert not started()


def test_non_interactive_without_yes_aborts(run_cli, confirming_config):
    assert run_cli(cfg=confirming_config, tty=False) == 1
    assert not started()


@pytest.mark.parametrize("flag", ["--yes", "-y"])
def test_yes_flag_skips_prompt(run_cli, confirming_config, flag):
    assert run_cli(flag, cfg=confirming_config, tty=False) == 0
    assert started()


def test_global_confirmation_applies(run_cli, config):
    config["global"]["require_confirmation"] = True
    assert run_cli(cfg=config, tty=False) == 1
    assert not started()


def test_dry_run_never_prompts(run_cli, confirming_config):
    assert run_cli("--dry-run", cfg=confirming_config) == 0
    assert not FakeRunner.instances


def test_global_max_duration_blocks_run(run_cli, config):
    config["global"]["max_duration"] = 100
    assert run_cli(cfg=config) == 1
    assert not FakeRunner.instances
