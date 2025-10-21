# cuOpt Examples
NVIDIA cuOpt is a GPU-accelerated combinatorial and linear optimization engine for solving complex route optimization problems such as Vehicle Routing and large Linear Programming problems.
This repository contains a collection of examples demonstrating use of NVIDIA cuOpt via service APIs, SDK and Integration with other OSS optimization solvers. 

This repository is under [MIT License](LICENSE.md)

[cuOpt Docs](https://docs.nvidia.com/cuopt/)

## Quick Start with Docker

The easiest way to get started with these examples is using cuOpt docker image.

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

2. Pull the cuOpt docker image:

For cuda-13:

```bash
docker pull nvidia/cuopt:25.10.0-cuda13.0-py3.13
```

For cuda-12
```bash
docker pull nvidia/cuopt:25.10.0-cuda12.9-py3.13
```

3. Run the examples:

For cuda-13:
```bash
docker run -it --rm --gpus all --network=host -v $(pwd):/workspace -w /workspace nvidia/cuopt:25.10.0-cuda13.0-py3.13 /bin/bash -c "pip install -r requirements.txt; jupyter-notebook"
```

For cuda-12:
```bash
docker run -it --rm --gpus all --network=host -v $(pwd):/workspace -w /workspace nvidia/cuopt:25.10.0-cuda12.9-py3.13 /bin/bash -c "pip install -r requirements.txt; jupyter-notebook"
```

4. Open your browser with the link provided in the terminal, and you can see the notebooks.


## Note

These notebooks have been tested on [NVIDIA Launchable](https://brev.nvidia.com/launchable/deploy?launchableID=env-2qIG6yjGKDtdMSjXHcuZX12mDNJ), [Google Colab](https://colab.research.google.com/github/NVIDIA/cuopt-examples/blob/cuopt_examples_launcher/cuopt_examples_launcher.ipynb), and local Jupyter environments. They may work on other platforms as well.


## Repository Structure

The repository is organized by use cases, with each directory containing examples and implementations specific to that use case. Each use case directory includes:
- Example notebooks
- README.md with specific instructions

## Featured Examples

### Intra-Factory Transport Optimization
The `intra-factory_transport` directory contains an example of using the cuOpt SDK API to solve a Capacitated Pickup and Delivery Problem with Time Windows (CPDPTW) for optimizing routes of Autonomous Mobile Robots (AMRs) within a factory environment.

## Contributing

We welcome contributions! Please see our [CONTRIBUTING.md](CONTRIBUTING.md) file for guidelines on how to contribute new examples or improve existing ones.

## Tutorial Videos

[Example videos](https://docs.nvidia.com/cuopt/user-guide/latest/resources.html#cuopt-examples-and-tutorials-videos) can be found listed in the documentation 
