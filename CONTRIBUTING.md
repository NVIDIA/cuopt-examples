# Contributing to cuOpt Examples and Workflows

Contributions to cuOpt Examples and Workflows fall into the following categories:

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
5. Write code to address the issue or implement the feature.
6. Add unit tests and documentation.
7. Create your pull request. To run continuous integration (CI) tests without requesting review, open a draft pull request.
8. Verify that CI passes all status checks. Fix if needed.
9. Wait for other developers to review your code and update code as needed.
10. Once reviewed and approved, a team member will merge your pull request.

If you are unsure about anything, don't hesitate to comment on issues and ask for clarification!

### Seasoned developers

Once you have gotten your feet wet and are more comfortable with the code, you can look at the prioritized issues for our next release in our project boards.

**Note:** Always look at the release board that is currently under development for issues to work on. This is where the team also focuses their efforts.

Look at the unassigned issues, and find an issue to which you are comfortable contributing. Start with _Step 3_ above, commenting on the issue to let others know you are working on it. If you have any questions related to the implementation of the issue, ask them in the issue instead of the PR.

## Setting up your build environment

The following instructions are for developers and contributors to cuOpt Examples and Workflows development. These instructions are tested on Ubuntu Linux LTS releases. Use these instructions to build and contribute to the development. Other operating systems may be compatible, but are not currently tested.

### General requirements

- Python 3.8+
- CUDA 11.8+
- NVIDIA GPU with Volta architecture or better (Compute Capability >=7.0)
- NVIDIA cuOpt service API access and credentials

### Create the build environment

1. Clone the repository:
```bash
git clone https://github.com/NVIDIA/cuopt-examples.git
cd cuopt-examples
```

2. Create and activate a conda environment:
```bash
conda create -n cuopt-dev python=3.8
conda activate cuopt-dev
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up your cuOpt service API credentials:
```bash
export CUOPT_API_KEY=your_api_key_here
```

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
- Type hints are checked with mypy
- Spelling is checked with codespell

## Developer Guidelines

### Python Code Style

- Follow PEP 8 guidelines
- Use type hints for function arguments and return values
- Write docstrings for all public functions and classes
- Keep functions focused and single-purpose
- Use meaningful variable and function names
- Add comments for complex logic

### Example and Workflow Guidelines

- Each example should be self-contained and runnable
- Include clear documentation and comments
- Add performance benchmarks where appropriate
- Include error handling and edge cases
- Provide example input data or instructions for generating test data
- Add visualization of results where applicable
- Follow the cuOpt service API best practices and guidelines
- Include example configuration files for different use cases
- Document any specific requirements or limitations

### Notebook Guidelines

- Use Jupyter notebooks for interactive examples
- Include markdown cells with clear explanations
- Add code comments for complex operations
- Include visualization cells for results
- Provide example outputs and expected results
- Add troubleshooting sections for common issues
- Include links to relevant documentation

### Testing Guidelines

- Write unit tests for all new functionality
- Include integration tests for workflows
- Test edge cases and error conditions
- Ensure tests are deterministic
- Add performance tests for critical paths
- Test with different input data sizes and configurations
- Include API error handling tests
