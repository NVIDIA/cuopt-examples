#!/usr/bin/env python3

# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.  # noqa
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
"""
Benchmark Results Analyzer for cuOpt Programs

This script analyzes the results from cuopt_benchmark_results.csv and provides:
- Which solver was fastest for each problem (based on total time including overhead)
- Whether objective values are consistent across solvers
- Percentage differences in total times compared to the fastest solver
- Solver time analysis and flags for interfaces with >1% solver time deviation (ignoring ≤1ms differences)

The script compares total time by default since overhead is important for practical use,
but also analyzes pure solver performance to identify interface inefficiencies.

Usage:
  python analyze_benchmark_results.py [csv_file] [--time-metric {solver,total}]
  
If no CSV file is specified, uses cuopt_benchmark_results.csv in current directory.
The default time metric is total_time.
"""

import csv
import sys
import os
import argparse
from typing import Dict, List, Optional, Tuple
import statistics

def is_close(a: float, b: float, rel_tol: float = 1e-6, abs_tol: float = 1e-9) -> bool:
    """
    Check if two floating point numbers are close within tolerance.
    Similar to math.isclose but handles None values.
    """
    if a is None or b is None:
        return False
    return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)

def discover_solvers(headers: List[str]) -> List[str]:
    """
    Discover solver names from CSV headers by looking for both *_objective, *_solver_time, and *_total_time patterns.
    
    Args:
        headers: List of CSV column headers
        
    Returns:
        List of solver names found
    """
    solvers = set()
    
    for header in headers:
        if header.endswith('_objective'):
            solver_name = header[:-10]  # Remove '_objective'
            # Check if both time columns exist
            if f"{solver_name}_solver_time" in headers and f"{solver_name}_total_time" in headers:
                solvers.add(solver_name)
    
    return sorted(list(solvers))

def analyze_row(row: Dict[str, str], solver_names: List[str], time_metric: str = 'total') -> Dict[str, any]:
    """
    Analyze a single benchmark result row.
    
    Args:
        row: Dictionary containing the CSV row data
        solver_names: List of solver names to analyze
        time_metric: Either 'solver' or 'total' to specify which time metric to use for main comparison
    
    Returns:
        Dictionary with analysis results
    """
    filename = row['filename']
    
    # Extract solver results dynamically - get both solver_time and total_time
    solvers = {}
    for solver_name in solver_names:
        solvers[solver_name] = {
            'objective': row.get(f'{solver_name}_objective'),
            'solver_time': row.get(f'{solver_name}_solver_time'),
            'total_time': row.get(f'{solver_name}_total_time')
        }
    
    # Convert string values to float, handle empty/None values
    for solver_name, data in solvers.items():
        try:
            data['objective'] = float(data['objective']) if data['objective'] and data['objective'].strip() else None
            data['solver_time'] = float(data['solver_time']) if data['solver_time'] and data['solver_time'].strip() else None
            data['total_time'] = float(data['total_time']) if data['total_time'] and data['total_time'].strip() else None
        except (ValueError, TypeError):
            data['objective'] = None
            data['solver_time'] = None
            data['total_time'] = None
    
    # Find solvers that completed successfully (need objective and both time metrics)
    successful_solvers = {name: data for name, data in solvers.items() 
                         if data['objective'] is not None and data['solver_time'] is not None and data['total_time'] is not None}
    
    analysis = {
        'filename': filename,
        'solvers': solvers,
        'successful_solvers': list(successful_solvers.keys()),
        'failed_solvers': [name for name in solvers.keys() if name not in successful_solvers],
        'fastest_solver': None,
        'fastest_solver_by_solver_time': None,
        'objective_consistent': None,
        'objective_values': [],
        'time_differences': {},
        'solver_time_differences': {},
        'fastest_time': None,
        'fastest_solver_time': None,
        'time_metric': time_metric,
        'solver_time_deviations': {}  # Interfaces with >1% solver time deviation
    }
    
    if not successful_solvers:
        analysis['status'] = 'ALL_FAILED'
        return analysis
    
    # Check objective value consistency
    objectives = [data['objective'] for data in successful_solvers.values()]
    analysis['objective_values'] = objectives
    
    if len(set([round(obj, 6) for obj in objectives])) == 1:
        analysis['objective_consistent'] = True
    else:
        # Check with tolerance
        reference_obj = objectives[0]
        analysis['objective_consistent'] = all(is_close(obj, reference_obj, rel_tol=1e-6) 
                                             for obj in objectives)
    
    # Find fastest solver by main metric (total time by default)
    main_time_key = 'total_time' if time_metric == 'total' else 'solver_time'
    times = [(name, data[main_time_key]) for name, data in successful_solvers.items()]
    times.sort(key=lambda x: x[1])
    
    analysis['fastest_solver'] = times[0][0]
    analysis['fastest_time'] = times[0][1]
    
    # Calculate time differences for main metric
    fastest_time = times[0][1]
    for name, data in successful_solvers.items():
        if data[main_time_key] != fastest_time:
            pct_diff = ((data[main_time_key] - fastest_time) / fastest_time) * 100
            analysis['time_differences'][name] = pct_diff
        else:
            analysis['time_differences'][name] = 0.0
    
    # Find fastest solver by solver time and calculate solver time differences
    solver_times = [(name, data['solver_time']) for name, data in successful_solvers.items()]
    solver_times.sort(key=lambda x: x[1])
    
    analysis['fastest_solver_by_solver_time'] = solver_times[0][0]
    analysis['fastest_solver_time'] = solver_times[0][1]
    
    # Calculate solver time differences and flag >1% deviations (but ignore differences ≤1ms)
    fastest_solver_time = solver_times[0][1]
    for name, data in successful_solvers.items():
        if data['solver_time'] != fastest_solver_time:
            pct_diff = ((data['solver_time'] - fastest_solver_time) / fastest_solver_time) * 100
            analysis['solver_time_differences'][name] = pct_diff
            # Flag if deviation is >1% AND absolute difference is >1ms (0.001s)
            abs_diff = data['solver_time'] - fastest_solver_time
            if pct_diff > 1.0 and abs_diff > 0.001:
                analysis['solver_time_deviations'][name] = pct_diff
        else:
            analysis['solver_time_differences'][name] = 0.0
    
    analysis['status'] = 'SUCCESS'
    return analysis

