# NVIDIA cuOpt Example Notebooks

Welcome to the NVIDIA cuOpt example notebooks repository! This collection of notebooks demonstrates how to use NVIDIA cuOpt for various optimization problems across different industries and workflows.

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
```

## Available Examples

### Finance
- **Portfolio Optimization**: Demonstrates portfolio optimization using NVIDIA cuOpt SDK for efficient financial portfolio optimization.

### Last Mile Delivery
- **Vehicle Routing**: Shows how to solve Vehicle Routing Problems (VRP) using NVIDIA cuOpt SDK for optimizing delivery routes.

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

General requirements for all notebooks:
- NVIDIA GPU with appropriate drivers
- CUDA 11.8+
- Python 3.8+
- Jupyter Notebook

Specific requirements are listed in each workflow's README.md and requirements.txt files.

## Contributing

We welcome contributions! Please see the main repository's CONTRIBUTING.md file for guidelines on how to contribute new examples or improve existing ones. 
