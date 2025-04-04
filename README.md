# cuOpt Resources
NVIDIA cuOpt is an accelerated Operations Research optimization API to help developers create complex, real-time fleet routing workflows on NVIDIA GPUs.
This repository contains a collection of examples demonstrating use of NVIDIA cuOpt via service APIs and SDK. 


The cuOpt-Resources repository is under [Apache 2.0 License](LICENSE.md)

 [cuOpt Docs](https://docs.nvidia.com/cuopt/)

## Contents
* NVIDIA cuOpt managed service example notebooks
  * [Routing Optimization](notebooks/routing/) 
# NVIDIA cuOpt Examples and Workflows

Welcome to the cuOpt example notebooks repository! This collection of notebooks demonstrates how to use NVIDIA cuOpt for various optimization problems across different industries and workflows.

## Repository Structure

```
notebooks-contrib/
├── Finance/
│   └── Portfolio_Optimization/
│       ├── README.md
│       ├── requirements.txt
│       └── portfolio_optimization.ipynb
└── Last_Mile_Delivery/
    └── Vehicle_Routing/
        ├── README.md
        ├── requirements.txt
        └── vrp_optimization.ipynb

notebooks/
└── routing/
    ├── managed_service/
    │   └── [managed service examples]
    └── on_prem_service/
        └── [on-premises service examples]
```

## Available Examples

### Finance
- **Portfolio Optimization**: Demonstrates portfolio optimization using cuOpt SDK for efficient frontier computation and risk-return analysis.

### Last Mile Delivery
- **Vehicle Routing**: Shows how to solve Vehicle Routing Problems (VRP) using cuOpt Server API for optimizing delivery routes.

### Routing Examples
- **Managed Service**: Examples demonstrating the use of cuOpt managed service API
- **On-Premises Service**: Examples showing how to use cuOpt on-premises service

## Getting Started

1. Clone this repository:
```bash
git clone https://github.com/NVIDIA/cuopt-examples.git
cd cuopt-examples/notebooks-contrib
```

2. Choose a workflow directory and follow the instructions in its README.md file.

3. Install the required dependencies for the specific workflow:
```bash
cd <workflow_directory>
pip install -r requirements.txt
```

4. Launch Jupyter Notebook:
```bash
jupyter notebook
```

## Requirements

For detailed system requirements, please refer to the [NVIDIA cuOpt System Requirements documentation](https://docs.nvidia.com/cuopt/user-guide/latest/system-requirements.html#).

Specific requirements are listed in each workflow's README.md and requirements.txt files.

## Contributing

We welcome contributions! Please see the main repository's CONTRIBUTING.md file for guidelines on how to contribute new examples or improve existing ones. 