def format_solver_name(name: str) -> str:
    """Format solver name for display."""
    # Known mappings for common solvers
    name_map = {
        'cuopt_json_to_c_api': 'C API',
        'cuopt_json_to_python': 'Python API',
        'cuopt_json_to_cvxpy': 'CVXPY',
        'cuopt_json_to_pulp': 'PuLP',
        'cuopt_json_to_ampl': 'AMPL',
        'cuopt_json_to_julia': 'Julia'
    }
    
    # If we have a known mapping, use it
    if name in name_map:
        return name_map[name]
    
    # Otherwise, create a nice display name from the solver name
    # Convert underscores to spaces and title case
    display_name = name.replace('_', ' ').title()
    
    # Handle some common patterns
    if display_name.startswith('Cuopt '):
        display_name = display_name.replace('Cuopt ', 'cuOpt ')
    
    return display_name

def print_detailed_analysis(analyses: List[Dict], solver_names: List[str], show_all: bool = False):
    """Print detailed analysis of all results."""
    
    if not analyses:
        return
        
    time_metric = analyses[0].get('time_metric', 'total')
    time_label = "Total Time" if time_metric == 'total' else "Solver Time"
    
    print("DETAILED BENCHMARK ANALYSIS")
    print("=" * 80)
    print(f"Primary Metric: {time_label} (overhead {'included' if time_metric == 'total' else 'excluded'})")
    print("=" * 80)
    
    # Summary statistics
    total_problems = len(analyses)
    successful_problems = sum(1 for a in analyses if a['status'] == 'SUCCESS')
    failed_problems = total_problems - successful_problems
    
    print(f"Total problems analyzed: {total_problems}")
    print(f"Successfully solved: {successful_problems}")
    print(f"Failed problems: {failed_problems}")
    
    if successful_problems == 0:
        print("No successful results to analyze!")
        return
    
    # Count solver performance and solver time deviations
    fastest_counts = {}
    fastest_solver_time_counts = {}
    objective_inconsistent = 0
    problems_with_solver_time_deviations = 0
    
    for analysis in analyses:
        if analysis['status'] == 'SUCCESS':
            fastest = analysis['fastest_solver']
            fastest_counts[fastest] = fastest_counts.get(fastest, 0) + 1
            
            fastest_solver_time = analysis['fastest_solver_by_solver_time']
            fastest_solver_time_counts[fastest_solver_time] = fastest_solver_time_counts.get(fastest_solver_time, 0) + 1
            
            if not analysis['objective_consistent']:
                objective_inconsistent += 1
            
            if analysis['solver_time_deviations']:
                problems_with_solver_time_deviations += 1
    
    print(f"\nFASTEST SOLVER SUMMARY ({time_label.lower()}):")
    print("-" * 40)
    for solver, count in sorted(fastest_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / successful_problems) * 100
        print(f"{format_solver_name(solver):<15}: {count:3d} problems ({percentage:5.1f}%)")
    
    print(f"\nFASTEST SOLVER BY PURE SOLVER TIME:")
    print("-" * 40)
    for solver, count in sorted(fastest_solver_time_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / successful_problems) * 100
        print(f"{format_solver_name(solver):<15}: {count:3d} problems ({percentage:5.1f}%)")
    
    if problems_with_solver_time_deviations > 0:
        print(f"\n⚠️  WARNING: {problems_with_solver_time_deviations} problems had interfaces with >1% solver time deviation!")
        print("   This suggests potential interface inefficiencies beyond just overhead.")
    else:
        print(f"\n✅ All interfaces had consistent solver times (within 1 millisecond or 1% of best)")
    
    if objective_inconsistent > 0:
        print(f"\n⚠️  WARNING: {objective_inconsistent} problems had inconsistent objective values!")
    else:
        print(f"\n✅ All problems had consistent objective values across solvers")
    
    print(f"\nPROBLEM-BY-PROBLEM ANALYSIS:")
    print("-" * 80)
    
    for analysis in analyses:
        if analysis['status'] != 'SUCCESS' and not show_all:
            continue
            
        filename = analysis['filename']
        print(f"\n📁 {filename}")
        
        if analysis['status'] == 'ALL_FAILED':
            print("   ❌ All solvers failed")
            continue
        elif analysis['failed_solvers']:
            print(f"   ⚠️  Failed solvers: {', '.join([format_solver_name(s) for s in analysis['failed_solvers']])}")
        
        if not analysis['objective_consistent']:
            print(f"   ⚠️  Objective values differ:")
            for solver in analysis['successful_solvers']:
                obj = analysis['solvers'][solver]['objective']
                print(f"      {format_solver_name(solver):<15}: {obj}")
        
        # Show timing results
        fastest = analysis['fastest_solver']
        fastest_time = analysis['fastest_time']
        fastest_solver_time_solver = analysis['fastest_solver_by_solver_time']
        fastest_solver_time = analysis['fastest_solver_time']
        
        print(f"   🏆 Fastest {time_label.lower()}: {format_solver_name(fastest)} ({fastest_time:.6f}s)")
        print(f"   ⚡ Fastest solver time: {format_solver_name(fastest_solver_time_solver)} ({fastest_solver_time:.6f}s)")
        
        # Flag solver time deviations
        if analysis['solver_time_deviations']:
            print(f"   🚨 Solver time deviations >1%:")
            # Sort by solver name for consistent ordering
            for solver in sorted(analysis['solver_time_deviations'].keys()):
                deviation = analysis['solver_time_deviations'][solver]
                solver_time = analysis['solvers'][solver]['solver_time']
                print(f"      {format_solver_name(solver):<15}: +{deviation:6.1f}% ({solver_time:.6f}s)")
        
        if len(analysis['successful_solvers']) > 1:
            print(f"   📊 {time_label} differences:")
            # Sort solvers by name for consistent ordering
            sorted_solvers = sorted(analysis['successful_solvers'])
            for solver in sorted_solvers:
                pct_diff = analysis['time_differences'][solver]
                solver_total_time = analysis['solvers'][solver]['total_time'] if time_metric == 'total' else analysis['solvers'][solver]['solver_time']
                solver_solver_time = analysis['solvers'][solver]['solver_time']
                total_time = analysis['solvers'][solver]['total_time']
                overhead = total_time - solver_solver_time
                overhead_pct = (overhead / solver_solver_time) * 100 if solver_solver_time > 0 else 0
                if pct_diff == 0.0:
                    print(f"      {format_solver_name(solver):<15}: 0.0% ({solver_total_time:.6f}s, overhead: {overhead:.6f}s/{overhead_pct:.1f}%)")
                else:
                    print(f"      {format_solver_name(solver):<15}: +{pct_diff:6.1f}% ({solver_total_time:.6f}s, overhead: {overhead:.6f}s/{overhead_pct:.1f}%)")

