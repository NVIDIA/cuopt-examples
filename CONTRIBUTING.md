# Contributing to NVIDIA cuOpt Examples and Workflows

Contributions to NVIDIA cuOpt Examples and Workflows fall into the following categories:

1. To report a bug, request a new feature, or report a problem with documentation, please file an issue describing the problem or new feature in detail. The team evaluates and triages issues, and schedules them for a release. If you believe the issue needs priority attention, please comment on the issue to notify the team.

2. To propose and implement a new example or workflow, please file a new feature request issue. Describe the intended example/workflow and discuss the design and implementation with the team and community. Once the team agrees that the plan looks good, go ahead and implement it, using the code contributions guide below.

3. To implement a feature or bug fix for an existing issue, please follow the code contributions guide below. If you need more context on a particular issue, please ask in a comment.

As contributors and maintainers to this project, you are expected to abide by the project's code of conduct.

## Code contributions

### Your first issue

1. Follow the guide at the bottom of this page for Setting up your build environment.
2. Find an issue to work on. The best way is to look for the `good first issue` or `help wanted` labels.
3. Comment on the issue stating that you are going to work on it.
4. Create a fork of the repository and check out a branch with a name that describes your planned work. For example, `add-new-workflow-example`.
5. Write code to address the issue/upgrade an existing example/workflow or add a new example/workflow.
6. Add documentation to the example/workflow, provide instructions for running the example/workflow, and add a README.md.
7. Create your pull request.
9. Wait for other developers to review your code and update code as needed.
10. Once reviewed and approved, a team member will merge your pull request.

If you are unsure about anything, don't hesitate to comment on issues and ask for clarification!

### Seasoned developers

Once you have gotten your feet wet and are more comfortable with the code, you can look at the prioritized issues for our next release in our project boards.

**Note:** Always look at the release board that is currently under development for issues to work on. This is where the team also focuses their efforts.

Look at the unassigned issues, and find an issue to which you are comfortable contributing. Start with _Step 3_ above, commenting on the issue to let others know you are working on it. If you have any questions related to the implementation of the issue, ask them in the issue instead of the PR.

## Setting up your build environment

The following instructions are for developers and contributors to NVIDIA cuOpt Examples and Workflows development. These instructions are tested on Ubuntu Linux LTS releases. Use these instructions to build and contribute to the development. Other operating systems may be compatible, but are not currently tested.

### General requirements

For detailed system requirements, please refer to the [NVIDIA cuOpt System Requirements documentation](https://docs.nvidia.com/cuopt/user-guide/latest/system-requirements.html).

### Create the build environment

Follow the steps in the [README.md](README.md#running-the-examples) under "Running the Examples" to set-up docker environment

## Code Formatting

### Using pre-commit hooks

The project uses pre-commit to execute code linters and formatters. These tools ensure a consistent code format throughout the project. Using pre-commit ensures that linter versions and options are aligned for all developers.

To use `pre-commit`, install via `conda` or `pip`:

```bash
conda install -c conda-forge pre-commit
# or
pip install pre-commit
```

Then run pre-commit hooks before committing code:

```bash
pre-commit run
```

By default, pre-commit runs on staged files. To run pre-commit checks on all files, execute:

```bash
pre-commit run --all-files
```

Optionally, you may set up the pre-commit hooks to run automatically when you make a git commit:

```bash
pre-commit install
```

You can skip these checks with `git commit --no-verify` or with the short version `git commit -n`.

### Summary of pre-commit hooks

The following section describes some of the core pre-commit hooks used by the repository. See `.pre-commit-config.yaml` for a full list.

- Python code is formatted with Black
- Imports are sorted with isort
- Code is checked with flake8

## Developer Guidelines

### Python Code Style

- Follow PEP 8 guidelines
- Use type hints for function arguments and return values
- Write docstrings for all public functions and classes
- Keep functions focused and single-purpose
- Use meaningful variable and function names
- Add comments for complex logic

### Example and Workflow Guidelines
- Structure to follow:
    - README.md
    - requirements.txt
    - notebooks.ipynb
    - data/
    - utils 
- Each example should be self-contained and runnable
- Include clear documentation and comments, add a README.md
- Add performance benchmarks where appropriate
- Include error handling and edge cases
- Provide example input data or instructions for generating test data
- Add visualization of results where applicable
- Include example configuration files for different use cases
- Document any specific requirements or limitations
- Add a requirements.txt file to the example/workflow directory which lists the dependencies for the example/workflow
- All data files should be included in the example/workflow directory

### Notebook Guidelines

- Use Jupyter notebooks for interactive examples
- Include markdown cells with clear explanations
- Add code comments for complex operations
- Include visualization cells for results
- Provide example outputs and expected results
- Add troubleshooting sections for common issues
- Include links to relevant documentation

### Testing Guidelines

- Include integration tests for workflows
- Test edge cases and error conditions
- Ensure tests are deterministic
- Test with different input data sizes and configurations
