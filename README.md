# cuOpt Examples
NVIDIA cuOpt is a GPU-accelerated combinatorial and linear optimization engine for solving complex route optimization problems such as Vehicle Routing and large Linear Programming problems.
This repository contains a collection of examples demonstrating use of NVIDIA cuOpt via service APIs, SDK and Integration with other OSS optimization solvers. 

The cuOpt-Resources repository is under [MIT License](LICENSE.md)

[cuOpt Docs](https://docs.nvidia.com/cuopt/)

## Quick Start with Docker

The easiest way to get started with these examples is using the included Docker container, which comes with all the necessary dependencies pre-installed.

### Prerequisites
- [Docker](https://docs.nvidia.com/ai-enterprise/deployment/vmware/latest/docker.html)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html#installing-the-nvidia-container-toolkit)
- NVIDIA GPU with appropriate drivers

## Requirements

For detailed system requirements, please refer to the [NVIDIA cuOpt System Requirements documentation](https://docs.nvidia.com/cuopt/user-guide/latest/system-requirements.html#).

Specific requirements are listed in each workflow's README.md and in the root directory's requirements.txt files.

### Running the Examples
1. Clone this repository:
```bash
git clone https://github.com/NVIDIA/cuopt-examples.git
cd cuopt-examples
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
- requirements.txt for any additional dependencies that this notebook may require

## Featured Examples

### Intra-Factory Transport Optimization
The `intra-factory_transport` directory contains an example of using the cuOpt SDK API to solve a Capacitated Pickup and Delivery Problem with Time Windows (CPDPTW) for optimizing routes of Autonomous Mobile Robots (AMRs) within a factory environment.

## Contributing

We welcome contributions! Please see our [CONTRIBUTING.md](CONTRIBUTING.md) file for guidelines on how to contribute new examples or improve existing ones.
