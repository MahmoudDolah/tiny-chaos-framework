# Tiny Chaos Framework

A lightweight Python framework for running chaos engineering experiments with comprehensive safety controls and environment-aware policies.

## Features

- **🛡️ Enhanced Safety System**: Environment auto-detection, configurable policies, and comprehensive safety checks
- **🎯 Multiple Experiment Types**: CPU stress, memory exhaustion, and network latency experiments
- **📊 Monitoring Integration**: Prometheus-compatible metrics collection and comparison
- **📈 HTML Reporting**: Automated experiment reports with visualizations
- **🔧 CLI Interface**: Easy-to-use command-line tools for experiment management
- **☁️ Cloud-Aware**: Automatic detection of AWS, GCP, and Azure environments

## Quick Start

### Installation

```bash
# Install dependencies
uv sync
```

### Basic Usage

```bash
# Check current environment and safety policy
uv run python chaos_framework.py env-info

# Create an experiment template
uv run python chaos_framework.py template --type cpu --output my_experiment.yaml

# Validate experiment safety (dry run)
uv run python chaos_framework.py run --experiment my_experiment.yaml --dry-run

# Run experiment with monitoring and reporting
uv run python chaos_framework.py run --experiment my_experiment.yaml --monitor --report
```

## Safety System

The framework includes a comprehensive safety system with:

- **Environment Auto-Detection**: Automatically identifies production, staging, development, and test environments
- **Configurable Policies**: Different safety rules per environment type
- **Protected Services**: Prevents experiments on critical services
- **Service Discovery**: Integration with Kubernetes and Consul

See [SAFETY_SYSTEM.md](SAFETY_SYSTEM.md) for detailed documentation.

## Configuration

Choose from pre-built safety configurations:

- `safety_config_default.yaml` - Balanced policies for general use
- `safety_config_dev.yaml` - Permissive policies for development
- `safety_config_enterprise.yaml` - Strict policies for enterprise environments

```bash
# Use custom safety configuration
uv run python chaos_framework.py run --experiment test.yaml --safety-config safety_config_dev.yaml
```

## Experiment Types

- **CPU Stress**: Simulate high CPU load using stress-ng
- **Memory Exhaustion**: Consume system memory to test memory pressure
- **Network Latency**: Introduce network delays using traffic control

## Documentation

- [Safety System Documentation](SAFETY_SYSTEM.md) - Comprehensive guide to the safety features
- [Usage Examples](EXAMPLES.md) - Practical examples and troubleshooting guide
- [Product Roadmap](ROADMAP.md) - Strategic development roadmap and future features
- [Claude Code Instructions](CLAUDE.md) - Developer guidance for working with this codebase

## Development

```bash
# Lint code
uv run ruff check .

# Format code
uv run ruff format .

# Validate safety configuration
uv run python chaos_framework.py validate-safety
```

## Roadmap

The Tiny Chaos Framework is actively evolving toward a comprehensive chaos engineering platform:

**✅ Phase 1 - Foundation (In Progress)**
- ✅ Enhanced Safety & Configuration System
- 🔄 Real-time Experiment Monitoring
- 📋 Expanded Experiment Library (15+ types)
- 🤖 Automated Success Criteria Validation

**🎯 Phase 2 - Advanced Capabilities (6-12 months)**
- Experiment Orchestration & Scheduling
- Multi-platform Monitoring Integration
- Plugin Architecture & Extensibility

**🚀 Phase 3 - Platform Maturity (12-18 months)**
- Machine Learning-powered Insights
- Cloud-native & Distributed Execution
- Enterprise Integration Ecosystem

See [ROADMAP.md](ROADMAP.md) for detailed feature plans and timelines.
