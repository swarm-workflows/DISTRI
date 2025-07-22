#!/bin/bash
# Activation script for DISTRI virtual environment

echo "Activating DISTRI virtual environment..."
source venv/bin/activate

echo "Virtual environment activated!"
echo "You can now run the simulator with: python main.py [options]"
echo "To see all available options: python main.py --help"
echo "To deactivate when done: deactivate" 