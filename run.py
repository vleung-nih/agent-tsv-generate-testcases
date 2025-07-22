#!/usr/bin/env python3
"""
Simple runner script for the Autonomous UI Validator.
This script makes it easy to run the program from the project root.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

if __name__ == "__main__":
    # Import and run the main function from run_agent
    from run_agent import main
    main() 