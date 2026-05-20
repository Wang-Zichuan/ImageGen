# Contributing to ImageGen

Thanks for your interest in contributing! Here are a few guidelines:

## Getting Started

1. Fork the repository
2. Run `setup.bat` (Windows) or `uv sync` (any OS) to set up your environment
3. Copy `config.example.json` to `config.json` and fill in your API key
4. Create a feature branch: `git checkout -b my-feature`

## Development

```bash
# Install in editable mode
uv pip install -e .

# Run the app
uv run streamlit run imagegen/app.py

# Run linting (if configured)
uv run ruff check imagegen/
```

## Submitting Changes

1. Make your changes on a feature branch
2. Ensure no config files with secrets are included
3. Write clear commit messages
4. Open a Pull Request describing the change

## Reporting Issues

- Use GitHub Issues
- Include steps to reproduce
- Mention your OS, Python version, and error output

## Code Style

- Follow PEP 8
- Use type hints where practical
- Keep functions focused and small

Thank you!