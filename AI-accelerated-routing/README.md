# EARLI: Evolutionary Algorithm with RL Initialization
*a cuOpt‑powered combinatorial optimization framework*

This section demonstrates how to use cuOpt with [EARLI](https://github.com/NVlabs/EARLI), published by NVIDIA as part of the paper [***Accelerating Vehicle Routing via AI-Initialized Genetic Algorithms***](https://arxiv.org/abs/2504.06126).

EARLI is a hybrid framework for solving the Vehicle Routing Problem (VRP). It uses Reinforcement Learning (RL) to learn to quickly generate high-quality solutions; then uses these as the initial population of a Genetic Algorithm (GA). The RL initialization enables leveraging of data for generalization across problems and acceleration of solving new instances. The GA search leverages inference time to refine the solution iteratively. Together, EARLI accelerates the time to find state-of-the-art solutions to VRP instances.

The [EARLI repo](https://github.com/NVlabs/EARLI) integrates EARLI's framework with NVIDIA's cuOpt genetic algorithm solver.
This includes:
* **A parallelisable VRP environment** compatible with both gym and stable-baselines.
* **Training** code from a given data file of problem instances (see [training example notebook](examples/ExampleTrain.ipynb)).
* **Inference** code that generates multiple solutions for a set of given problem instances.
* **Integration to NVIDIA's cuOpt**: the generated solutions are injected to the solver as its initial population (see [inference example notebook](examples/Example.ipynb)).
* Several **pre-trained RL models** are provided, based on synthetic training data.

### Contents
* [Examples](#examples)
   * [Training example notebook](examples/ExampleTrain.ipynb)
   * [Inference example notebook](examples/Example.ipynb)
* [Data](#data)
* [Cite Us](#cite-us)

| <img src="photos/diagram.png" width="480"> |
| :--: |
| ***EARLI***: a, During offline training, an RL agent interacts with a dataset of problems and learns to generate high-quality solutions. b, On inference, the trained RL agent faces a new problem instance and generates K solutions with quick decision making. c, The K solutions are used as the initial population of the cuOpt genetic algorithm, initiating its optimization loop. |


| <img src="photos/sample_sp2rio_100_cuOpt_1s_85.png" width="640"> |
| :--: |
| The solution of cuOpt, with and without EARLI, in a sample problem of 100 customers in Rio de Janeiro, given a time-budget of 1s. The RL agent was trained on Sao-Paulo problems and generalized to Rio. Note that the arrows are straight for visualization only: the actual traveling costs correspond to road-based driving time. |


# Examples

Example for training is provided in [`ExampleTrain.ipynb`](examples/ExampleTrain.ipynb).

Example for inference is provided in [`Example.ipynb`](examples/Example.ipynb). It can be used with our pretrained RL agents provided under `pretrained_models/`, or with a new trained agent.


# Data

The data of problem instances - for either training or inference - should be stored in a `pickle` file that contains a python dictionary with the following fields:
* `'positions'`: `numpy.ndarray, (n_problems, problem_size, 2)`
* `'distance_matrix'`: `numpy.ndarray, (n_problems, problem_size, problem_size)`
* `'demands'`: `numpy.ndarray, (n_problems, problem_size)`
* `'capacities'`: `numpy.ndarray, (n_problems,)`

Sample problems can be downloaded from the [NVIDIA Labs olist-vrp-benchmark repository](https://github.com/NVlabs/olist-vrp-benchmark):

```bash
python download_data.py --cleanup
```

This downloads into `./datasets/` VRP problems based on real Brazilian e-commerce data with various sizes (50-500 nodes) for Rio de Janeiro and São Paulo.


# Cite Us

This repo is published by NVIDIA as part of the paper ***Accelerating Vehicle Routing via AI-Initialized Genetic Algorithms***.
To cite:

```
@article{EARLI25,
  title={Accelerating Vehicle Routing via AI-Initialized Genetic Algorithms},
  author={Greenberg, Ido and Sielski, Piotr and Linsenmaier, Hugo and Gandham, Rajesh and Mannor, Shie and Fender, Alex and Chechik, Gal and Meirom, Eli},
  journal={arXiv preprint},
  year={2025}
}
```
