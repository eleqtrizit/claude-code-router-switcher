# Claude Code Router Switcher

A CLI tool for managing Claude Code Router configuration. Switch between different AI models and providers for various router types (default, background, think, longContext, webSearch) with a simple command-line interface.

## Features

- List all available models grouped by provider
- View current router configuration
- Change router settings for different use cases
- Add and manage providers and models
- Auto-detect provider when model name is unique

## Development Setup

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd claude-code-router-switcher
```

2. Re/Install the package in development mode:
```bash
make install
```

### Running the CLI

Run in development mode without installation:
```bash
make dev
```

### Development Commands

- `make test` - Run tests
- `make lint` - Run linters (flake8, mypy)
- `make format` - Format code with autopep8
- `make clean` - Clean build artifacts

### Usage

```bash
# List all models
ccs ls

# Show current router configuration
ccs show

# Change a router setting
ccs change default anthropic,claude-3-5-sonnet-20241022

# Add a provider
ccs add provider --name myprovider --base-url https://api.example.com --api-key YOUR_KEY

# Add a model to a provider
ccs add model myprovider my-model-name

# Delete a provider (with confirmation)
ccs delete provider myprovider

# Delete a model (with confirmation)
ccs delete model my-model-name
```

