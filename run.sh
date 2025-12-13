#!/bin/bash
# Quick start script for Coding Agent System

echo "Starting Coding Agent System..."
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null
then
    echo "Error: uv is not installed. Please install it first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo "Error: .env file not found. Please copy .env.example to .env and configure it."
    exit 1
fi

# Run the application
uv run python -m src.main "$@"
