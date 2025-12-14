# Pre-publication Review Report

**Date:** December 13, 2025
**Package:** `edusched`
**Version:** 0.1.0

## Summary
The package currently **fails** pre-publication checks due to missing critical files (README, LICENSE) and broken code references (missing source files for declared dependencies).

## 1. Metadata & Configuration (`pyproject.toml`)
*   **Status:** ⚠️ Needs Update
*   **Issues:**
    *   `project.license`: Defined as a table `{text = "MIT"}` which is deprecated. Must be a SPDX string or `license-files`.
    *   `classifiers`: Contains deprecated "License :: OSI Approved :: MIT License".
    *   `readme`: References `README.md`, which does not exist in the root directory.

## 2. File Structure
*   **Status:** ❌ Critical Missing Files
*   **Issues:**
    *   `README.md`: Missing. Required for PyPI.
    *   `LICENSE`: Missing. Required for distribution.

## 3. Dependencies & Code Integrity
*   **Status:** ❌ Broken References
*   **Issues:**
    *   **`ortools`**: Listed as optional dependency. Referenced in `src/edusched/api.py` (`from edusched.solvers.ortools_solver import ORToolsSolver`), but `src/edusched/solvers/ortools_solver.py` **does not exist**. This will cause `ImportError`.
    *   **`matplotlib`**: Listed in `optional-dependencies` (`viz`), but **unused** in the codebase.
    *   **`icalendar`**: Listed in `optional-dependencies` (`ics`), but **unused** in the codebase.

## 4. Build Check
*   **Status:** ⚠️ Warnings
*   **Output:** `setuptools` verified the missing `README.md` and deprecated license config.

## Recommendations
1.  **Create `README.md`**: Add a project description, installation instructions, and usage examples.
2.  **Create `LICENSE`**: Add the MIT License text.
3.  **Update `pyproject.toml`**: Fix license definition and classifiers.
4.  **Fix `ortools`**: Either implement `ortools_solver.py` or remove the import from `api.py` and the dependency.
5.  **Clean Dependencies**: Remove unused `viz` and `ics` extras or implement the features.
