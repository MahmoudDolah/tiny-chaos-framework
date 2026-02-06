# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the Tiny Chaos Framework - a lightweight Python framework for running chaos engineering experiments. The project aims to provide a simple way to test system resilience through controlled failure injection.

## Commands

### Development Commands
- **Run the main framework**: `uv run python chaos_framework.py --help`
- **Create experiment template**: `uv run python chaos_framework.py template --type cpu --output cpu_experiment.yaml`
- **Run experiment**: `uv run python chaos_framework.py run --experiment cpu_experiment.yaml --dry-run`
- **Check environment info**: `uv run python chaos_framework.py env-info`
- **Validate safety config**: `uv run python chaos_framework.py validate-safety`
- **Lint code**: `uv run ruff check .`
- **Format code**: `uv run ruff format .`

### Safety Configuration Commands
- **Use custom safety config**: `uv run python chaos_framework.py run --experiment test.yaml --safety-config safety_config_dev.yaml`
- **Validate enterprise config**: `uv run python chaos_framework.py validate-safety --safety-config safety_config_enterprise.yaml`
- **Check environment with custom config**: `uv run python chaos_framework.py env-info --safety-config safety_config_enterprise.yaml`

### Dependencies
- **Install dependencies**: `uv sync` (project uses uv for dependency management)
- **Add dependency**: `uv add <package>`

## Architecture

### Core Components

1. **chaos_framework.py** - Main CLI entry point and orchestration
   - Provides template generation for different experiment types (CPU, memory, network)
   - Orchestrates experiment execution with enhanced safety checks and monitoring
   - Extended CLI with safety validation, environment info, and configuration support
   - Handles command-line interface and argument parsing

2. **experiments.py** - Experiment execution engine
   - `ExperimentRunner` class manages different types of chaos experiments
   - Uses system tools like `stress-ng` for CPU/memory stress and `tc` for network latency
   - Provides emergency stop functionality for safety

2.1. **environment_detector.py** - Environment detection system
   - Auto-detects cloud providers (AWS, GCP, Azure) via metadata APIs
   - Pattern matching for hostnames, environment variables, and cloud tags
   - Configurable classification rules for environment types

2.2. **service_discovery.py** - Service discovery integration
   - Kubernetes service discovery with namespace protection
   - Consul integration with tag-based service protection
   - Dynamic identification of protected services

3. **safety.py** - Enhanced safety validation system
   - `SafetyChecker` with configurable YAML-based policies
   - Environment auto-detection (cloud providers, hostname patterns, environment variables)
   - Per-environment safety policies (production, staging, development, test)
   - Experiment-specific parameter validation
   - Detailed safety violation reporting with context
   - Comprehensive audit logging

4. **monitoring.py** - Metrics collection and monitoring
   - `MonitoringClient` integrates with Prometheus-compatible monitoring systems
   - Captures baseline metrics before experiments and compares post-experiment
   - Supports custom monitoring URLs via `CHAOS_MONITORING_URL` environment variable

5. **reporting.py** - Experiment reporting and visualization
   - `ExperimentReporter` generates HTML reports with metrics visualization
   - Uses matplotlib for creating impact charts and pandas for data processing
   - Outputs reports to `./reports` directory by default

### Experiment Flow

1. **Template Creation**: Generate YAML experiment definitions using built-in templates
2. **Environment Detection**: Auto-detect current environment type (production, staging, dev, test)
3. **Safety Policy Loading**: Load appropriate safety configuration for detected environment
4. **Enhanced Safety Validation**:
   - Check if experiments enabled in current environment
   - Validate experiment type against allowlist
   - Check duration limits and parameter constraints
   - Verify target service is not protected (static + service discovery)
   - Generate detailed violation reports if unsafe
5. **Baseline Capture**: Record metrics before experiment (if monitoring enabled)
6. **Experiment Execution**: Run controlled failure injection for specified duration
7. **Metrics Comparison**: Compare post-experiment metrics with baseline
8. **Report Generation**: Create HTML reports with visualizations and analysis
9. **Audit Logging**: Record safety decisions and experiment outcomes for compliance

### Configuration

- **Environment Variables**:
  - `CHAOS_MONITORING_URL`: Monitoring system endpoint (default: http://localhost:9090)
  - `ENVIRONMENT`/`ENV`/`STAGE`: Environment type for auto-detection
- **Experiment YAML Structure**: Contains name, type, description, target (environment/service/hosts), duration, and success criteria
- **Safety Configuration Files**:
  - `safety_config_default.yaml`: Balanced policies for general use
  - `safety_config_dev.yaml`: Permissive policies for development environments
  - `safety_config_enterprise.yaml`: Strict policies for enterprise environments
- **Safety Constraints**: Configurable per environment (duration limits, allowed experiment types, protected services)

### Safety Features

- **Environment Auto-Detection**: Cloud provider detection, hostname patterns, environment variables
- **Configurable Safety Policies**: Different rules per environment type (production, staging, dev, test)
- **Protected Service Validation**: Static lists + dynamic service discovery (K8s, Consul)
- **Experiment-Specific Limits**: CPU intensity, memory usage, network latency constraints
- **Comprehensive Violation Reporting**: Detailed context and remediation guidance
- **Audit Logging**: Complete safety decision tracking for compliance
- **Emergency Stop**: Immediate experiment termination capability
- **Dry-run Mode**: Safe validation without execution

### Safety Configuration Templates

- **Default**: Balanced safety for most organizations
  - Production: Experiments disabled
  - Staging: 30-minute limit, limited experiment types
  - Development: 2-hour limit, all experiment types
  - Test: 2-hour limit, minimal restrictions

- **Development**: Permissive policies for development work
  - Longer durations (up to 4 hours for testing)
  - All experiment types allowed
  - Minimal service protection

- **Enterprise**: Strict security-focused policies
  - Very conservative limits
  - Enhanced audit logging and notifications
  - Comprehensive service protection
  - Business hours restrictions (configurable)

## Documentation Structure

The project includes comprehensive documentation:

- **README.md** - Main project overview, quick start guide, and roadmap summary
- **CLAUDE.md** - This file; developer guidance and detailed architecture documentation
- **SAFETY_SYSTEM.md** - Comprehensive safety system documentation and configuration guide
- **EXAMPLES.md** - Practical usage examples, troubleshooting, and workflow guides
- **ROADMAP.md** - Strategic product roadmap with detailed feature plans and timelines