#!/usr/bin/env python3
"""
Start the EduSched test environment.

This script starts:
1. The backend API server
2. The frontend development server
3. Monitors both for errors
"""

import subprocess
import sys
import time
import os
from pathlib import Path
import signal


class TestEnvironmentManager:
    """Manages the test environment processes."""

    def __init__(self):
        self.processes = []
        self.project_root = Path(__file__).parent

    def start_backend(self):
        """Start the backend FastAPI server."""
        print("Starting backend server...")

        # Check if FastAPI is installed
        try:
            import uvicorn
            import fastapi
        except ImportError:
            print("❌ FastAPI dependencies not found. Please install them:")
            print("pip install fastapi uvicorn websockets")
            return False

        # Start backend in subprocess
        backend_cmd = [
            sys.executable, "-m", "uvicorn",
            "edusched.api.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ]

        # Set environment variables
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.project_root / "src")

        try:
            process = subprocess.Popen(
                backend_cmd,
                cwd=self.project_root,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            self.processes.append(("backend", process))

            # Wait a moment for startup
            time.sleep(3)

            # Check if process is still running
            if process.poll() is None:
                print("✅ Backend server started successfully")
                print("   API Docs: http://localhost:8000/docs")
                return True
            else:
                print("❌ Backend server failed to start")
                return False
        except Exception as e:
            print(f"❌ Failed to start backend: {e}")
            return False

    def start_frontend(self):
        """Start the frontend React development server."""
        print("Starting frontend server...")

        frontend_dir = self.project_root / "frontend"

        # Check if node_modules exists
        if not (frontend_dir / "node_modules").exists():
            print("Installing frontend dependencies...")
            npm_install = subprocess.run(
                ["npm", "install"],
                cwd=frontend_dir,
                capture_output=True,
                text=True
            )
            if npm_install.returncode != 0:
                print(f"❌ Failed to install dependencies: {npm_install.stderr}")
                return False

        # Start frontend dev server
        frontend_cmd = ["npm", "run", "dev"]

        try:
            process = subprocess.Popen(
                frontend_cmd,
                cwd=frontend_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            self.processes.append(("frontend", process))

            # Wait a moment for startup
            time.sleep(5)

            # Check if process is still running
            if process.poll() is None:
                print("✅ Frontend server started successfully")
                print("   Frontend: http://localhost:5173")
                return True
            else:
                print("❌ Frontend server failed to start")
                return False
        except Exception as e:
            print(f"❌ Failed to start frontend: {e}")
            return False

    def monitor_output(self):
        """Monitor output from all processes."""
        print("\nMonitoring server output (Ctrl+C to stop)...")
        print("-"*50)

        try:
            while True:
                # Check each process for output
                for name, process in self.processes:
                    if process.poll() is not None:
                        print(f"\n❌ {name} process has stopped!")
                        return False

                    # Read any available output
                    while True:
                        line = process.stdout.readline()
                        if line:
                            # Print with prefix
                            print(f"[{name}] {line.strip()}")
                        else:
                            break

                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n\nShutting down servers...")
            return True

    def cleanup(self):
        """Clean up all processes."""
        for name, process in self.processes:
            try:
                print(f"Stopping {name} server...")
                process.terminate()
                process.wait(timeout=5)
                print(f"✅ {name} server stopped")
            except subprocess.TimeoutExpired:
                print(f"Force killing {name} server...")
                process.kill()
                process.wait()
            except Exception as e:
                print(f"Error stopping {name}: {e}")

    def run(self):
        """Run the test environment."""
        print("EduSched Test Environment")
        print("="*50)

        # Set up signal handler for cleanup
        def signal_handler(sig, frame):
            print("\nReceived interrupt signal...")
            self.cleanup()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            # Start backend
            if not self.start_backend():
                self.cleanup()
                return False

            # Start frontend
            if not self.start_frontend():
                self.cleanup()
                return False

            # Monitor
            success = self.monitor_output()

            # Cleanup
            self.cleanup()

            return success

        except Exception as e:
            print(f"Error: {e}")
            self.cleanup()
            return False


def main():
    """Main entry point."""
    manager = TestEnvironmentManager()
    success = manager.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()