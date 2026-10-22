# Healthcare Workforce Scheduling

A Mixed Integer Linear Program (MILP) example for assigning healthcare staff to shifts while meeting coverage requirements and minimizing scheduling penalties.

## Problem Overview

A hospital unit needs to determine:

- Which nurses and CNAs should work each shift
- How to cover RN, CNA, and charge nurse demand
- How to respect approved PTO and staff availability
- How to limit weekly hours and avoid unnecessary overtime

Goal: Create a feasible multi-day staffing plan while minimizing uncovered demand, overtime, and preference penalties.

## Model Assumptions

This model uses simplified assumptions suitable for a small scheduling example:

1. Single unit: The example schedules one ICU unit.
2. Short planning horizon: The sample data covers three days with day and night shifts.
3. Known demand: Required RN, CNA, and charge nurse counts are fixed for each shift.
4. Synthetic staff data: Staff names, roles, preferences, and PTO are fictional.
5. Soft shortfall handling: Uncovered staffing is allowed through slack variables, but heavily penalized.

This formulation works well for demonstrating:

- Nurse and CNA shift assignment
- Basic coverage planning
- PTO-aware scheduling
- Charge nurse coverage
- Overtime penalty modeling

Note: Production nurse rostering may require additional constraints such as rolling weekend limits, multi-week history, skill tiers, union rules, and fairness policies.

## Notebook Contents

### Setup & Data

- 8 synthetic staff members
- 6 ICU shifts across 3 days
- RN, CNA, and charge nurse demand by shift
- Approved PTO records
- Staff shift preferences

### Optimization

- Decision variables: staff-to-shift assignments, uncovered demand, overtime
- Objective: minimize uncovered demand, overtime, and preference penalties
- Constraints: coverage, charge nurse requirement, PTO, one shift per person per day, weekly hour limits

### Results & Analysis

- Solver termination status
- Objective value
- Final staff schedule
- Open shift summary
- Overtime summary
- Schedule and call-out impact visualizations
- Call-out re-optimization example

## Quick Start

Use a Python environment with NVIDIA cuOpt, NumPy, and pandas available.

```bash
jupyter notebook healthcare_workforce_scheduling.ipynb
```

## Possible Extensions

Larger Scheduling Cases:

- Add more units and staff
- Extend the planning horizon to 1-4 weeks
- Add skill-specific requirements
- Add rolling weekend and rest-history rules

Operational Scenarios:

- Model staff call-outs and re-optimization
- Add agency staff as a high-cost fallback
- Add fairness or workload-balancing objectives
- Connect the schedule output to a staffing dashboard
