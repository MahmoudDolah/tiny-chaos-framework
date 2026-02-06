#!/usr/bin/env python3

import argparse
import logging
import sys
import yaml
import os
from safety import SafetyChecker
from experiments import ExperimentRunner
from monitoring import MonitoringClient
from reporting import ExperimentReporter

VERSION = "0.1.0"

def setup_logging(verbose=False):
    """Configure logging based on verbosity level"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def create_experiment_template(args):
    """Create a template experiment YAML file"""
    experiment_types = {
        "cpu": {
            "name": "CPU Stress Test",
            "type": "cpu_stress",
            "description": "Simulate high CPU load on test servers",
            "target": {
                "environment": "test",
                "service": "web-server",
                "hosts": ["test-server-01", "test-server-02"]
            },
            "duration": 300,  # seconds
            "intensity": 80,  # percentage
            "success_criteria": [
                "Autoscaling group scales up within 2 minutes",
                "No request timeouts during experiment"
            ]
        },
        "memory": {
            "name": "Memory Pressure Test",
            "type": "memory_exhaust",
            "description": "Simulate memory pressure on test servers",
            "target": {
                "environment": "test",
                "service": "web-server", 
                "hosts": ["test-server-01"]
            },
            "duration": 180,  # seconds
            "memory_mb": 1024,  # MB to consume
            "success_criteria": [
                "OOM killer does not trigger",
                "Service remains responsive"
            ]
        },
        "network": {
            "name": "Network Latency Test",
            "type": "network_latency",
            "description": "Introduce network latency between services",
            "target": {
                "environment": "test",
                "service": "api-gateway",
                "hosts": ["test-api-01"]
            },
            "duration": 240,  # seconds
            "interface": "eth0",
            "latency_ms": 100,  # milliseconds
            "success_criteria": [
                "Circuit breakers activate appropriately",
                "Timeout mechanisms function correctly"
            ]
        }
    }
    
    exp_type = args.type
    if exp_type not in experiment_types:
        logging.error(f"Unknown experiment type: {exp_type}")
        logging.info(f"Available types: {', '.join(experiment_types.keys())}")
        return 1
        
    template = experiment_types[exp_type]
    
    # Save template to file
    output_file = args.output
    with open(output_file, 'w') as f:
        yaml.dump(template, f, default_flow_style=False)
        
    logging.info(f"Template created: {output_file}")
    return 0

def run_experiment(args):
    """Run a chaos engineering experiment"""
    # Load experiment definition
    try:
        with open(args.experiment, 'r') as f:
            experiment = yaml.safe_load(f)
    except Exception as e:
        logging.error(f"Failed to load experiment: {e}")
        return 1
        
    logging.info(f"Loaded experiment: {experiment['name']}")
    
    # Safety checks
    safety = SafetyChecker(args.safety_config if hasattr(args, 'safety_config') else None)

    # Validate safety configuration if requested
    if hasattr(args, 'validate_safety') and args.validate_safety:
        return validate_safety_config(safety)

    is_safe, violations = safety.is_safe_to_run(experiment)

    if not is_safe:
        logging.error("Safety check failed. Experiment aborted.")
        for violation in violations:
            logging.error(f"  - {violation.violation_type}: {violation.message}")
            if args.verbose and violation.details:
                logging.error(f"    Details: {violation.details}")
        return 1

    if args.verbose:
        env_info = safety.get_environment_info()
        logging.info(f"Environment detected: {env_info['environment_type']}")
        logging.info(f"Safety policy: {env_info['policy']['enabled']} (max duration: {env_info['policy']['max_duration']}s)")
        
    if args.dry_run:
        logging.info("Dry run complete. Experiment would be safe to execute.")
        return 0
        
    # Setup monitoring if requested
    monitoring = None
    if args.monitor:
        monitoring_url = os.environ.get('CHAOS_MONITORING_URL', 'http://localhost:9090')
        monitoring = MonitoringClient(monitoring_url)
        logging.info(f"Capturing baseline metrics for {experiment['target']['service']}")
        baseline = monitoring.capture_baseline(experiment['target']['service'])
        logging.info(f"Baseline captured: {len(baseline)} metrics")
    
    # Run experiment
    runner = ExperimentRunner()
    try:
        logging.info(f"Starting experiment: {experiment['name']}")
        runner.start(experiment)
        
        # Wait for completion
        import time
        logging.info(f"Experiment running for {experiment['duration']} seconds...")
        time.sleep(experiment['duration'])
        
        # Stop experiment
        logging.info("Stopping experiment...")
        results = runner.stop()
        logging.info(f"Experiment completed: {results}")
        
        # Generate report if monitoring was enabled
        if monitoring:
            logging.info("Collecting post-experiment metrics...")
            comparison = monitoring.compare_with_baseline(experiment['target']['service'])
            
            if args.report:
                reporter = ExperimentReporter()
                report_file = reporter.generate_report(experiment, comparison)
                logging.info(f"Report generated: {report_file}")
                
        return 0
        
    except KeyboardInterrupt:
        logging.warning("Experiment interrupted by user")
        runner.emergency_stop()
        return 130
        
    except Exception as e:
        logging.error(f"Error during experiment: {e}")
        runner.emergency_stop()
        return 1

def validate_safety_config(safety):
    """Validate safety configuration and return status."""
    issues = safety.validate_config()

    if issues:
        logging.error("Safety configuration validation failed:")
        for issue in issues:
            logging.error(f"  - {issue}")
        return 1
    else:
        logging.info("Safety configuration is valid")
        return 0

def validate_safety_command(args):
    """Command to validate safety configuration."""
    try:
        safety = SafetyChecker(args.safety_config)
        issues = safety.validate_config()

        if issues:
            logging.error("Safety configuration validation failed:")
            for issue in issues:
                logging.error(f"  - {issue}")
            return 1
        else:
            logging.info("Safety configuration is valid")

            # Show configuration summary
            env_info = safety.get_environment_info()
            logging.info(f"Current environment: {env_info['environment_type']}")

            policy = env_info['policy']
            logging.info(f"Experiments enabled: {policy.get('enabled', False)}")
            logging.info(f"Max duration: {policy.get('max_duration', 0)} seconds")
            logging.info(f"Allowed types: {policy.get('allowed_experiment_types', [])}")
            logging.info(f"Protected services: {len(policy.get('protected_services', []))} configured")

            return 0

    except Exception as e:
        logging.error(f"Failed to validate safety configuration: {e}")
        return 1

def environment_info_command(args):
    """Command to show current environment information."""
    try:
        safety = SafetyChecker(args.safety_config)
        env_info = safety.get_environment_info()

        logging.info("=== Environment Information ===")
        logging.info(f"Environment Type: {env_info['environment_type']}")

        details = env_info['environment_details']
        logging.info(f"Hostname: {details.get('hostname', 'unknown')}")

        if details.get('cloud_provider'):
            logging.info(f"Cloud Provider: {details['cloud_provider']}")

        if details.get('matched_rules'):
            logging.info("Matched Detection Rules:")
            for rule in details['matched_rules']:
                logging.info(f"  - {rule['rule']} ({rule['type']}): {rule['pattern']} -> {rule['value']}")

        policy = env_info['policy']
        logging.info("\n=== Safety Policy ===")
        logging.info(f"Experiments Enabled: {policy.get('enabled', False)}")
        logging.info(f"Maximum Duration: {policy.get('max_duration', 0)} seconds")
        logging.info(f"Allowed Experiment Types: {policy.get('allowed_experiment_types', [])}")
        logging.info(f"Protected Services: {policy.get('protected_services', [])}")
        logging.info(f"Require Confirmation: {policy.get('require_confirmation', False)}")

        protected_services = env_info.get('protected_services', [])
        if protected_services:
            logging.info("\n=== Service Discovery ===")
            logging.info(f"Protected Services Found: {list(protected_services)}")

        return 0

    except Exception as e:
        logging.error(f"Failed to get environment information: {e}")
        return 1

def main():
    """Main entry point for the chaos engineering mini-framework"""
    parser = argparse.ArgumentParser(
        description='Chaos Engineering Mini-Framework',
        epilog='Run controlled chaos experiments to test system resilience'
    )
    parser.add_argument('--version', action='version', version=f'%(prog)s {VERSION}')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Create template command
    template_parser = subparsers.add_parser('template', help='Create experiment template')
    template_parser.add_argument('--type', choices=['cpu', 'memory', 'network'], required=True,
                                help='Type of experiment template')
    template_parser.add_argument('--output', required=True, help='Output file for template')
    template_parser.add_argument('--safety-config', help='Path to safety configuration YAML file (affects template generation)')
    
    # Run experiment command
    run_parser = subparsers.add_parser('run', help='Run chaos experiment')
    run_parser.add_argument('--experiment', required=True, help='Path to experiment YAML file')
    run_parser.add_argument('--dry-run', action='store_true', help='Validate but do not run experiment')
    run_parser.add_argument('--monitor', action='store_true', help='Enable monitoring integration')
    run_parser.add_argument('--report', action='store_true', help='Generate experiment report')
    run_parser.add_argument('--safety-config', help='Path to safety configuration YAML file')

    # Safety validation command
    safety_parser = subparsers.add_parser('validate-safety', help='Validate safety configuration')
    safety_parser.add_argument('--safety-config', help='Path to safety configuration YAML file')

    # Environment info command
    env_parser = subparsers.add_parser('env-info', help='Show current environment information')
    env_parser.add_argument('--safety-config', help='Path to safety configuration YAML file')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Execute command
    if args.command == 'template':
        return create_experiment_template(args)
    elif args.command == 'run':
        return run_experiment(args)
    elif args.command == 'validate-safety':
        return validate_safety_command(args)
    elif args.command == 'env-info':
        return environment_info_command(args)
    else:
        parser.print_help()
        return 0

if __name__ == "__main__":
    sys.exit(main())
