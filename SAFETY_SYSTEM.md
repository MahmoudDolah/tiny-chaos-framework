# Enhanced Safety & Configuration System

The Tiny Chaos Framework includes a comprehensive safety system to prevent chaos experiments from causing damage in inappropriate environments.

## Key Features

### 1. Environment Auto-Detection
- **Cloud Provider Detection**: Automatically detects AWS, GCP, and Azure environments via metadata APIs
- **Pattern Matching**: Uses hostname patterns, environment variables, and cloud tags to classify environments
- **Rule-Based Classification**: Configurable rules to identify production, staging, development, and test environments

### 2. Configurable Safety Policies
- **Per-Environment Policies**: Different safety rules for each environment type
- **Experiment Type Allowlists**: Control which experiment types can run in each environment
- **Duration Limits**: Maximum experiment duration per environment
- **Protected Services**: Lists of services that cannot be targeted for experiments

### 3. Service Discovery Integration
- **Kubernetes Integration**: Automatically identifies protected services in K8s clusters
- **Consul Integration**: Discovers services marked with protected tags
- **Dynamic Protection**: Real-time discovery of critical services

## Configuration Files

### Default Configuration (`safety_config_default.yaml`)
- Balanced safety policies suitable for most organizations
- Production experiments disabled by default
- Conservative limits for staging and development

### Development Configuration (`safety_config_dev.yaml`)
- Permissive policies for development environments
- Longer experiment durations allowed
- Minimal protected services

### Enterprise Configuration (`safety_config_enterprise.yaml`)
- Strict security policies for enterprise environments
- Enhanced audit logging and notifications
- Comprehensive protection rules

## CLI Commands

### Environment Information
```bash
# Show current environment detection results
python chaos_framework.py env-info

# Use custom safety config
python chaos_framework.py env-info --safety-config safety_config_enterprise.yaml
```

### Safety Validation
```bash
# Validate safety configuration
python chaos_framework.py validate-safety

# Validate with custom config
python chaos_framework.py validate-safety --safety-config safety_config_dev.yaml
```

### Running Experiments with Safety
```bash
# Run with default safety config
python chaos_framework.py run --experiment test.yaml --dry-run

# Run with custom safety config
python chaos_framework.py run --experiment test.yaml --safety-config safety_config_dev.yaml --dry-run
```

## Environment Detection Examples

### Automatic Detection
The system automatically detects environments using:

1. **Cloud Metadata**: Queries cloud provider APIs for instance information
2. **Environment Variables**: Checks `ENVIRONMENT`, `ENV`, `STAGE` variables
3. **Hostname Patterns**: Matches hostnames against configurable patterns
4. **Cloud Tags**: Uses cloud provider tags for classification

### Manual Override
You can force environment detection by setting environment variables:
```bash
ENVIRONMENT=development python chaos_framework.py env-info
```

## Safety Policy Structure

Each environment has its own safety policy:

```yaml
environment_policies:
  production:
    enabled: false                    # Experiments disabled
    max_duration: 0
    allowed_experiment_types: []
    protected_services: ["*"]         # All services protected
    require_confirmation: true
    require_approval: true

  development:
    enabled: true                     # Experiments enabled
    max_duration: 7200               # 2 hours
    allowed_experiment_types: ["*"]   # All types allowed
    protected_services: []            # No protected services
    require_confirmation: false
    require_approval: false
```

## Experiment-Specific Safety

The system includes experiment-specific safety rules:

```yaml
experiment_safety:
  cpu_stress:
    max_intensity: 90               # Maximum CPU percentage
    min_available_cores: 1          # Always leave cores available

  memory_exhaust:
    max_memory_percentage: 80       # Maximum memory to consume
    min_free_memory_mb: 512        # Always leave memory free

  network_latency:
    max_latency_ms: 5000           # Maximum latency to introduce
    allowed_interfaces: ["eth0"]    # Allowed network interfaces
```

## Safety Violations

When safety checks fail, the system provides detailed violation information:

- **Violation Type**: Category of safety violation
- **Message**: Human-readable description
- **Details**: Additional context and parameters

Example output:
```
Safety check failed. Experiment aborted.
  - environment_disabled: Chaos experiments are disabled in production environment
    Details: {'environment': 'production', 'policy': {...}}
  - protected_service: Service 'database' is protected and cannot be targeted
    Details: {'service': 'database', 'environment': 'production'}
```

## Audit and Compliance

The enhanced safety system includes comprehensive audit capabilities:

- **Safety Decision Logging**: All safety decisions are logged with timestamps
- **Experiment Details**: Full experiment configuration can be included in logs
- **Violation Tracking**: Detailed information about safety violations
- **Compliance Reporting**: Structured logs for compliance requirements

## Best Practices

1. **Use Environment-Specific Configs**: Choose the appropriate safety configuration for your environment type
2. **Test Safety Rules**: Use `validate-safety` command to verify configuration
3. **Monitor Environment Detection**: Use `env-info` to verify correct environment classification
4. **Start with Dry Runs**: Always test experiments with `--dry-run` first
5. **Review Audit Logs**: Regularly check safety audit logs for compliance