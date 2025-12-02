#!/bin/bash

# Find the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Define the full path to the Python executable
PYTHON_EXE="/usr/bin/python3" 

# Define the path to your main viewer script
VIEWER_SCRIPT="$DIR/miniviewer.py"

# Check if an argument ($1) was passed (i.e., if a file was dropped)
if [ -z "$1" ]; then
    echo " MiniViewer Launcher: Drag a file or folder onto this script/launcher to open it."
    exit 0
fi

# Execute the Python script, passing the first argument (the dropped file/folder path)
# The path is quoted ("$1") to handle spaces in filenames correctly.
"$PYTHON_EXE" "$VIEWER_SCRIPT" "$1"