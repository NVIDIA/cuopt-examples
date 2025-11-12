# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#!/usr/bin/env python3

"""
Benchmark script for cuOpt programs.

This script runs different cuOpt programs on JSON files in a specified directory:
1. ./cuopt_json_to_c_api
2. python cuopt_json_to_api2.py 
3. python cuopt_json_to_cvxpy.py --solver_verbose
4. python cuopt_json_to_pulp.py --quiet
5. python cuopt_json_to_ampl.py --quiet
6. ./cuopt_json_to_julia.jl
7. python cuopt_json_to_gams.py

For each program and file combination, it extracts:
- Objective value
- Solve time

Features:
- Results are saved to a CSV file with incremental updates after each file
- Optional filter file to specify which JSON files to process
- Real-time monitoring possible with: tail -f cuopt_benchmark_results.csv

Usage:
  python benchmark_cuopt.py [json_files_directory] [-f filter_file]
  
If no directory is specified, uses the current directory for JSON files.
The cuOpt programs must be present in the directory where this script is run from.
The filter file should contain one JSON filename per line.
"""

import os
import glob
import subprocess
import re
import csv
import time
import argparse
from typing import Dict, List, Tuple, Optional
import sys

def parse_detailed_timing_markers(stdout: str) -> Optional[Dict[str, float]]:
    """
    Parse detailed timing markers from cuOpt interface output.
    
    Returns dictionary with timing values in seconds, or None if key markers not found.
    Expected markers:
    - PROBLEM_START: When interface setup begins
    - CUOPT_CREATE_PROBLEM: When cuOpt problem creation starts  
    - CUOPT_SOLVE_START: When cuOpt solving starts
    - CUOPT_SOLVE_RETURN: When cuOpt solving finishes
    - SOLVE_END_TIME: When interface cleanup finishes
    """
    markers = {}
    
    # Define all expected markers (handle both regular and scientific notation, and both with/without colons)
    marker_patterns = {
        'PROBLEM_START': r'PROBLEM_START:?\s+([\d.]+(?:[eE][-+]?\d+)?)',
        'CUOPT_CREATE_PROBLEM': r'CUOPT_CREATE_PROBLEM:?\s+([\d.]+(?:[eE][-+]?\d+)?)', 
        'CUOPT_SOLVE_START': r'CUOPT_SOLVE_START:?\s+([\d.]+(?:[eE][-+]?\d+)?)',
        'CUOPT_SOLVE_RETURN': r'CUOPT_SOLVE_RETURN:?\s+([\d.]+(?:[eE][-+]?\d+)?)',
        'SOLVE_END_TIME': r'(?:SOLVE_END_TIME|SOLVE_END):?\s+([\d.]+(?:[eE][-+]?\d+)?)'
    }
    
    # Extract each marker
    for marker_name, pattern in marker_patterns.items():
        match = re.search(pattern, stdout)
        if match:
            markers[marker_name] = float(match.group(1))
    
    # Only return if we have the essential markers for calculations
    essential_markers = ['PROBLEM_START', 'CUOPT_SOLVE_START', 'CUOPT_SOLVE_RETURN', 'SOLVE_END_TIME']
    if all(marker in markers for marker in essential_markers):
        return markers
    
    return None

def calculate_timing_metrics(markers: Dict[str, float]) -> Dict[str, float]:
    """
    Calculate timing metrics from detailed markers.
    
    Returns dictionary with:
    - interface_overhead: Setup + teardown overhead
    - cuopt_solver_time: Pure cuOpt solver time
    - total_time: End-to-end time
    """
    metrics = {}
    
    # Interface overhead = setup + teardown
    setup_overhead = 0.0
    if 'CUOPT_CREATE_PROBLEM' in markers:
        setup_overhead = markers['CUOPT_CREATE_PROBLEM'] - markers['PROBLEM_START']
    else:
        # If no CUOPT_CREATE_PROBLEM, use CUOPT_SOLVE_START as fallback
        setup_overhead = markers['CUOPT_SOLVE_START'] - markers['PROBLEM_START']
    
    teardown_overhead = markers['SOLVE_END_TIME'] - markers['CUOPT_SOLVE_RETURN']
    metrics['interface_overhead'] = setup_overhead + teardown_overhead
    
    # cuOpt solver time
    metrics['cuopt_solver_time'] = markers['CUOPT_SOLVE_RETURN'] - markers['CUOPT_SOLVE_START']
    
    # Total end-to-end time
    metrics['total_time'] = markers['SOLVE_END_TIME'] - markers['PROBLEM_START']
    
    return metrics

