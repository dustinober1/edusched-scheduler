#!/usr/bin/env python3
"""Quick test to verify the EduSched stack is working."""

import subprocess
import sys
import time
import os
from pathlib import Path


def run_command(cmd, cwd=None, capture_output=True):
    """Run a command and return result."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)


def test_backend():
    """Test if backend can start."""
    print("Testing backend...")

    # Check if dependencies are installed
    success, _, _ = run_command("python3 -c \"import fastapi, uvicorn, websockets\"")
    if not success:
        print("❌ Backend dependencies not installed")
        print("   Run: pip install fastapi uvicorn websockets")
        return False

    print("✅ Backend dependencies installed")

    # Test if backend can import
    success, _, _ = run_command("python3 -c \"from edusched.api.main import app\"")
    if not success:
        print("❌ Backend import failed")
        return False

    print("✅ Backend imports successfully")
    return True


def test_frontend():
    """Test if frontend is set up."""
    print("\nTesting frontend...")

    frontend_dir = Path(__file__).parent / "frontend"

    # Check if node_modules exists
    if not (frontend_dir / "node_modules").exists():
        print("⚠️  Frontend dependencies not installed")
        print("   Run: cd frontend && npm install")
        return False

    print("✅ Frontend dependencies installed")

    # Check package.json
    if not (frontend_dir / "package.json").exists():
        print("❌ package.json not found")
        return False

    print("✅ Frontend package.json found")
    return True


def main():
    """Run quick tests."""
    print("EduSched Quick Test")
    print("="*50)

    backend_ok = test_backend()
    frontend_ok = test_frontend()

    print("\n" + "="*50)
    print("Summary:")
    print(f"Backend: {'✅ Ready' if backend_ok else '❌ Issues'}")
    print(f"Frontend: {'✅ Ready' if frontend_ok else '❌ Issues'}")

    if backend_ok and frontend_ok:
        print("\n🚀 Ready to run full-stack test!")
        print("\nNext steps:")
        print("1. Start both servers: python3 start_test_environment.py")
        print("2. Or start manually:")
        print("   Backend: uvicorn edusched.api.main:app --reload --port 8000")
        print("   Frontend: cd frontend && npm run dev")
        print("3. Run tests: python3 test_full_stack.py")
        print("4. Or visit: http://localhost:5173/test")
    else:
        print("\n❌ Please fix the issues above before testing")

    return backend_ok and frontend_ok


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)