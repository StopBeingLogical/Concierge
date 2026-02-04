#!/bin/bash
# Concierge Setup Script
# One-command initialization for fresh clones

set -e

echo "🚀 Concierge Setup"
echo "=================="
echo ""

# Check Python version
echo "✓ Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.12"

if [[ ! "$PYTHON_VERSION" =~ ^3\.1[2-9] ]]; then
    echo "⚠️  Warning: Python 3.12+ recommended, found $PYTHON_VERSION"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create workspace
WORKSPACE=${1:-.}
echo "✓ Creating workspace at: $WORKSPACE"
mkdir -p "$WORKSPACE"

# Install package in development mode
echo "✓ Installing Concierge in development mode..."
pip install -e . --quiet

# Initialize workspace
echo "✓ Initializing workspace..."
bit init "$WORKSPACE"

# Open workspace
bit ws open --path "$WORKSPACE"

# Set default mode
echo "✓ Setting default mode..."
bit mode set --name code

# Validate installation
echo "✓ Validating installation..."
bit ws validate

# Summary
echo ""
echo "✅ Setup Complete!"
echo ""
echo "Next steps:"
echo "  1. Open workspace:   bit ws open --path $WORKSPACE"
echo "  2. Set your mode:    bit mode set --name <mode>"
echo "  3. Try first intent: bit intent synth --text 'Your intent here'"
echo "  4. See QUICKREF.md for commands"
echo ""
echo "Learn more:"
echo "  • INDEX.md - Navigation guide"
echo "  • QUICKREF.md - One-page cheat sheet"
echo "  • docs/examples/README.md - Workflow examples"
echo ""
