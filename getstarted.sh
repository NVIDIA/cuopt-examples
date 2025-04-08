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
            # Check if it's a template directory
            if [[ "$dirname" == TEMPLATE_* ]]; then
                echo -e "${prefix}${YELLOW}📁 $dirname/ (Template)${NC}"
            else
                echo -e "${prefix}${GREEN}📁 $dirname/${NC}"
            fi
            print_structure "$item" "$prefix  "
        elif [ -f "$item" ] && [[ "$item" == *.ipynb ]]; then
            echo -e "${prefix}${BLUE}📓 $(basename "$item")${NC}"
        fi
    done
}

# Print main structure
echo "Repository Contents:"
print_structure "." ""

echo -e "\n${BLUE}Directory Naming Convention:${NC}"
echo "- Verticals: INT_FAC (Intra Factory), LMD (Last Mile Delivery), DIS (Dispatch), PDP (Pickup and Delivery), FIN (Financial)"
echo "- Implementation: SER (Service API), PY (Python SDK)"
echo "- Example: PDP_SER (Pickup and Delivery using Service API)"

echo -e "\n${BLUE}Getting Started:${NC}"
echo "1. Make sure you have Docker and NVIDIA Container Toolkit installed"
echo "2. Run 'docker-compose up' to start the Jupyter notebook environment"
echo "3. Open your browser at http://localhost:8888"
echo "4. Explore examples in the root directory" 