def run_command_with_timeout(cmd: List[str], timeout: int = 600, cwd: str = None) -> Tuple[int, str, str]:
    """
    Run a command with timeout and return exit code, stdout, stderr.
    """
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=timeout,
            cwd=cwd or os.getcwd()
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout} seconds"
    except Exception as e:
        return -1, "", str(e)

def parse_cuopt_json_solver_output(stdout: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse output from cuopt_json_solver to extract objective value and solver time.
    
    Expected patterns:
    - Status: Optimal   Objective: -4.64753143e+02  Iterations: 15  Time: 0.019s
    - Objective value: -464.753143
    - - Objective value: -11.638929 (Julia format with bullet point)
    """
    objective = None
    solver_time = None
    
    # Look for objective value (multiple formats)
    # Format 1: "- Objective value: -11.638929" (detailed output)
    obj_match = re.search(r'[-\s]*Objective value:\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)', stdout)
    if not obj_match:
        # Format 2: "Objective: -11.638929" (Julia subprocess format)
        obj_match = re.search(r'^Objective:\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)$', stdout, re.MULTILINE)
    
    if obj_match:
        objective = float(obj_match.group(1))
    
    # Look for solver time from Status line
    status_time_match = re.search(r'Status:\s+\w+.*?Time:\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)s', stdout)
    if status_time_match:
        solver_time = float(status_time_match.group(1))
    else:
        # Try Julia subprocess format: "Time: 0.023847" (separate line)
        time_match = re.search(r'^Time:\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)$', stdout, re.MULTILINE)
        if time_match:
            solver_time = float(time_match.group(1))
        else:
            # Try Julia detailed format: "- Solve time: 0.022 seconds"
            solve_time_match = re.search(r'[-\s]*Solve time:\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)\s*seconds', stdout)
            if solve_time_match:
                solver_time = float(solve_time_match.group(1))
    
    return objective, solver_time

def parse_cuopt_api2_output(stdout: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse output from cuopt_json_to_python_api.py to extract objective value and solver time.
    
    Expected patterns:
    - Status: Optimal   Objective: -4.64753143e+02  Iterations: 15  Time: 0.022s
    - Objective value: -464.75314285714285
    """
    objective = None
    solver_time = None
    
    # Look for objective value
    obj_match = re.search(r'Objective value:\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)', stdout)
    if obj_match:
        objective = float(obj_match.group(1))
    
    # Look for solver time from Status line
    status_time_match = re.search(r'Status:\s+\w+.*?Time:\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)s', stdout)
    if status_time_match:
        solver_time = float(status_time_match.group(1))
    
    return objective, solver_time

def parse_cuopt_json_to_cvxpy_output(stdout: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse output from cuopt_json_to_cvxpy.py to extract objective value and solver time.
    
    Expected patterns:
    - Status: Optimal   Objective: -4.64753143e+02  Iterations: 15  Time: 0.021s
    - Optimal value: -464.7531428571428
    """
    objective = None
    solver_time = None
    
    # Look for optimal value
    obj_match = re.search(r'Optimal value:\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)', stdout)
    if obj_match:
        objective = float(obj_match.group(1))
    
    # Look for solver time from Status line
    status_time_match = re.search(r'Status:\s+\w+.*?Time:\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)s', stdout)
    if status_time_match:
        solver_time = float(status_time_match.group(1))
    
    return objective, solver_time

def parse_cuopt_pulp_output(stdout: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse output from cuopt_json_to_pulp.py to extract objective value and solver time.
    
    Expected patterns (from --quiet mode):
    - Status: Optimal   Objective: -4.64753143e+02  Iterations: 15  Time: 0.024s
    - Status: Optimal
    - Objective: -464.7531428571428
    - Time: 0.011456
    """
    objective = None
    solver_time = None
    
    # Look for objective value (try both patterns)
    obj_match = re.search(r'Objective:\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)', stdout)
    if obj_match:
        objective = float(obj_match.group(1))
    
    # Look for solver time from Status line
    status_time_match = re.search(r'Status:\s+\w+.*?Time:\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)s', stdout)
    if status_time_match:
        solver_time = float(status_time_match.group(1))
    
    return objective, solver_time

def parse_cuopt_ampl_output(stdout: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse output from cuopt_json_to_ampl.py to extract objective value and solver time.
    
    Expected patterns (from --quiet mode):
    - Status: Optimal
    - Objective: -464.7531428571428
    - Time: 0.011456
    
    Also handles cuOpt solver output when AMPL licensing issues occur:
    - Status: Optimal   Objective: -4.64753143e+02  Iterations: 16  Time: 0.019s
    """
    objective = None
    solver_time = None
    
    # Look for objective value (try both patterns)
    obj_match = re.search(r'Objective:\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)', stdout)
    if obj_match:
        objective = float(obj_match.group(1))
    
    # Look for solver time - try multiple patterns
    # First try single-line cuOpt format with 's' suffix
    status_time_match = re.search(r'Status:\s+\w+.*?Time:\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)s', stdout)
    if status_time_match:
        solver_time = float(status_time_match.group(1))
    else:
        # Try AMPL format without 's' suffix
        time_match = re.search(r'Time:\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)', stdout)
        if time_match:
            solver_time = float(time_match.group(1))
    
    return objective, solver_time

def parse_cuopt_julia_output(stdout: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse output from cuopt_json_to_julia.jl to extract objective value and solver time.
    
    Expected patterns (from --quiet mode):
    - Status: OPTIMAL
    - Objective: -464.75314285714285
    - Time: 0.796463
    
    Also handles single-line format:
    - Status: Optimal   Objective: -4.64753143e+02  Iterations: 15  Time: 0.019s
    """
    objective = None
    solver_time = None
    
    # Look for objective value
    obj_match = re.search(r'Objective:\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)', stdout)
    if obj_match:
        objective = float(obj_match.group(1))
    
    # Look for solver time - handle both formats
    # First try single-line format with 's' suffix
    status_time_match = re.search(r'Status:\s+\w+.*?Time:\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)s', stdout)
    if status_time_match:
        solver_time = float(status_time_match.group(1))
    else:
        # Try multi-line format without 's' suffix
        time_match = re.search(r'Time:\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)', stdout)
        if time_match:
            solver_time = float(time_match.group(1))
    
    return objective, solver_time

def parse_cuopt_gams_output(stdout: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse output from cuopt_json_to_gams.py to extract objective value and solver time.
    
    Expected patterns:
    - Optimal objective value: -464.75314285714285
    - Solver timing information from GAMS/cuOpt solver output
    - May also handle single-line cuOpt format: Status: Optimal   Objective: -4.64753143e+02  Iterations: 15  Time: 0.019s
    """
    objective = None
    solver_time = None
    
    # Look for objective value - try both "Optimal objective value:" and "Objective:" patterns
    obj_match = re.search(r'Optimal objective value:\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)', stdout)
    if not obj_match:
        obj_match = re.search(r'Objective:\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)', stdout)
    if obj_match:
        objective = float(obj_match.group(1))
    
    # Look for solver time - handle cuOpt solver output from GAMS
    # First try single-line cuOpt format with 's' suffix
    status_time_match = re.search(r'Status:\s+\w+.*?Time:\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)s', stdout)
    if status_time_match:
        solver_time = float(status_time_match.group(1))
    else:
        # Try generic time patterns without 's' suffix
        time_match = re.search(r'Time:\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)', stdout)
        if time_match:
            solver_time = float(time_match.group(1))
    
    return objective, solver_time

def benchmark_file(json_file_path: str, selected_solvers: List[Dict]) -> Dict[str, Dict[str, Optional[float]]]:
    """
    Run selected solver programs on a JSON file and return results.
    
    Args:
        json_file_path: Full path to the JSON file
        selected_solvers: List of solver configurations to run
    
    Returns:
        Dictionary with program names as keys, each containing 'objective' and 'time' keys
    """
    results = {}
    json_filename = os.path.basename(json_file_path)
    
    print(f"\nBenchmarking {json_filename}...")
    
    # Run each selected solver
    for solver in selected_solvers:
        solver_name = solver['name']
        print(f"  Running {solver_name}...")
        
        # Build command
        cmd = solver['command'] + [json_file_path]
        
        # Julia needs --quiet after the filename
        if 'julia' in solver_name:
            cmd.append('--quiet')
        
        # Special handling for Julia - needs LD_LIBRARY_PATH set and proper conda environment
        env = None
        if 'julia' in solver_name:
            env = os.environ.copy()
            
            # Check if we're in the correct cuopt_dev environment
            conda_prefix = env.get('CONDA_PREFIX', '')
            if not conda_prefix.endswith('cuopt_dev'):
                # Try to find cuopt_dev environment
                conda_base = os.path.dirname(conda_prefix) if conda_prefix else None
                cuopt_env_path = os.path.join(conda_base, 'cuopt_dev') if conda_base else None
                
                if cuopt_env_path and os.path.exists(cuopt_env_path):
                    conda_prefix = cuopt_env_path
                    env['CONDA_PREFIX'] = conda_prefix
                    # Also update PATH to use cuopt_dev environment
                    cuopt_bin = os.path.join(conda_prefix, 'bin')
                    if os.path.exists(cuopt_bin):
                        current_path = env.get('PATH', '')
                        env['PATH'] = f"{cuopt_bin}:{current_path}"
            
            # Set LD_LIBRARY_PATH to include the conda environment lib directory
            if conda_prefix:
                current_ld_path = env.get('LD_LIBRARY_PATH', '')
                env['LD_LIBRARY_PATH'] = f"{conda_prefix}/lib:{current_ld_path}"
        
        # Run the command and measure total time
        import time
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=600,
                env=env
            )
            exit_code = result.returncode
            stdout = result.stdout
            stderr = result.stderr
        except subprocess.TimeoutExpired:
            exit_code = -1
            stdout = ""
            stderr = "Command timed out after 600 seconds"
        except Exception as e:
            exit_code = -1
            stdout = ""
            stderr = str(e)
        total_time = time.time() - start_time
        
        # Parse output using detailed timing markers
        if exit_code == 0:
            # Get the parser function by name for objective and reported solver time
            parser_func = globals()[solver['parser']]
            objective, reported_solver_time = parser_func(stdout)
            
            
            # Round objective value to 6 decimal places if not None
            if objective is not None:
                objective = round(objective, 6)
            
            # Parse detailed timing markers
            timing_markers = parse_detailed_timing_markers(stdout)
            if timing_markers:
                timing_metrics = calculate_timing_metrics(timing_markers)
                
                results[solver_name] = {
                    "objective": objective,
                    "interface_overhead": timing_metrics['interface_overhead'],
                    "cuopt_solver_time": timing_metrics['cuopt_solver_time'],
                    "process_total_time": total_time,  # Always use subprocess time for total_time
                    "reported_solver_time": reported_solver_time,  # Keep for comparison
                    "marker_total_time": timing_metrics['total_time']  # Store marker time for analysis
                }
                
                print(f"    ✓ Objective: {objective}")
                print(f"      Interface Overhead: {timing_metrics['interface_overhead']:.3f}s")
                print(f"      cuOpt Solver Time: {timing_metrics['cuopt_solver_time']:.3f}s")
                print(f"      Total Time (subprocess): {total_time:.3f}s")
                print(f"      Total Time (markers): {timing_metrics['total_time']:.3f}s")
                print(f"      (Reported solver time: {reported_solver_time if reported_solver_time is not None else 'None'}s)")
            else:
                # Fallback to old method if detailed markers not found
                results[solver_name] = {
                    "objective": objective,
                    "interface_overhead": None,
                    "cuopt_solver_time": None, 
                    "process_total_time": total_time,  # Subprocess time
                    "reported_solver_time": reported_solver_time,
                    "marker_total_time": None
                }
                print(f"    ✓ Objective: {objective}, Reported Solver Time: {reported_solver_time}s, Total Time: {total_time:.3f}s")
                print(f"      (No detailed timing markers found)")
        else:
            results[solver_name] = {
                "objective": None,
                "interface_overhead": None,
                "cuopt_solver_time": None,
                "process_total_time": total_time,  # Subprocess time for failed runs
                "reported_solver_time": None,
                "marker_total_time": None
            }
            print(f"    ✗ Failed (exit code {exit_code}): {stderr}")
    
    return results

def main():
    """
    Main benchmarking function.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Benchmark cuOpt programs on JSON files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python benchmark_cuopt.py                    # Use JSON files from current directory
  python benchmark_cuopt.py /path/to/jsons     # Use JSON files from specified directory
  python benchmark_cuopt.py ../test_problems   # Use JSON files from relative path
  python benchmark_cuopt.py lp/ -f small_files.txt  # Use files from lp/ but only those listed in small_files.txt

Note: The cuOpt programs (cuopt_json_to_c_api, cuopt_json_to_python_api.py, cuopt_json_to_cvxpy.py, 
cuopt_json_to_pulp.py, cuopt_json_to_ampl.py, cuopt_json_to_julia.jl, cuopt_json_to_gams.py, etc.) must be present in the directory where this script is run from.

The CSV results file is updated after each file is processed, so you can monitor 
progress in real-time using: tail -f cuopt_benchmark_results.csv
        """
    )
    parser.add_argument(
        'directory', 
        nargs='?', 
        default='.',
        help='Directory containing JSON files to benchmark (default: current directory)'
    )
    parser.add_argument(
        '-f', '--filter-file',
        type=str,
        help='Text file containing JSON filenames to process (one per line). If not provided, all JSON files will be processed.'
    )
    parser.add_argument(
        '--solvers',
        type=str,
        default='C,ampl,julia,gams,python,cvxpy,pulp',
        help='Comma-separated list of solvers to run. Options: C (cuopt_json_to_c_api), ampl (cuopt_json_to_ampl.py), julia (cuopt_json_to_julia.jl), gams (cuopt_json_to_gams.py), python (cuopt_json_to_python_api.py), cvxpy (cuopt_json_to_cvxpy.py), pulp (cuopt_json_to_pulp.py). Default: C,ampl,julia,gams,python,cvxpy,pulp (currently focusing on detailed timing analysis for these seven)'
    )
    
    args = parser.parse_args()
    
    # Parse and validate solvers argument (currently focusing on C, AMPL, Julia, GAMS, Python, CVXPY, and PuLP with detailed timing)
    SOLVER_MAPPING = {
        'C': {
            'name': 'cuopt_json_to_c_api',
            'command': ['./cuopt_json_to_c_api'],
            'file_check': 'cuopt_json_to_c_api',
            'parser': 'parse_cuopt_json_solver_output'
        },
        'ampl': {
            'name': 'cuopt_json_to_ampl',
            'command': ['python', 'cuopt_json_to_ampl.py', '--quiet'],
            'file_check': 'cuopt_json_to_ampl.py',
            'parser': 'parse_cuopt_ampl_output'
        },
        'julia': {
            'name': 'cuopt_json_to_julia',
            'command': ['julia', 'cuopt_json_to_julia.jl'],
            'file_check': 'cuopt_json_to_julia.jl',
            'parser': 'parse_cuopt_json_solver_output'
        },
        'gams': {
            'name': 'cuopt_json_to_gams',
            'command': ['python', 'cuopt_json_to_gams.py'],
            'file_check': 'cuopt_json_to_gams.py',
            'parser': 'parse_cuopt_gams_output'
        },
        'python': {
            'name': 'cuopt_json_to_python_api',
            'command': ['python', 'cuopt_json_to_python_api.py'],
            'file_check': 'cuopt_json_to_python_api.py',
            'parser': 'parse_cuopt_json_solver_output'
        },
        'cvxpy': {
            'name': 'cuopt_json_to_cvxpy',
            'command': ['python', 'cuopt_json_to_cvxpy.py', '--solver_verbose'],
            'file_check': 'cuopt_json_to_cvxpy.py',
            'parser': 'parse_cuopt_json_to_cvxpy_output'
        },
        'pulp': {
            'name': 'cuopt_json_to_pulp',
            'command': ['python', 'cuopt_json_to_pulp.py', '--quiet'],
            'file_check': 'cuopt_json_to_pulp.py',
            'parser': 'parse_cuopt_pulp_output'
        }
    }
    
    # Parse selected solvers
    solver_keys = [s.strip() for s in args.solvers.split(',')]
    invalid_solvers = [s for s in solver_keys if s not in SOLVER_MAPPING]
    if invalid_solvers:
        print(f"ERROR: Invalid solver(s): {', '.join(invalid_solvers)}")
        print(f"Valid options: {', '.join(SOLVER_MAPPING.keys())}")
        sys.exit(1)
    
    selected_solvers = [SOLVER_MAPPING[key] for key in solver_keys]
    
    # Convert to absolute path and validate for JSON files directory
    json_dir = os.path.abspath(args.directory)
    if not os.path.exists(json_dir):
        print(f"ERROR: Directory '{json_dir}' does not exist!")
        sys.exit(1)
    
    if not os.path.isdir(json_dir):
        print(f"ERROR: '{json_dir}' is not a directory!")
        sys.exit(1)
    
    # Current working directory where programs should be located
    program_dir = os.getcwd()
    
    print("cuOpt Programs Benchmark")
    print("=" * 50)
    print(f"Programs directory: {program_dir}")
    print(f"JSON files directory: {json_dir}")
    
    # Find all JSON files in the specified directory
    json_pattern = os.path.join(json_dir, "*.json")
    json_paths = glob.glob(json_pattern)
    
    if not json_paths:
        print(f"No JSON files found in directory: {json_dir}")
        sys.exit(1)
    
    json_files = [os.path.basename(path) for path in json_paths]
    print(f"Found {len(json_files)} JSON files in directory")
    
    # Apply filter if provided
    if args.filter_file:
        if not os.path.exists(args.filter_file):
            print(f"ERROR: Filter file '{args.filter_file}' does not exist!")
            sys.exit(1)
        
        print(f"Reading filter file: {args.filter_file}")
        try:
            with open(args.filter_file, 'r') as f:
                filter_files = set(line.strip() for line in f if line.strip())
            
            # Filter JSON files to only those in the filter list
            original_count = len(json_files)
            json_files = [f for f in json_files if f in filter_files]
            json_paths = [p for p in json_paths if os.path.basename(p) in filter_files]
            
            print(f"Filter contains {len(filter_files)} filenames")
            print(f"After filtering: {len(json_files)} files will be processed (was {original_count})")
            
            if not json_files:
                print("No JSON files match the filter!")
                sys.exit(1)
                
        except Exception as e:
            print(f"ERROR reading filter file: {e}")
            sys.exit(1)
    
    print(f"Files to process: {', '.join(json_files[:10])}")
    if len(json_files) > 10:
        print(f"... and {len(json_files) - 10} more")
    
    # Check if selected programs exist in the current working directory
    programs_exist = True
    print(f"Selected solvers: {', '.join([s['name'] for s in selected_solvers])}")
    
    for solver in selected_solvers:
        file_path = os.path.join(program_dir, solver['file_check'])
        if not os.path.exists(file_path):
            print(f"ERROR: {solver['file_check']} not found in {program_dir}")
            programs_exist = False
    
    if not programs_exist:
        sys.exit(1)
    
    # Initialize CSV file for incremental updates
    csv_filename = "cuopt_benchmark_results.csv"
    fieldnames = ['filename']
    for solver in selected_solvers:
        fieldnames.extend([
            f"{solver['name']}_objective", 
            f"{solver['name']}_interface_overhead", 
            f"{solver['name']}_cuopt_solver_time",
            f"{solver['name']}_process_total_time",
            f"{solver['name']}_reported_solver_time",
            f"{solver['name']}_marker_total_time"
        ])
    
    print(f"\nCreating CSV report: {csv_filename}")
    print("(You can monitor progress by running: tail -f cuopt_benchmark_results.csv)")
    
    # Create CSV file and write header
    with open(csv_filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
    
    # Run benchmarks with incremental CSV updates
    all_results = {}
    total_start = time.time()
    
    for i, json_path in enumerate(sorted(json_paths), 1):
        json_filename = os.path.basename(json_path)
        print(f"\n[{i}/{len(json_paths)}] Processing {json_filename}...")
        
        file_results = benchmark_file(json_path, selected_solvers)
        all_results[json_filename] = file_results
        
        # Update CSV file immediately after each file
        with open(csv_filename, 'a', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            row = {'filename': json_filename}
            
            for solver in selected_solvers:
                solver_name = solver['name']
                if solver_name in file_results:
                    row[f'{solver_name}_objective'] = file_results[solver_name]['objective']
                    row[f'{solver_name}_interface_overhead'] = file_results[solver_name]['interface_overhead']
                    row[f'{solver_name}_cuopt_solver_time'] = file_results[solver_name]['cuopt_solver_time']
                    row[f'{solver_name}_process_total_time'] = file_results[solver_name]['process_total_time']
                    row[f'{solver_name}_reported_solver_time'] = file_results[solver_name]['reported_solver_time']
                    row[f'{solver_name}_marker_total_time'] = file_results[solver_name]['marker_total_time']
                else:
                    row[f'{solver_name}_objective'] = None
                    row[f'{solver_name}_interface_overhead'] = None
                    row[f'{solver_name}_cuopt_solver_time'] = None
                    row[f'{solver_name}_process_total_time'] = None
                    row[f'{solver_name}_reported_solver_time'] = None
                    row[f'{solver_name}_marker_total_time'] = None
            
            writer.writerow(row)
            csvfile.flush()  # Ensure data is written immediately for tailing
    
    total_time = time.time() - total_start
    print(f"\nBenchmarking completed in {total_time:.2f} seconds")
    
    # Print summary table
    print("\nSummary Table:")

    # Dynamic header generation
    solver_names = [solver['name'] for solver in selected_solvers]
    header_width = 20 + (25 * len(solver_names))
    print("-" * header_width)

    # File column plus solver columns
    header_parts = [f"{'File':<20}"]
    for solver_name in solver_names:
        header_parts.append(f"{solver_name:<25}")
    print("".join(header_parts))

    # Sub-header for "Obj / cuOpt+Interface / Total Time"  
    subheader_parts = [f"{'':20}"]
    for _ in solver_names:
        subheader_parts.append(f"{'Obj / cuOpt+Interface / TotalT':<25}")
    print("".join(subheader_parts))
    print("-" * header_width)

    for json_file in sorted(json_files):
        results = all_results[json_file]
        row_parts = [json_file[:19]]
        
        for solver in selected_solvers:
            solver_name = solver['name']
            if solver_name in results and results[solver_name]['objective'] is not None:
                obj = results[solver_name]['objective']
                
                # Use new detailed timing structure if available
                if results[solver_name]['cuopt_solver_time'] is not None:
                    cuopt_time = results[solver_name]['cuopt_solver_time']
                    interface_overhead = results[solver_name]['interface_overhead']
                    total_time = results[solver_name]['process_total_time']
                    # Show cuOpt solver time + interface overhead
                    row_parts.append(f"{obj:.2f}/{cuopt_time:.3f}+{interface_overhead:.3f}/{total_time:.3f}"[:24])
                else:
                    # Fallback to old structure
                    reported_solver_time = results[solver_name]['reported_solver_time']
                    total_time = results[solver_name]['process_total_time']
                    if reported_solver_time is not None:
                        row_parts.append(f"{obj:.2f}/{reported_solver_time:.3f}/{total_time:.3f}"[:24])
                    else:
                        row_parts.append(f"{obj:.2f}/--/{total_time:.3f}"[:24])
            else:
                row_parts.append("FAILED"[:24])
        
        # Print the row with dynamic formatting
        formatted_row = f"{row_parts[0]:<20}"
        for i in range(1, len(row_parts)):
            formatted_row += f" {row_parts[i]:<25}"
        print(formatted_row)
    
    print(f"\nResults saved to: {os.path.abspath(csv_filename)}")

if __name__ == "__main__":
    main() 
