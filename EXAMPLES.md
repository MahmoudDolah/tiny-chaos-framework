# Usage Examples

This document provides practical examples of using the Tiny Chaos Framework with the Enhanced Safety & Configuration System.

## Basic Workflow

### 1. Check Your Environment

First, understand what environment the framework detects and what safety policies apply:

```bash
# Check current environment and safety policy
uv run python chaos_framework.py env-info

# Example output:
# === Environment Information ===
# Environment Type: development
# Hostname: dev-server-01
# Matched Detection Rules:
#   - development (hostname): dev-* -> dev-server-01
#
# === Safety Policy ===
# Experiments Enabled: True
# Maximum Duration: 7200 seconds
# Allowed Experiment Types: ['*']
# Protected Services: []
# Require Confirmation: False
```

### 2. Choose Safety Configuration

Select the appropriate safety configuration for your use case:

```bash
# For development work (permissive)
uv run python chaos_framework.py env-info --safety-config safety_config_dev.yaml

# For production-like environments (strict)
uv run python chaos_framework.py env-info --safety-config safety_config_enterprise.yaml

# For balanced policies (default)
uv run python chaos_framework.py env-info --safety-config safety_config_default.yaml
```

### 3. Create Experiment Template

Generate experiment templates with safety-aware defaults:

```bash
# Create CPU stress experiment
uv run python chaos_framework.py template --type cpu --output cpu_test.yaml

# Create with specific safety config (affects template parameters)
uv run python chaos_framework.py template --type cpu --output cpu_test_enterprise.yaml --safety-config safety_config_enterprise.yaml
```

### 4. Validate Experiment Safety

Always validate experiments before running:

```bash
# Dry run with current environment detection
uv run python chaos_framework.py run --experiment cpu_test.yaml --dry-run

# Dry run with specific safety configuration
uv run python chaos_framework.py run --experiment cpu_test.yaml --dry-run --safety-config safety_config_dev.yaml
```

### 5. Run Experiments

Execute experiments with appropriate safety controls:

```bash
# Basic experiment run
uv run python chaos_framework.py run --experiment cpu_test.yaml

# With monitoring and reporting
uv run python chaos_framework.py run --experiment cpu_test.yaml --monitor --report

# With custom safety configuration
uv run python chaos_framework.py run --experiment cpu_test.yaml --safety-config safety_config_dev.yaml --monitor --report
```

## Environment-Specific Examples

### Development Environment

```bash
# Set environment explicitly
export ENVIRONMENT=dev

# Create and run permissive experiment
uv run python chaos_framework.py template --type memory --output dev_memory_test.yaml --safety-config safety_config_dev.yaml
uv run python chaos_framework.py run --experiment dev_memory_test.yaml --safety-config safety_config_dev.yaml
```

### Staging Environment

```bash
# Staging environment with balanced safety
export ENVIRONMENT=staging

# Validate with default configuration
uv run python chaos_framework.py validate-safety

# Run conservative experiment
uv run python chaos_framework.py template --type cpu --output staging_cpu_test.yaml
uv run python chaos_framework.py run --experiment staging_cpu_test.yaml --dry-run
```

### Enterprise/Production-Adjacent Environment

```bash
# Use enterprise configuration for maximum safety
uv run python chaos_framework.py env-info --safety-config safety_config_enterprise.yaml

# Attempt to create experiment (may be restricted)
uv run python chaos_framework.py template --type cpu --output enterprise_test.yaml --safety-config safety_config_enterprise.yaml

# Validate strict safety policies
uv run python chaos_framework.py validate-safety --safety-config safety_config_enterprise.yaml
```

## Safety Violation Examples

### Example 1: Environment Detection Blocking

```bash
# Simulate production environment
export ENVIRONMENT=prod

# Try to run experiment (will be blocked)
uv run python chaos_framework.py run --experiment cpu_test.yaml --dry-run

# Output:
# ERROR - Safety check failed. Experiment aborted.
# ERROR -   - environment_disabled: Chaos experiments are disabled in production environment
```

### Example 2: Protected Service Detection