def print_summary_table(analyses: List[Dict], solver_names: List[str]):
    """Print a concise summary table."""
    
    successful_analyses = [a for a in analyses if a['status'] == 'SUCCESS']
    if not successful_analyses:
        return
    
    time_metric = successful_analyses[0].get('time_metric', 'total')
    time_label = "Total Time" if time_metric == 'total' else "Solver Time"
    
    print(f"\nSUMMARY TABLE ({time_label})")
    print("=" * 120)
    print(f"{'Problem':<20} {'Fastest':<12} {'Obj OK':<7} {'SolverT Dev':<11} {time_label + ' Differences':<60}")
    print("-" * 120)
    
    for analysis in successful_analyses:
        filename = analysis['filename'][:19]  # Truncate long names
        fastest = format_solver_name(analysis['fastest_solver'])[:11]
        obj_ok = "✅" if analysis['objective_consistent'] else "❌"
        
        # Show solver time deviation flag
        solver_dev = "🚨" if analysis['solver_time_deviations'] else "✅"
        
        # Build time difference string - include ALL solvers in consistent order
        time_diffs = []
        # Sort solvers by name for consistent ordering across problems
        sorted_solvers = sorted(analysis['successful_solvers'])
        for solver in sorted_solvers:
            pct_diff = analysis['time_differences'][solver]
            if pct_diff == 0.0:
                time_diffs.append(f"{format_solver_name(solver)}: 0.0%")
            else:
                time_diffs.append(f"{format_solver_name(solver)}: +{pct_diff:.1f}%")
        
        time_diff_str = ", ".join(time_diffs)[:59]  # Truncate if too long
        
        print(f"{filename:<20} {fastest:<12} {obj_ok:<7} {solver_dev:<11} {time_diff_str:<60}")

