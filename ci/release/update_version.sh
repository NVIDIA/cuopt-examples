#!/bin/bash

set -e

# Parse command line arguments
RUN_CONTEXT=""
NEW_VERSION=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --run-context=*)
            RUN_CONTEXT="${1#*=}"
            shift
            ;;
        --run-context)
            RUN_CONTEXT="$2"
            shift 2
            ;;
        *)
            # If it's not a known option, treat it as the version (positional argument)
            if [[ -z "$NEW_VERSION" ]]; then
                NEW_VERSION="$1"
                shift
            else
                echo "Unknown option: $1"
                echo "Usage: $0 --run-context=main|release VERSION"
                exit 1
            fi
            ;;
    esac
done

# Validate required arguments
if [[ -z "$RUN_CONTEXT" ]]; then
    echo "Error: --run-context is required"
    echo "Usage: $0 --run-context=main|release VERSION"
    exit 1
fi

if [[ -z "$NEW_VERSION" ]]; then
    echo "Error: VERSION is required"
    echo "Usage: $0 --run-context=main|release VERSION"
    exit 1
fi

if [[ "$RUN_CONTEXT" != "main" && "$RUN_CONTEXT" != "release" ]]; then
    echo "Error: --run-context must be either 'main' or 'release'"
    echo "Usage: $0 --run-context=main|release VERSION"
    exit 1
fi

# Validate version format (basic check for X.Y.Z pattern)
if ! [[ "$NEW_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: Invalid version format. Expected format: X.Y.Z (e.g., 26.02.00)"
    exit 1
fi

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION_FILE="$PROJECT_ROOT/VERSION"
README_FILE="$PROJECT_ROOT/README.md"

# Update VERSION file with new version
echo "Updating VERSION file to $NEW_VERSION..."
echo "$NEW_VERSION" > "$VERSION_FILE"
echo "VERSION file updated successfully"

# Use the new version as base version
BASE_VERSION="$NEW_VERSION"

# Determine the container version tag based on run context
if [[ "$RUN_CONTEXT" == "main" ]]; then
    # For pre-release: transform 26.02.00 -> 26.2.0a
    # Remove leading zeros and transform patch version
    IFS='.' read -r MAJOR MINOR PATCH <<< "$BASE_VERSION"
    # Remove leading zeros from minor and patch versions
    MINOR=$((10#$MINOR))
    PATCH=$((10#$PATCH))
    # Remove last digit from patch (e.g., 00 -> 0)
    PATCH_STR=$(printf "%02d" $PATCH)
    PATCH_TRANSFORMED="${PATCH_STR%?}"
    CONTAINER_VERSION="${MAJOR}.${MINOR}.${PATCH_TRANSFORMED}a"
    echo "Building for pre-release (main branch)"
    echo "Base version: $BASE_VERSION"
    echo "Container version: $CONTAINER_VERSION"
elif [[ "$RUN_CONTEXT" == "release" ]]; then
    CONTAINER_VERSION="$BASE_VERSION"
    echo "Building for release"
    echo "Version: $CONTAINER_VERSION"
fi

# Update README.md
if [[ ! -f "$README_FILE" ]]; then
    echo "Warning: README.md not found at $README_FILE"
else
    echo "Updating README.md with version $CONTAINER_VERSION..."
    
    # Create a temporary file
    TMP_FILE=$(mktemp)
    
    # Use sed to replace version patterns in docker commands
    # Pattern matches: nvidia/cuopt:XX.XX.XX-cudaXX.X-pyX.XX or nvidia/cuopt:XX.XX.Xa-cudaXX.X-pyX.XX
    # We need to replace the version part while keeping cuda and python versions
    sed -E "s|nvidia/cuopt:[0-9]+\.[0-9]+\.[0-9]+[a-z]?-cuda|nvidia/cuopt:${CONTAINER_VERSION}-cuda|g" "$README_FILE" > "$TMP_FILE"
    
    # Move the temporary file back to README.md
    mv "$TMP_FILE" "$README_FILE"
    
    echo "README.md updated successfully"
fi

# Summary
echo ""
echo "============================================"
echo "Version Update Summary"
echo "============================================"
echo "Run Context: $RUN_CONTEXT"
echo "Base Version (VERSION file): $BASE_VERSION"
echo "Container Version Tag: $CONTAINER_VERSION"
echo "============================================"

# Display the updated lines from README.md for verification
if [[ -f "$README_FILE" ]]; then
    echo ""
    echo "Updated lines in README.md:"
    grep -n "nvidia/cuopt:" "$README_FILE" || true
fi

echo ""
echo "Update completed successfully!"

