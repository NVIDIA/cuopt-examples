# cuOpt Resources
NVIDIA cuOpt is an accelerated Operations Research optimization API to help developers create complex, real-time fleet routing workflows on NVIDIA GPUs.
This repository contains a collection of examples demonstrating use of NVIDIA cuOpt via service APIs and SDK. 

The cuOpt-Resources repository is under [MIT License](LICENSE.md)

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

The repository is organized by use cases, with each directory containing examples and implementations specific to that use case. Each use case directory includes:
- Example notebooks
- Implementation files
- README.md with specific instructions
- requirements.txt for dependencies

## Featured Examples

### Intra-Factory Transport Optimization
The `intra-factory_transport` directory contains an example of using the cuOpt SDK API to solve a Capacitated Pickup and Delivery Problem with Time Windows (CPDPTW) for optimizing routes of Autonomous Mobile Robots (AMRs) within a factory environment.

## Contents
* NVIDIA cuOpt Examples and Workflows
  * [Intra-Factory Transport](intra-factory_transport/)

## Requirements

For detailed system requirements, please refer to the [NVIDIA cuOpt System Requirements documentation](https://docs.nvidia.com/cuopt/user-guide/latest/system-requirements.html#).

Specific requirements are listed in each workflow's README.md and requirements.txt files.

## Contributing

We welcome contributions! Please see the main repository's CONTRIBUTING.md file for guidelines on how to contribute new examples or improve existing ones. 
