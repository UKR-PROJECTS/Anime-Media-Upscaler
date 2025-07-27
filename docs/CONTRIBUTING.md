# Contributing to Sharpify GUI

Thank you for your interest in contributing to Sharpify GUI! We welcome contributions from everyone and appreciate your help in making this PyQt6-based media upscaler better for the community.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Issue Guidelines](#issue-guidelines)
- [Community](#community)

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to [ujjwalkrai@gmail.com](mailto:ujjwalkrai@gmail.com).

## Getting Started

### Prerequisites

Before you begin, ensure you have the following:
- A GitHub account
- Git installed on your local machine
- Python 3.8 or higher
- Basic knowledge of PyQt6 and GUI development.
- Understanding of Real-ESRGAN and FFmpeg.

### First Time Setup

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/your-username/sharpify-gui.git
   cd sharpify-gui
   ```
3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/uikraft-hub/sharpify-gui.git
   ```
4. Review the project structure:
```
sharpify-gui/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── workflows/
│       └── ci.yml
├── .gitignore
├── assets/
│   ├── example/
│   │   ├── pikachu_upscaled_x4.jpg
│   │   └── pikachu.jpg
│   ├── screenshots/
│   │   └── screenshot.png
│   └── sharpify-gui-logo.ico
├── docs/
│   ├── CHANGELOG.md
│   ├── CODE_OF_CONDUCT.md
│   ├── CONTRIBUTING.md
│   ├── README.md
│   ├── SECURITY.md
│   ├── STATUS.md
│   └── USAGE.md
├── LICENSE
├── pyproject.toml
├── requirements.txt
├── src/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main_window.py
│   │   ├── settings_dialog.py
│   │   ├── ui_utils.py
│   │   └── workers.py
│   ├── bin/
│   │   ├── ffmpeg.exe
│   │   └── realesrgan-ncnn-vulkan.exe
│   ├── build.bat
│   ├── favicon.ico
│   ├── main.py
│   └── models/
│       ├── realesr-animevideov3-x4.bin
│       ├── realesr-animevideov3-x4.param
│       ├── realesrgan-x4plus-anime.bin
│       ├── realesrgan-x4plus-anime.param
│       ├── realesrgan-x4plus.bin
│       └── realesrgan-x4plus.param
└── tests/
    └── test_workers.py
```

5. Install the project in development mode:
   ```bash
   pip install -e .
   ```

## How to Contribute

### Types of Contributions

We welcome several types of contributions:

- **Core Functionality**: Enhance upscaling capabilities and features.
- **UI/UX Improvements**: Improve the PyQt6 interface and user experience.
- **Performance Optimization**: Optimize upscaling speed, memory usage, and concurrency.
- **Error Handling**: Improve error handling and user feedback mechanisms.
- **Testing**: Add comprehensive tests for upscaling and GUI functionality.
- **Documentation**: Improve guides, API documentation, and usage examples.
- **Bug Reports**: Help us identify and fix upscaling or GUI issues.
- **Feature Requests**: Suggest new features or improvements.

### Before You Start

1. Check existing [issues](https://github.com/uikraft-hub/sharpify-gui/issues) and [pull requests](https://github.com/uikraft-hub/sharpify-gui/pulls) to avoid duplicates
2. For major changes or new features, please open an issue first to discuss your proposed changes.
3. Make sure your contribution aligns with the project's goal of providing a reliable media upscaler.

## Development Setup

### Local Development Environment

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

3. Install development dependencies:
   ```bash
   pip install pytest pytest-cov black flake8 mypy
   ```

4. Create a new branch for your feature or improvement:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/upscaling-issue-description
   # or
   git checkout -b ui/interface-improvement
   ```

### Running the Application

1.  Navigate to the `src` directory:
    ```bash
    cd src
    ```
2.  Run the application:
    ```bash
    python main.py
    ```

### Development Tools

- **Code Formatting**: Use `black` for consistent code formatting.
- **Linting**: Use `flake8` for code quality checks.
- **Type Checking**: Use `mypy` for static type analysis.
- **Testing**: Use `pytest` for running tests.

## Coding Standards

### General Guidelines

- Write clean, readable, and well-documented Python code.
- Follow PEP 8 style guidelines with Black formatting.
- Use type hints for function parameters and return values.
- Handle errors gracefully with proper exception handling.
- Log important events and errors for debugging.

### Python Standards

#### Code Style
- Use Black for automatic code formatting.
- Maximum line length: 88 characters (Black default).
- Use meaningful variable and function names.
- Add docstrings for all public functions and classes.
- Follow PEP 8 naming conventions.

#### Architecture Guidelines
- Separate concerns: UI logic in `main_window.py` and `settings_dialog.py`, upscaling logic in `workers.py`.
- Use utility functions in `ui_utils.py` for common operations.
- Keep the main application entry point clean in `main.py`.
- Implement proper error handling and user feedback.

### PyQt6 UI Guidelines

- **Responsive Design**: Ensure UI works on different screen sizes.
- **Progress Feedback**: Show progress for long-running operations.
- **Error Messages**: Display clear, actionable error messages.
- **Input Validation**: Validate user input before processing.
- **State Management**: Use `QSettings` for persistent settings.

## Testing Guidelines

### Test Structure

Tests are located in the `tests/` directory.

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_workers.py

# Run tests with verbose output
pytest -v
```

### Test Guidelines

- Write tests for all new functionality.
- Test both success and failure scenarios.
- Mock external processes like `realesrgan-ncnn-vulkan.exe` and `ffmpeg.exe`.
- Maintain test coverage above 80%.

## Commit Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification for commit messages.

### Commit Message Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types

- `feat`: A new feature (upscaling capability, UI improvement)
- `fix`: A bug fix (upscaling error, UI issue)
- `perf`: Performance improvements (faster upscaling, memory optimization)
- `refactor`: Code refactoring without changing functionality
- `test`: Adding or updating tests
- `docs`: Documentation only changes
- `style`: Code style changes (formatting, etc.)
- `chore`: Maintenance tasks and dependency updates

### Scopes (Optional)

- `upscaler`: Changes to upscaling functionality
- `ui`: PyQt6 interface changes
- `worker`: Upscaling worker changes
- `utils`: Utility functions
- `tests`: Test-related changes
- `docs`: Documentation changes

### Examples

```
feat(upscaler): add support for a new upscaling model

fix(ui): resolve progress bar not updating during batch processing

perf(worker): optimize video frame extraction

docs: update usage examples with new file formats

test(worker): add comprehensive tests for video upscaling
```

## Pull Request Process

### Before Submitting

1. Ensure your branch is up to date with the main branch:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. Run the full test suite:
   ```bash
   pytest
   ```

3. Check code formatting and linting:
   ```bash
   black src/ tests/
   flake8 src/ tests/
   mypy src/
   ```

4. Test the application manually.

5. Update documentation if necessary.

### Submitting Your Pull Request

1. Push your branch to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. Create a pull request from your fork to the main repository.

3. Fill out the pull request template completely.

### Pull Request Checklist

- [ ] Code follows the project's coding standards.
- [ ] Tests pass locally and cover new functionality.
- [ ] Documentation has been updated (if applicable).
- [ ] Commit messages follow conventional commit format.
- [ ] No breaking changes (or breaking changes are documented).
- [ ] Performance impact has been considered.
- [ ] Error handling has been implemented appropriately.

## Issue Guidelines

### Before Creating an Issue

1. Search existing issues to avoid duplicates.
2. Test with the latest version of the application.
3. Gather relevant information (error messages, screenshots).
4. Try to reproduce the issue consistently.

### Bug Reports

When reporting a bug, please include:

- **Bug Description**: Clear and concise description of the issue.
- **Steps to Reproduce**: Detailed steps to reproduce the issue.
- **Expected Behavior**: What should happen.
- **Actual Behavior**: What actually happens.
- **Error Messages**: Any error messages or logs.
- **Environment**: Operating system, Python version.
- **Screenshots**: UI screenshots showing the issue.

### Feature Requests

When requesting a new feature, please include:

- **Feature Description**: Clear description of the proposed feature.
- **Use Case**: Why is this feature needed? What problem does it solve?
- **Proposed Implementation**: Your ideas for how this could be implemented.

## Community

### Getting Help

If you need help or have questions:

- Open an issue with the "question" label.
- Email us at [ujjwalkrai@gmail.com](mailto:ujjwalkrai@gmail.com).
- Check existing documentation in the `docs/` folder.
- Review the [USAGE.md](USAGE.md) for detailed usage instructions.

## License

By contributing to this project, you agree that your contributions will be licensed under the MIT License, the same license as the project. See [LICENSE](../LICENSE) for details.
