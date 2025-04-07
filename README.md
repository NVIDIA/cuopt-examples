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