def calculate_overall_stats(analyses: List[Dict], solver_names: List[str]):
    """Calculate and print overall statistics."""
    
    successful_analyses = [a for a in analyses if a['status'] == 'SUCCESS']
    if not successful_analyses:
        return
    
    time_metric = successful_analyses[0].get('time_metric', 'total')
    time_label = "Total Time" if time_metric == 'total' else "Solver Time"
    
    print(f"\nOVERALL PERFORMANCE STATISTICS")
    print("=" * 70)
    
    # Initialize speedup statistics for all discovered solvers
    solver_speedups = {solver: [] for solver in solver_names}
    solver_time_speedups = {solver: [] for solver in solver_names}
    overhead_stats = {solver: [] for solver in solver_names}
    
    for analysis in successful_analyses:
        fastest_time = analysis['fastest_time']
        fastest_solver_time = analysis['fastest_solver_time']
        
        for solver in analysis['successful_solvers']:
            # Main metric speedups
            main_time = analysis['solvers'][solver]['total_time'] if time_metric == 'total' else analysis['solvers'][solver]['solver_time']
            speedup_factor = main_time / fastest_time
            solver_speedups[solver].append(speedup_factor)
            
            # Solver time speedups
            solver_time = analysis['solvers'][solver]['solver_time']
            solver_time_speedup_factor = solver_time / fastest_solver_time
            solver_time_speedups[solver].append(solver_time_speedup_factor)
            
            # Overhead calculation
            total_time = analysis['solvers'][solver]['total_time']
            overhead = total_time - solver_time
            overhead_pct = (overhead / solver_time) * 100 if solver_time > 0 else 0
            overhead_stats[solver].append(overhead_pct)
    
    print(f"{time_label} Performance:")
    print("-" * 50)
    for solver in solver_names:
        speedups = solver_speedups[solver]
        if speedups:
            avg_speedup = statistics.mean(speedups)
            median_speedup = statistics.median(speedups)
            print(f"{format_solver_name(solver):<15}: Avg {avg_speedup:.2f}x, Median {median_speedup:.2f}x relative to fastest")
    
    print(f"\nSolver Time Performance:")
    print("-" * 50)
    for solver in solver_names:
        speedups = solver_time_speedups[solver]
        if speedups:
            avg_speedup = statistics.mean(speedups)
            median_speedup = statistics.median(speedups)
            print(f"{format_solver_name(solver):<15}: Avg {avg_speedup:.2f}x, Median {median_speedup:.2f}x relative to fastest")
    
    print(f"\nOverhead Analysis:")
    print("-" * 50)
    for solver in solver_names:
        overheads = overhead_stats[solver]
        if overheads:
            avg_overhead = statistics.mean(overheads)
            median_overhead = statistics.median(overheads)
            print(f"{format_solver_name(solver):<15}: Avg {avg_overhead:.1f}%, Median {median_overhead:.1f}% overhead")