```bash
# Create experiment targeting protected service
cat > protected_service_test.yaml << EOF
name: Database Stress Test
type: cpu_stress
description: Test targeting protected database service
target:
  environment: staging
  service: database
  hosts: ["staging-db-01"]
duration: 300
intensity: 80
EOF

# Try to run (will be blocked)
uv run python chaos_framework.py run --experiment protected_service_test.yaml --dry-run

# Output:
# ERROR -   - protected_service: Service 'database' is protected and cannot be targeted
```

### Example 3: Duration Limit Exceeded

```bash
# Create long-running experiment
cat > long_test.yaml << EOF
name: Long CPU Test
type: cpu_stress
target:
  environment: staging
  service: web-server
  hosts: ["staging-web-01"]
duration: 7200  # 2 hours
intensity: 50
EOF

# Try with enterprise config (strict limits)
uv run python chaos_framework.py run --experiment long_test.yaml --dry-run --safety-config safety_config_enterprise.yaml

# Output:
# ERROR -   - duration_exceeded: Experiment duration 7200s exceeds maximum allowed 600s
```

## Configuration Management

### Validate Configuration Files

```bash
# Validate default configuration
uv run python chaos_framework.py validate-safety

# Validate specific configuration
uv run python chaos_framework.py validate-safety --safety-config safety_config_enterprise.yaml

# Example success output:
# INFO - Safety configuration is valid
# INFO - Current environment: development
# INFO - Experiments enabled: True
# INFO - Max duration: 7200 seconds
# INFO - Allowed types: ['*']
```

### Environment Override Testing

```bash
# Test different environment variables
ENVIRONMENT=prod uv run python chaos_framework.py env-info
ENVIRONMENT=staging uv run python chaos_framework.py env-info
ENVIRONMENT=dev uv run python chaos_framework.py env-info
ENV=test uv run python chaos_framework.py env-info
STAGE=production uv run python chaos_framework.py env-info
```

### Cloud Environment Simulation

```bash
# The framework will attempt to detect cloud providers
# In cloud environments, it will show additional metadata:

# Example AWS output:
# Environment Type: production
# Cloud Provider: aws
# Matched Detection Rules:
#   - production (cloud_tag): environment=production -> environment=production

# Example local development:
# Environment Type: development
# Hostname: dev-laptop
# No cloud provider detected
```

## Troubleshooting

### Safety Configuration Issues

```bash
# Check configuration validity
uv run python chaos_framework.py validate-safety --safety-config your_config.yaml

# Get detailed environment information
uv run python chaos_framework.py --verbose env-info --safety-config your_config.yaml

# Test specific experiment with verbose output
uv run python chaos_framework.py --verbose run --experiment test.yaml --dry-run --safety-config your_config.yaml
```

### Environment Detection Issues

```bash
# Force environment detection
ENVIRONMENT=your_env uv run python chaos_framework.py env-info

# Check hostname-based detection
hostname  # Check your current hostname
uv run python chaos_framework.py env-info  # See how it's classified

# Test pattern matching
grep -A 10 "classification_rules" safety_config_default.yaml
```

### Permission and Safety Issues

```bash
# Use most permissive configuration for testing
uv run python chaos_framework.py run --experiment test.yaml --safety-config safety_config_dev.yaml --dry-run

# Check what services are protected
uv run python chaos_framework.py --verbose env-info | grep -A 5 "Protected Services"

# Test with minimal experiment
cat > minimal_test.yaml << EOF
name: Minimal Test
type: cpu_stress
target:
  environment: test
  service: test-service
  hosts: ["localhost"]
duration: 60  # 1 minute
intensity: 10  # 10% CPU
EOF
```

## Best Practices

1. **Always Start with `env-info`**: Understand your environment before running experiments
2. **Use Dry Runs**: Always test with `--dry-run` first
3. **Choose Appropriate Config**: Use `safety_config_dev.yaml` for development, `safety_config_enterprise.yaml` for production-adjacent environments
4. **Monitor Safety Logs**: Check `./logs/safety_audit.log` for compliance tracking
5. **Validate Configurations**: Use `validate-safety` command when creating custom configurations
6. **Environment Variables**: Set `ENVIRONMENT` explicitly to ensure correct environment detection