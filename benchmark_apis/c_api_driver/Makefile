# Makefile for cuOpt JSON to C API
# This builds a C program that reads cuOpt JSON files and solves them using the C API

# Default compiler
CC = gcc

# Default flags
CFLAGS = -Wall -Wextra -O2 -std=c99

# Program name
PROGRAM = cuopt_json_to_c_api

# Source files
SOURCES = cuopt_json_to_c_api.c

# Object files
OBJECTS = $(SOURCES:.c=.o)

# Default target
all: $(PROGRAM)

# Build the program
$(PROGRAM): $(OBJECTS)
	$(CC) $(OBJECTS) $(LDFLAGS) -o $(PROGRAM) $(LIBS)

# Compile source files
%.o: %.c
	$(CC) $(CFLAGS) $(INCLUDES) -c $< -o $@

# Clean build artifacts
clean:
	rm -f $(OBJECTS) $(PROGRAM)

# Clean and rebuild
rebuild: clean all

# Install dependencies (Ubuntu/Debian)
install-deps:
	sudo apt-get update
	sudo apt-get install -y libcjson-dev

# Help target
help:
	@echo "cuOpt JSON to C API Makefile"
	@echo "============================"
	@echo ""
	@echo "Targets:"
	@echo "  all         - Build the program (default)"
	@echo "  clean       - Remove build artifacts"
	@echo "  rebuild     - Clean and rebuild"
	@echo "  install-deps- Install dependencies (Ubuntu/Debian)"
	@echo "  help        - Show this help"
	@echo ""
	@echo "Variables you may need to set:"
	@echo "  CUOPT_INCLUDE_PATH  - Path to cuOpt include directory"
	@echo "  CUOPT_LIBRARY_PATH  - Path to cuOpt library directory"
	@echo "  CONDA_ENV          - Name of conda environment to search in"
	@echo ""
	@echo "Example usage:"
	@echo "  # If cuOpt is installed in system paths:"
	@echo "  make"
	@echo ""
	@echo "  # If cuOpt is built locally you can use absolute or relative paths:"
	@echo "  make CUOPT_INCLUDE_PATH=../cpp/include CUOPT_LIBRARY_PATH=../cpp/build"
	@echo ""
	@echo "  # To search for a specific conda environment (under miniforge3):"
	@echo "  make CONDA_ENV=cuopt_dev"
	@echo ""
	@echo "  # Custom compiler or flags:"
	@echo "  make CC=clang CFLAGS=\"-O3 -g\""

# Set up include and library paths
ifdef CUOPT_INCLUDE_PATH
    INCLUDES += -I$(CUOPT_INCLUDE_PATH)
endif

ifdef CUOPT_LIBRARY_PATH
    LDFLAGS += -L$(CUOPT_LIBRARY_PATH)
endif

# Add cJSON flags if available
CJSON_CFLAGS := $(shell pkg-config --cflags libcjson 2>/dev/null)
CJSON_LIBS := $(shell pkg-config --libs libcjson 2>/dev/null)

ifneq ($(CJSON_CFLAGS),)
    CFLAGS += $(CJSON_CFLAGS)
endif

# Default library paths (try common system locations)
ifneq ($(CJSON_LIBS),)
    LIBS = -lcuopt $(CJSON_LIBS) -lm
else
    LIBS = -lcuopt -lcjson -lm
endif

# Auto-detect cuOpt paths if not specified (skip for clean targets)
ifeq ($(filter clean,$(MAKECMDGOALS)),)
ifndef CUOPT_INCLUDE_PATH
    # Search order: specific conda env (if set), current conda env, other conda envs, local build, system paths
    ifdef CONDA_ENV
        SPECIFIC_CONDA_PATH := $(HOME)/miniforge3/envs/$(CONDA_ENV)
        $(info Searching in specified conda environment: $(CONDA_ENV))
        SEARCH_PATHS := $(SPECIFIC_CONDA_PATH) $(CONDA_PREFIX) $(HOME)/miniforge3/envs /usr/include /usr/local/include ..
    else
        SEARCH_PATHS := $(CONDA_PREFIX) $(HOME)/miniforge3/envs /usr/include /usr/local/include ..
    endif
    CUOPT_HEADER_SEARCH := $(shell for path in $(SEARCH_PATHS); do find "$$path" -name "cuopt_c.h" -path "*/linear_programming/*" 2>/dev/null | head -1; done | head -1)
    ifneq ($(CUOPT_HEADER_SEARCH),)
        CUOPT_INCLUDE_DIR := $(shell dirname $(shell dirname $(shell dirname $(CUOPT_HEADER_SEARCH))))
        INCLUDES += -I$(CUOPT_INCLUDE_DIR)
        $(info Found cuOpt headers at: $(CUOPT_INCLUDE_DIR))
    endif
endif

ifndef CUOPT_LIBRARY_PATH
    # Search order: specific conda env (if set), current conda env, other conda envs, local build, system paths
    ifdef CONDA_ENV
        SPECIFIC_CONDA_LIB_PATH := $(HOME)/miniforge3/envs/$(CONDA_ENV)/lib
        SEARCH_PATHS := $(SPECIFIC_CONDA_LIB_PATH) $(CONDA_PREFIX)/lib $(HOME)/miniforge3/envs /usr/lib /usr/local/lib /usr/lib64 /usr/local/lib64 ../cpp/build
    else
        SEARCH_PATHS := $(CONDA_PREFIX)/lib $(HOME)/miniforge3/envs /usr/lib /usr/local/lib /usr/lib64 /usr/local/lib64 ../cpp/build
    endif
    CUOPT_LIBRARY_SEARCH := $(shell for path in $(SEARCH_PATHS); do find "$$path" -name "libcuopt.so" 2>/dev/null | head -1; done | head -1)
    ifneq ($(CUOPT_LIBRARY_SEARCH),)
        CUOPT_LIB_DIR := $(shell dirname $(CUOPT_LIBRARY_SEARCH))
        LDFLAGS += -L$(CUOPT_LIB_DIR)
        $(info Found cuOpt library at: $(CUOPT_LIB_DIR))
    endif
endif
endif

# Debug target
debug: CFLAGS += -g -DDEBUG
debug: $(PROGRAM)

# Print variables for debugging
print-vars:
	@echo "CC = $(CC)"
	@echo "CFLAGS = $(CFLAGS)"
	@echo "INCLUDES = $(INCLUDES)"
	@echo "LDFLAGS = $(LDFLAGS)"
	@echo "LIBS = $(LIBS)"
	@echo "SOURCES = $(SOURCES)"
	@echo "OBJECTS = $(OBJECTS)"
	@echo "CONDA_ENV = $(CONDA_ENV)"
	@echo "CONDA_PREFIX = $(CONDA_PREFIX)"

.PHONY: all clean rebuild install-deps help debug print-vars 
