# experiments.py
import subprocess
import logging
import random

class ExperimentRunner:
    def __init__(self):
        self.running_experiments = []
        
    def start(self, experiment):
        experiment_type = experiment['type']
        
        if experiment_type == 'cpu_stress':
            self._start_cpu_stress(experiment)
        elif experiment_type == 'memory_exhaust':
            self._start_memory_exhaust(experiment)
        elif experiment_type == 'network_latency':
            self._start_network_latency(experiment)
        else:
            raise ValueError(f"Unknown experiment type: {experiment_type}")
            
        logging.info(f"Started {experiment_type} experiment")
        
    def _start_cpu_stress(self, experiment):
        # Example using stress-ng for CPU load
        intensity = experiment.get('intensity', 80)
        cmd = f"stress-ng --cpu 1 --cpu-load {intensity} --timeout {experiment['duration']}s"
        process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
        self.running_experiments.append(('cpu_stress', process))
        
    def _start_memory_exhaust(self, experiment):
        # Memory exhaustion experiment
        memory_mb = experiment.get('memory_mb', 1024)
        cmd = f"stress-ng --vm 1 --vm-bytes {memory_mb}M --timeout {experiment['duration']}s"
        process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
        self.running_experiments.append(('memory_exhaust', process))
        
    def _start_network_latency(self, experiment):
        # Network latency using tc
        interface = experiment.get('interface', 'eth0')
        latency_ms = experiment.get('latency_ms', 100)
        cmd = f"tc qdisc add dev {interface} root netem delay {latency_ms}ms"
        subprocess.run(cmd.split(), check=True)
        self.running_experiments.append(('network_latency', interface))
        
    def stop(self):
        results = {}
        
        for exp_type, process_or_resource in self.running_experiments:
            if exp_type == 'network_latency':
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
