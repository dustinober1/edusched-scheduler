Contributing
============

Thank you for your interest in contributing to EduSched! This document provides guidelines and information about how to contribute.

Getting Started
---------------

1. Fork the repository on GitHub
2. Clone your fork: ``git clone https://github.com/YOUR_USERNAME/edusched-scheduler.git``
3. Create a virtual environment: ``python -m venv venv``
4. Activate the virtual environment: ``source venv/bin/activate`` (Linux/Mac) or ``venv\Scripts\activate`` (Windows)
5. Install dependencies: ``pip install -e ".[dev]"``

Development Workflow
--------------------

1. Create a feature branch: ``git checkout -b feature/amazing-feature``
2. Make your changes
3. Add tests for your changes
4. Run tests: ``pytest``
5. Run linting: ``ruff check .``
6. Run type checking: ``mypy src/``
7. Commit your changes: ``git commit -m 'Add amazing feature'``
8. Push to the branch: ``git push origin feature/amazing-feature``
9. Open a Pull Request

Code Style
----------

* Follow PEP 8 style guidelines
* Use type hints for all public functions
* Write docstrings for all public classes and functions
* Keep functions focused and small when possible
* Write comprehensive tests for new features

Testing
-------

All contributions should include appropriate tests:

* Unit tests for individual functions and classes
* Integration tests for complex interactions
* Property-based tests where appropriate

Run all tests with: ``pytest``

Documentation
-------------

Update documentation when adding new features:

* API documentation in docstrings
* User guides in the docs directory
* Examples showing how to use new features