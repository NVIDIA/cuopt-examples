## GAMSPy cuOpt integration example notebook

### How to run the notebook
- Setup and activate a Python environment in the `cuopt-examples` root directory e.g. with `python -m venv .venv` and `source .venv/bin/activate`
- Install requirements `pip install -r requirements.txt`
- Run this notebook from a GUI or update its cells in the command line via `jupyter nbconvert --to notebook --execute --inplace trnsport_cuopt.ipynb`
- The first cell takes care of installing cuOpt runtime, GAMSPy, and the solver link. Skips most parts when it's already there.
