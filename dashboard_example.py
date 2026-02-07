#!/usr/bin/env python3
"""
Example script demonstrating how to use the real-time dashboard
with the tiny-chaos framework.
"""

import subprocess
import time
import webbrowser
import os
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def create_sample_experiment():
    """Create a sample CPU stress experiment for demo purposes"""
    experiment = {
        "name": "Dashboard Demo CPU Stress",
        "type": "cpu_stress",
        "description": "Demonstration of real-time dashboard during CPU stress test",
        "target": {
            "environment": "test",
            "service": "demo-web-server",
            "hosts": ["localhost"]
        },
        "duration": 60,  # 1 minute for demo
        "intensity": 50,
        "success_criteria": [
            "System remains responsive during stress test",
            "Dashboard shows real-time metrics changes"
        ]
    }
    
    import yaml
    with open("demo_experiment.yaml", "w") as f:
        yaml.dump(experiment, f, default_flow_style=False)
    
    logging.info("Created demo_experiment.yaml")
    return "demo_experiment.yaml"


def run_dashboard_demo():
    """Run a complete dashboard demonstration"""
    
    print("🚀 Tiny Chaos Dashboard Demo")
    print("=" * 50)
    
    # Check if dashboard.html exists
    dashboard_path = Path("dashboard.html")
    if not dashboard_path.exists():
        print("❌ dashboard.html not found in current directory")
        print("Make sure you're running this from the tiny-chaos project root")
        return 1
    
    # Create sample experiment
    experiment_file = create_sample_experiment()
    
    print("\n📋 Demo Steps:")
    print("1. Start dashboard server")
    print("2. Open dashboard in browser")
    print("3. Run experiment with dashboard integration")
    print("4. View real-time metrics")
    
    input("\nPress Enter to start the dashboard server...")
    
    # Start dashboard server in background
    print("\n🌐 Starting dashboard server...")
    dashboard_process = subprocess.Popen(
        ["python", "chaos_framework.py", "dashboard"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Give server time to start
    time.sleep(3)
    
    # Open dashboard in browser
    dashboard_url = f"file://{dashboard_path.absolute()}"
    print(f"🔗 Opening dashboard at: {dashboard_url}")
    webbrowser.open(dashboard_url)
    
    print("\n📊 Dashboard should now be open in your browser")
    print("You should see:")
    print("- Connection status indicator")
    print("- Controls for service monitoring")
    print("- Empty charts waiting for data")
    
    input("\nPress Enter to run the demo experiment...")
    
    # Run experiment with dashboard integration
    print("\n🧪 Starting chaos experiment with dashboard...")
    print("This will:")
    print("- Start a CPU stress test")
    print("- Stream metrics to the dashboard in real-time")
    print("- Show experiment status updates")
    
    try:
        result = subprocess.run([
            "python", "chaos_framework.py", "run",
            "--experiment", experiment_file,
            "--monitor", "--dashboard", "--report"
        ], timeout=120)  # 2 minute timeout
        
        if result.returncode == 0:
            print("✅ Experiment completed successfully!")
        else:
            print("❌ Experiment failed or was interrupted")
    
    except subprocess.TimeoutExpired:
        print("⏰ Experiment timed out (this is normal for demo)")
    except KeyboardInterrupt:
        print("🛑 Demo interrupted by user")
    
    # Cleanup
    print("\n🧹 Cleaning up...")
    dashboard_process.terminate()
    dashboard_process.wait()
    
    if os.path.exists(experiment_file):
        os.remove(experiment_file)
        print(f"Removed {experiment_file}")
    
    print("\n🎉 Dashboard demo completed!")
    print("\nTo use the dashboard in your own experiments:")
    print("1. Start dashboard: python chaos_framework.py dashboard")
    print("2. Open dashboard.html in browser")
    print("3. Run experiments with --dashboard flag")
    
    return 0


def run_standalone_dashboard():
    """Run just the dashboard server for manual testing"""
    print("🌐 Starting standalone dashboard server...")
    print("Open dashboard.html in your browser to view the interface")
    print("Press Ctrl+C to stop the server")
    
    try:
        subprocess.run(["python", "chaos_framework.py", "dashboard"])
    except KeyboardInterrupt:
        print("\n🛑 Dashboard server stopped")
        return 0


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--standalone":
        sys.exit(run_standalone_dashboard())
    else:
        sys.exit(run_dashboard_demo())