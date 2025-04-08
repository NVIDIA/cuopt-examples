#!/bin/bash

# Colors for better visibility
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}NVIDIA cuOpt Resources Repository Structure${NC}\n"

# Function to print directory structure
print_structure() {
    local path=$1
    local prefix=$2
    
    for item in "$path"/*; do
        if [ -d "$item" ]; then
            local dirname=$(basename "$item")
            echo -e "${prefix}${GREEN}📁 $dirname/${NC}"
            print_structure "$item" "$prefix  "
        elif [ -f "$item" ] && [[ "$item" == *.ipynb ]]; then
            echo -e "${prefix}${BLUE}📓 $(basename "$item")${NC}"
        fi
    done
}

# Print main structure
echo "Repository Contents:"
print_structure "." ""

echo -e "\n${BLUE}Repository Structure:${NC}"
echo "Each use case directory contains:"
echo "- Example notebooks demonstrating cuOpt functionality"
echo "- Implementation files and utilities"
echo "- README.md with specific instructions"
echo "- requirements.txt for dependencies"

echo -e "\n${BLUE}Getting Started:${NC}"
echo "1. Make sure you have Docker and NVIDIA Container Toolkit installed"
echo "2. Run 'docker-compose up' to start the Jupyter notebook environment"
echo "3. Open your browser at http://localhost:8888"
echo "4. Explore the example notebooks in their respective use case directories" 
