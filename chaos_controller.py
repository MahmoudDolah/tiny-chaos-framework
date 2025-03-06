# chaos_controller.py
import argparse
import logging
import yaml
import time
from safety import SafetyChecker
from experiments import ExperimentRunner

def load_experiment(file_path):
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)

def main():
    parser = argparse.ArgumentParser(description='Chaos Engineering Mini-Framework')
    parser.add_argument('--experiment', required=True, help='Path to experiment YAML file')
    parser.add_argument('--dry-run', action='store_true', help='Validate but do not run experiment')
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Load experiment definition
    experiment = load_experiment(args.experiment)
    logging.info(f"Loaded experiment: {experiment['name']}")
    
    # Safety checks
    safety = SafetyChecker()
    if not safety.is_safe_to_run(experiment):
        logging.error("Safety check failed. Experiment aborted.")
        return
    
    if args.dry_run:
        logging.info("Dry run complete. Experiment would be safe to execute.")
        return
    
    # Run experiment
    runner = ExperimentRunner()
    try:
        runner.start(experiment)
        time.sleep(experiment['duration'])
        results = runner.stop()
        logging.info(f"Experiment completed: {results}")
    except Exception as e:
        logging.error(f"Error during experiment: {e}")
        runner.emergency_stop()

if __name__ == "__main__":
    main()
