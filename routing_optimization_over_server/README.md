# cuOpt Server Notebooks

Contains a collection of Jupyter Notebooks that outline how cuOpt self hosted service can be used to solve a wide variety of problems.

## Platform Compatibility

If you are running on a platform where cuOpt is not installed, please un-comment the installation cell in the notebook for cuopt.

## Summary
Each notebook represents an example use case for NVIDIA cuOpt. All notebooks demonstrate high level problem modeling leveraging the cuOpt self hosted service.  In addition, each notebook covers additional cuOpt features listed below alongside notebook descriptions

- **cvrptw_service_team_routing.ipynb :** A notebook demonstrating service team routing using technicians with varied availability and skillset.
    - *Additional Features:*
        - Multiple Capacity (and demand) Dimensions
        - Vehicle Time Windows

- **cvrptw_benchmark_gehring_homberger.ipynb :** A notebook demonstrating a benchmark run using a large academic problem instance.
