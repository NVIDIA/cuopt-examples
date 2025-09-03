# cuOpt Benchmark APIs

This directory contains benchmark scripts that compare cuOpt performance across different modeling frameworks and APIs.

## Installation

### cuOpt
Install cuOpt by following the instructions at [github.com/NVIDIA/cuopt](https://github.com/NVIDIA/cuopt). This installs both the C and Python APIs along with cuOpt itself.

### Modeling Frameworks

- **Python API**: No additional installation needed (included with cuOpt)
- **C API**: No additional installation needed, but requires building the C program - see build instructions in the `c_api_driver/` subdirectory
- **CVXPY**: [https://www.cvxpy.org/install/index.html](https://www.cvxpy.org/install/index.html)
- **AMPL**: [https://dev.ampl.com/solvers/cuopt/index.html](https://dev.ampl.com/solvers/cuopt/index.html)
- **PuLP**: [https://coin-or.github.io/pulp/main/installing_pulp_at_home.html](https://coin-or.github.io/pulp/main/installing_pulp_at_home.html)
- **GAMS**: [https://www.gams.com/download/](https://www.gams.com/download/), [https://gamspy.readthedocs.io/en/latest/user/installation.html](https://gamspy.readthedocs.io/en/latest/user/installation.html), and the GAMS/cuOpt link from [https://github.com/GAMS-dev/cuoptlink-builder](https://github.com/GAMS-dev/cuoptlink-builder)
- **Julia**: 
  - [https://julialang.org/install/](https://julialang.org/install/)
  - [https://jump.dev/JuMP.jl/stable/installation/](https://jump.dev/JuMP.jl/stable/installation/)
  - [https://jump.dev/JuMP.jl/stable/packages/cuOpt/](https://jump.dev/JuMP.jl/stable/packages/cuOpt/)

### Environment Setup
For C and Julia APIs, set the library path:
```bash
export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH
```

## Usage

### Running Benchmarks
Use `benchmark_cuopt.py` to run performance comparisons across different APIs. Run with `--help` for detailed options.

### Analyzing Results  
Use `analyze_benchmark_results.py` to process and analyze benchmark output. Run with `--help` for available analysis options.

### Individual API Scripts
Each `cuopt_json_to_*.py` and `cuopt_json_to_*.jl` script can be run individually. Use `--help` or check the script documentation for usage details.

## Data Preparation

### Converting MPS Files to cuOpt JSON
Use the `transform.py` utility to convert MPS files to cuOpt JSON format for input to the benchmark scripts:

```bash
python transform.py problem.mps
```

This will create `problem.json` in cuOpt JSON format. Run `python transform.py --help` for available options and usage details.
