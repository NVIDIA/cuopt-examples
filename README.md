# cuOpt Resources
NVIDIA cuOpt is an accelerated Operations Research optimization API to help developers create complex, real-time fleet routing workflows on NVIDIA GPUs.
This repository contains a collection of examples demonstrating use of NVIDIA cuOpt via service APIs and SDK. 

The cuOpt-Resources repository is under [Apache 2.0 License](LICENSE.md)

[cuOpt Docs](https://docs.nvidia.com/cuopt/)

## Quick Start with Docker

The easiest way to get started with these examples is using our Docker container, which comes with all the necessary dependencies pre-installed.

### Prerequisites
- Docker
- NVIDIA Container Toolkit
- NVIDIA GPU with appropriate drivers

### Running the Examples
1. Clone this repository:
```bash
git clone https://github.com/NVIDIA/cuOpt-Resources.git
cd cuOpt-Resources
```

2. Start the Jupyter notebook environment:
```bash
docker-compose up
```

3. Open your browser at http://localhost:8888 to access the notebooks

## Notebook Naming Convention

All notebooks in this repository follow a consistent naming convention based on their directory structure. The naming pattern is:

```
<directory_abbreviation>_<subdirectory_abbreviation>_<notebook_name>.ipynb
```

Directory abbreviations:
- `RT` - Routing
- `MGD_SRVC` - Managed Service
- `ONP_SRVC` - On-Premises Service
- `FIN` - Finance
- `LMD` - Last Mile Delivery
- `nbutils` - Notebook Utils
- `VRP` - Vehicle Routing
- `PORTFOLIO_OPT` - Portfolio Optimization

Example:
- A notebook in `routing/managed_service/example.ipynb` would be renamed to `RT_MGD_SRVC_example.ipynb`
- A notebook in `Finance/Portfolio_Optimization/optimization.ipynb` would be renamed to `FIN_PORTFOLIO_OPT_optimization.ipynb`

## Repository Structure

To explore the repository structure, run:
```bash
./explore.sh
```

This will show you a tree view of all notebooks and directories in the repository.

## Contents
* NVIDIA cuOpt managed service example notebooks
  * [Routing Optimization](notebooks/routing/) 
* NVIDIA cuOpt Examples and Workflows
  * [Finance](notebooks-contrib/Finance/)
  * [Last Mile Delivery](notebooks-contrib/Last_Mile_Delivery/)

## Requirements

For detailed system requirements, please refer to the [NVIDIA cuOpt System Requirements documentation](https://docs.nvidia.com/cuopt/user-guide/latest/system-requirements.html#).

Specific requirements are listed in each workflow's README.md and requirements.txt files.

## Contributing

We welcome contributions! Please see the main repository's CONTRIBUTING.md file for guidelines on how to contribute new examples or improve existing ones. 
