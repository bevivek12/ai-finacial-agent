"""Setup script to initialize the AI Financial Agent project."""

import os
import sys
from pathlib import Path


def create_directories():
    """Create necessary directories if they don't exist."""
    directories = [
        "logs",
        "output",
        "data/sample_pdfs",
        "templates/word",
        "templates/excel",
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {directory}")


def create_env_file():
    """Create .env file from template if it doesn't exist."""
    env_template = Path(".env.template")
    env_file = Path(".env")
    
    if not env_file.exists() and env_template.exists():
        with open(env_template, "r") as f:
            content = f.read()
        
        with open(env_file, "w") as f:
            f.write(content)
        
        print("✓ Created .env file from template")
        print("  ⚠ Please edit .env and add your API keys")
    elif env_file.exists():
        print("✓ .env file already exists")
    else:
        print("✗ .env.template not found")


def check_python_version():
    """Check if Python version is 3.10 or higher."""
    if sys.version_info < (3, 10):
        print("✗ Python 3.10 or higher is required")
        print(f"  Current version: {sys.version}")
        return False
    
    print(f"✓ Python version: {sys.version.split()[0]}")
    return True


def main():
    """Run setup tasks."""
    print("=" * 60)
    print("AI Financial Agent - Setup")
    print("=" * 60)
    print()
    
    # Check Python version
    print("Checking Python version...")
    if not check_python_version():
        sys.exit(1)
    print()
    
    # Create directories
    print("Creating directories...")
    create_directories()
    print()
    
    # Create .env file
    print("Setting up environment variables...")
    create_env_file()
    print()
    
    # Instructions
    print("=" * 60)
    print("Setup complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Install dependencies:")
    print("   pip install -r requirements.txt")
    print()
    print("2. Configure your API keys:")
    print("   Edit .env and add your OPENAI_API_KEY")
    print()
    print("3. Review configuration:")
    print("   Edit config/config.yaml if needed")
    print()
    print("4. Read the documentation:")
    print("   - README.md for overview")
    print("   - IMPLEMENTATION_ROADMAP.md for next steps")
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
