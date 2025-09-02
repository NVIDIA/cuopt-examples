# Build Guide for cuOpt JSON to C API

This guide addresses the common build issues when working with conda environments and provides reliable build solutions.

## The Problem

When building inside conda environments, you may encounter:
```
ld: cannot find -lcjson: No such file or directory
```

This occurs because:
- Conda environments use isolated toolchains
- The `libcjson` library is not available in most conda channels
- System libraries like `libcjson-dev` are not accessible from within conda

## ✅ **Solution**

```bash
# Deactivate conda env if activate and build with system libraries
conda deactivate
make clean && make

# To run set the LD_LIBRARY_PATH to find libcuopt.so
export LD_LIBRARY_PATH=$(HOME)/miniforge3/envs/cuopt_dev/lib:$LD_LIBRARY_PATH
./cuopt_json_to_c_api your_problem.json
```

## Prerequisites

Make sure you have the required system dependencies:
```bash
sudo apt-get update
sudo apt-get install build-essential libcjson-dev
```

Or use the Makefile target:
```bash
make install-deps
```
