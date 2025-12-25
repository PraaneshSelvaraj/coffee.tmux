# Contributing to Coffee.tmux

Thank you for your interest in contributing to Coffee.tmux! We welcome contributions of all kinds, including bug reports, feature requests, documentation improvements, and code contributions.

## Getting Started

1. **Fork the repository** and clone your fork locally:

```bash
git clone https://github.com/PraaneshSelvaraj/coffee.tmux.git
cd coffee.tmux
```

2. **Set up your development environment:**

- Install Python 3.10 or higher.
- Install dependencies:

  ```bash
  pip install -r requirements.txt
  ```

- Ensure `tmux` (version 3.0+) and `git` are installed.

3. **Create a new branch for your feature or bugfix:**

```bash
git checkout -b feature/your-feature-name
```

## Code quality

We maintain high code quality standards using automated tools. Please ensure your code passes all checks:

### PEP Standards

This project follows the official Python Enhancement Proposal (PEP) guidelines for style and type hints.

- **PEP 8 – Style Guide for Python Code**  
  Write clear, consistent, and readable code by following the PEP 8 conventions for naming, layout, imports, and formatting.

- **PEP 484 – Type Hints**  
  Use type hints for all function parameters and return values to improve correctness, readability, and tooling support.

- **PEP 585 & PEP 604 – Modern Type Syntax**  
  Prefer modern built‑in generics (for example, `list[str]`, `dict[str, int]`) and the union operator (`str | None`) where supported by Python 3.10+.

All new and updated code is expected to comply with these PEPs, and the formatting and type‑checking tools configured in this repository will enforce them.

### Code Formatting

**Black**: We use Black for consistent code formatting

```bash
black .
```

**isort**: We use isort for import sorting

```bash
isort .
```

### Type Checking

**mypy**: All code must include proper type hints and pass mypy checks

```bash
mypy .
```

- Add type annotations to all function parameters and return types
- Use `from typing import` for complex types (List, Dict, Optional, etc.)

### Running All Checks

Before submitting your PR, run all quality checks:

```bash
# Format code
black .
isort .

# Check types
mypy .
```
Our CI pipeline will automatically run these checks on your PR.

## Coding Guidelines

- Follow Python best practices and write clean, readable code.
- Use meaningful variable and function names.
- Comment your code where appropriate to explain complex logic.
- Maintain consistency with existing code style.
- Use f-strings for string formatting where applicable.

## Testing

- Add tests for any new features or bug fixes.
- Run existing tests to ensure nothing is broken.
- Currently, the project uses manual and functional tests — unit tests are welcome and appreciated!
- Test CLI commands and TUI interaction where relevant.

## Submitting Changes

1. Commit your changes with clear, descriptive messages:

```bash
git commit -m "Add feature X to improve plugin loading"
```

2. Push your branch to your fork:

```bash
git push origin feature/your-feature-name
```

3. Open a Pull Request (PR) to the main repository’s `main` branch.

## Reporting Issues

- Use the GitHub issue tracker.
- Provide a clear, descriptive title and detailed description.
- Include steps to reproduce, your OS, tmux version, Python version, and any relevant logs or error messages.

## Code of Conduct

We expect all contributors to follow the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct.html) to foster an open and welcoming environment.

## Need help?

If you have questions or need guidance, feel free to open an issue or reach out via GitHub discussions.

Thank you for helping make Coffee.tmux better!