def main():
    """Main analysis function."""
    
    parser = argparse.ArgumentParser(
        description='Analyze cuOpt benchmark results',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python analyze_benchmark_results.py                           # Use default CSV file, analyze total time
  python analyze_benchmark_results.py results.csv              # Use specified CSV file, analyze total time
  python analyze_benchmark_results.py --time-metric solver     # Analyze solver time instead of total time
  python analyze_benchmark_results.py --show-failed            # Include failed problems in output

Note: The script always analyzes both solver time and total time, but uses the specified
time metric for primary comparisons. Solver time deviations >1% are flagged regardless
of the primary metric.
        """
    )
    
    parser.add_argument(
        'csv_file', 
        nargs='?', 
        default='cuopt_benchmark_results.csv',
        help='CSV file to analyze (default: cuopt_benchmark_results.csv)'
    )
    
    parser.add_argument(
        '--time-metric',
        choices=['solver', 'total'],
        default='total',
        help='Primary time metric for comparisons: solver (time spent in solver) or total (including overhead). Default: total'
    )
    
    parser.add_argument(
        '--show-failed',
        action='store_true',
        help='Show details for problems where all solvers failed'
    )
    
    args = parser.parse_args()
    
    # Check if CSV file exists
    if not os.path.exists(args.csv_file):
        print(f"ERROR: CSV file '{args.csv_file}' not found!")
        print(f"Make sure to run the benchmark script first to generate results.")
        sys.exit(1)
    
    # Read CSV and discover solvers
    analyses = []
    solver_names = []
    
    try:
        with open(args.csv_file, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Discover solver names from headers
            solver_names = discover_solvers(reader.fieldnames)
            
            if not solver_names:
                available_headers = [h for h in reader.fieldnames if '_time' in h]
                print("ERROR: No solver columns found in CSV file!")
                print(f"Expected columns with patterns: {{solver_name}}_objective, {{solver_name}}_solver_time, and {{solver_name}}_total_time")
                if available_headers:
                    print(f"Available time columns: {', '.join(available_headers)}")
                sys.exit(1)
            
            time_label = "Total Time" if args.time_metric == 'total' else "Solver Time"
            print(f"Discovered {len(solver_names)} solvers: {', '.join([format_solver_name(s) for s in solver_names])}")
            print(f"Primary Analysis Metric: {time_label}")
            print("Note: Solver time deviations >1% and >1ms will be flagged regardless of primary metric.")
            
            for row in reader:
                analysis = analyze_row(row, solver_names, args.time_metric)
                analyses.append(analysis)
                
    except Exception as e:
        print(f"ERROR reading CSV file: {e}")
        sys.exit(1)
    
    if not analyses:
        print("No data found in CSV file!")
        sys.exit(1)
    
    # Print results
    print_detailed_analysis(analyses, solver_names, args.show_failed)
    print_summary_table(analyses, solver_names)
    calculate_overall_stats(analyses, solver_names)
    
    print(f"\nAnalyzed {len(analyses)} problems from {args.csv_file}")

if __name__ == "__main__":
    main() 
