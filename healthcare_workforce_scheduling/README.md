# Healthcare Workforce Scheduling

A Mixed Integer Linear Program (MILP) example for assigning healthcare staff to shifts with the NVIDIA cuOpt Python API.

## Problem Overview

An ICU needs to assign registered nurses (RNs) and certified nursing assistants (CNAs) to day and night shifts while accounting for staffing demand, charge-eligible RN coverage, approved PTO, regular-hours limits, overtime, and shift preferences.

The example also demonstrates re-optimization after a nurse assigned to a shift calls out.

The supplied CSV data is synthetic.

## How This Differs from `workforce_optimization`

The existing `workforce_optimization` example assigns general workers to shifts while minimizing labor cost and exploring coverage and fairness. This healthcare example focuses on clinical scheduling requirements:

- separate RN and CNA roles
- charge-eligible RN coverage
- approved PTO
- regular-hours and overtime tracking
- day/night shift preferences
- soft staffing and charge-coverage shortfalls
- call-out recovery using the same optimization model

## Files

- `healthcare_workforce_scheduling.ipynb`: formulation, solve, analysis, and call-out recovery
- `data/staff.csv`: synthetic staff roster
- `data/demand.csv`: synthetic shift-level staffing requirements
- `data/pto.csv`: synthetic approved PTO
- `requirements.txt`: notebook data and visualization dependencies

## Model Summary

### Decision variables

- binary staff-to-shift assignments
- RN and CNA shortage variables
- charge-coverage shortfall variables
- continuous overtime hours

### Constraints

- RN, CNA, and charge-eligible RN coverage
- approved PTO and call-out unavailability
- at most one shift per person per day
- regular-hours limits with overtime tracking

### Objective

Minimize weighted penalties for staffing shortages, missing charge coverage, overtime, and shift-preference misses.

## Run the Notebook

Use a Linux environment with a supported NVIDIA GPU and the cuOpt Python API installed.

From the repository root, install the example dependencies:

```bash
python -m pip install -r healthcare_workforce_scheduling/requirements.txt
```

Start Jupyter:

```bash
jupyter notebook healthcare_workforce_scheduling/healthcare_workforce_scheduling.ipynb
```

Run the cells in order. The notebook validates the base schedule, re-solves after a call-out, and checks an extreme no-assignment case.

## Possible Extensions

- extend the planning horizon
- schedule multiple hospital units
- add skill and certification requirements
- add rest, fatigue, weekend, and fairness rules
- add agency staff as a high-cost fallback
