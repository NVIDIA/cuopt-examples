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
Benchmark Results Analyzer for cuOpt Programs

This script analyzes the results from cuopt_benchmark_results.csv and provides:
- Which solver was fastest for each problem (based on total time including overhead)
- Whether objective values are consistent across solvers
- Percentage differences in total times compared to the fastest solver
- Solver time analysis and flags for interfaces with >5% solver time deviation (ignoring ≤1ms differences)

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
    Discover solver names from CSV headers by looking for *_objective and *_total_time patterns.
    
    Args:
        headers: List of CSV column headers
        
    Returns:
        List of solver names found
    """
    solvers = set()
    
    for header in headers:
        if header.endswith('_objective'):
            solver_name = header[:-10]  # Remove '_objective'
            # Check if total_time column exists (minimum requirement)
            if f"{solver_name}_process_total_time" in headers:
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
    
    # Extract solver results with new detailed timing structure
    solvers = {}
    for solver_name in solver_names:
        solvers[solver_name] = {
            'objective': row.get(f'{solver_name}_objective'),
            'interface_overhead': row.get(f'{solver_name}_interface_overhead'),
            'cuopt_solver_time': row.get(f'{solver_name}_cuopt_solver_time'),
            'process_total_time': row.get(f'{solver_name}_process_total_time'),
            'reported_solver_time': row.get(f'{solver_name}_reported_solver_time'),  # For comparison
            'marker_total_time': row.get(f'{solver_name}_marker_total_time')  # Marker-based total time
        }
    
    # Convert string values to float, handle empty/None values
    for solver_name, data in solvers.items():
        try:
            data['objective'] = float(data['objective']) if data['objective'] and data['objective'].strip() else None
            data['interface_overhead'] = float(data['interface_overhead']) if data['interface_overhead'] and data['interface_overhead'].strip() else None
            data['cuopt_solver_time'] = float(data['cuopt_solver_time']) if data['cuopt_solver_time'] and data['cuopt_solver_time'].strip() else None
            data['process_total_time'] = float(data['process_total_time']) if data['process_total_time'] and data['process_total_time'].strip() else None
            data['reported_solver_time'] = float(data['reported_solver_time']) if data['reported_solver_time'] and data['reported_solver_time'].strip() else None
            data['marker_total_time'] = float(data['marker_total_time']) if data['marker_total_time'] and data['marker_total_time'].strip() else None
        except (ValueError, TypeError):
            data['objective'] = None
            data['interface_overhead'] = None
            data['cuopt_solver_time'] = None
            data['process_total_time'] = None
            data['reported_solver_time'] = None
            data['marker_total_time'] = None
    
    # Find solvers that completed successfully (need objective and total_time at minimum)
    successful_solvers = {name: data for name, data in solvers.items() 
                         if data['objective'] is not None and data['process_total_time'] is not None}
    
    # Find solvers with detailed timing data (interface_overhead and cuopt_solver_time)
    detailed_timing_solvers = {name: data for name, data in successful_solvers.items()
                              if data['interface_overhead'] is not None and data['cuopt_solver_time'] is not None}
    
    analysis = {
        'filename': filename,
        'solvers': solvers,
        'successful_solvers': list(successful_solvers.keys()),
        'failed_solvers': [name for name in solvers.keys() if name not in successful_solvers],
        'detailed_timing_solvers': list(detailed_timing_solvers.keys()),  # Solvers with detailed timing data
        'fastest_solver_by_total': None,
        'fastest_solver_by_cuopt': None,  # Fastest by cuOpt solver time
        'fastest_solver_by_interface': None,  # Fastest by interface overhead
        'objective_consistent': None,
        'objective_values': [],
        'total_time_differences': {},
        'cuopt_solver_time_differences': {},
        'interface_overhead_differences': {},
        'fastest_total_time': None,
        'fastest_cuopt_solver_time': None,
        'fastest_interface_overhead': None,
        'time_metric': time_metric
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
    
    # Find fastest solver by total time and calculate differences
    total_times = [(name, data['process_total_time']) for name, data in successful_solvers.items()]
    total_times.sort(key=lambda x: x[1])
    
    analysis['fastest_solver_by_total'] = total_times[0][0]
    analysis['fastest_total_time'] = total_times[0][1]
    
    # Calculate total time differences
    fastest_total_time = total_times[0][1]
    for name, data in successful_solvers.items():
        if data['process_total_time'] != fastest_total_time:
            pct_diff = ((data['process_total_time'] - fastest_total_time) / fastest_total_time) * 100
            analysis['total_time_differences'][name] = pct_diff
        else:
            analysis['total_time_differences'][name] = 0.0
    
    # Analyze detailed timing data if available
    if detailed_timing_solvers:
        # Find fastest solver by cuOpt solver time
        cuopt_times = [(name, data['cuopt_solver_time']) for name, data in detailed_timing_solvers.items()]
        cuopt_times.sort(key=lambda x: x[1])
        
        analysis['fastest_solver_by_cuopt'] = cuopt_times[0][0]
        analysis['fastest_cuopt_solver_time'] = cuopt_times[0][1]
        
        # Calculate cuOpt solver time differences
        fastest_cuopt_time = cuopt_times[0][1]
        for name, data in detailed_timing_solvers.items():
            if data['cuopt_solver_time'] != fastest_cuopt_time:
                pct_diff = ((data['cuopt_solver_time'] - fastest_cuopt_time) / fastest_cuopt_time) * 100
                analysis['cuopt_solver_time_differences'][name] = pct_diff
            else:
                analysis['cuopt_solver_time_differences'][name] = 0.0
        
        # Find fastest solver by interface overhead (lowest is best)
        interface_times = [(name, data['interface_overhead']) for name, data in detailed_timing_solvers.items()]
        interface_times.sort(key=lambda x: x[1])
        
        analysis['fastest_solver_by_interface'] = interface_times[0][0]
        analysis['fastest_interface_overhead'] = interface_times[0][1]
        
        # Calculate interface overhead differences
        fastest_interface_time = interface_times[0][1]
        for name, data in detailed_timing_solvers.items():
            if data['interface_overhead'] != fastest_interface_time:
                pct_diff = ((data['interface_overhead'] - fastest_interface_time) / fastest_interface_time) * 100
                analysis['interface_overhead_differences'][name] = pct_diff
            else:
                analysis['interface_overhead_differences'][name] = 0.0
    
    analysis['status'] = 'SUCCESS'
    return analysis

def format_solver_name(name: str) -> str:
    """Format solver name for display."""
    # Known mappings for common solvers
    name_map = {
        'cuopt_json_to_c_api': 'C API',
        'cuopt_json_to_python_api': 'Python',
        'cuopt_json_to_cvxpy': 'CVXPY',
        'cuopt_json_to_pulp': 'PuLP',
        'cuopt_json_to_ampl': 'AMPL',
        'cuopt_json_to_julia': 'Julia',
        'cuopt_json_to_gams': 'GAMS'
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
        
    print("DETAILED BENCHMARK ANALYSIS")
    print("=" * 80)
    print("Primary Metric: Total Time (overhead included)")
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
            fastest = analysis['fastest_solver_by_total']
            fastest_counts[fastest] = fastest_counts.get(fastest, 0) + 1
            
            # Only count cuOpt solver time if detailed timing is available
            if analysis['fastest_solver_by_cuopt']:
                fastest_cuopt_time = analysis['fastest_solver_by_cuopt']
                fastest_solver_time_counts[fastest_cuopt_time] = fastest_solver_time_counts.get(fastest_cuopt_time, 0) + 1
            
            if not analysis['objective_consistent']:
                objective_inconsistent += 1
            
            # Note: solver_time_deviations no longer exists in new structure
            # We could add logic here to check cuOpt solver time deviations if needed
    
    print(f"\nFASTEST SOLVER SUMMARY (total time):")
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
        print(f"\n⚠️  WARNING: {problems_with_solver_time_deviations} problems had interfaces with >5% solver time deviation!")
        print("   This suggests potential interface inefficiencies beyond just overhead.")
    else:
        print(f"\n✅ All interfaces had consistent solver times (within 1 millisecond or 5% of best)")
    
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
        fastest = analysis['fastest_solver_by_total']
        fastest_time = analysis['fastest_total_time']
        
        print(f"   🏆 Fastest total time: {format_solver_name(fastest)} ({fastest_time:.6f}s)")
        
        # Show detailed timing if available
        if analysis['fastest_solver_by_cuopt']:
            fastest_cuopt_solver = analysis['fastest_solver_by_cuopt']
            fastest_cuopt_time = analysis['fastest_cuopt_solver_time']
            print(f"   ⚡ Fastest cuOpt solver time: {format_solver_name(fastest_cuopt_solver)} ({fastest_cuopt_time:.6f}s)")
            
            fastest_interface_solver = analysis['fastest_solver_by_interface'] 
            fastest_interface_time = analysis['fastest_interface_overhead']
            print(f"   🔗 Lowest interface overhead: {format_solver_name(fastest_interface_solver)} ({fastest_interface_time:.6f}s)")
            
            # Show cuOpt call overhead (marker time vs reported time)
            print(f"   ⚙️  cuOpt Call Overhead (Marker vs Reported Time):")
            for solver in sorted(analysis['detailed_timing_solvers']):
                solver_data = analysis['solvers'][solver]
                if solver_data['reported_solver_time'] is not None:
                    marker_time = solver_data['cuopt_solver_time']
                    reported_time = solver_data['reported_solver_time']
                    overhead = marker_time - reported_time
                    overhead_pct = (overhead / reported_time) * 100 if reported_time > 0 else 0
                    print(f"      {format_solver_name(solver):<15}: {marker_time:.6f}s vs {reported_time:.6f}s (+{overhead_pct:.1f}%)")
        
        # Flag cuOpt solver time deviations (if detailed timing available)
        if analysis['fastest_solver_by_cuopt'] and analysis['cuopt_solver_time_differences']:
            # Check for significant deviations (>5%)
            significant_deviations = {solver: diff for solver, diff in analysis['cuopt_solver_time_differences'].items() 
                                    if diff > 5.0}
            if significant_deviations:
                print(f"   🚨 cuOpt solver time deviations >5%:")
                for solver in sorted(significant_deviations.keys()):
                    deviation = significant_deviations[solver]
                    cuopt_time = analysis['solvers'][solver]['cuopt_solver_time']
                    print(f"      {format_solver_name(solver):<15}: +{deviation:6.1f}% ({cuopt_time:.6f}s)")
        
        if len(analysis['successful_solvers']) > 1:
            print(f"   📊 Total Time differences:")
            # Sort solvers by name for consistent ordering
            sorted_solvers = sorted(analysis['successful_solvers'])
            for solver in sorted_solvers:
                pct_diff = analysis['total_time_differences'][solver]
                solver_data = analysis['solvers'][solver]
                solver_total_time = solver_data['process_total_time']
                
                # Calculate overhead based on available data
                if solver_data['cuopt_solver_time'] and solver_data['interface_overhead']:
                    # For detailed timing: overhead = interface overhead
                    overhead = solver_data['interface_overhead']
                    overhead_pct = (overhead / solver_data['cuopt_solver_time']) * 100 if solver_data['cuopt_solver_time'] > 0 else 0
                elif solver_data['reported_solver_time']:
                    # For old structure: overhead = total - reported_solver_time
                    overhead = solver_total_time - solver_data['reported_solver_time']
                    overhead_pct = (overhead / solver_data['reported_solver_time']) * 100 if solver_data['reported_solver_time'] > 0 else 0
                else:
                    overhead = 0
                    overhead_pct = 0
                
                if pct_diff == 0.0:
                    print(f"      {format_solver_name(solver):<15}: 0.0% ({solver_total_time:.6f}s, overhead: {overhead:.6f}s/{overhead_pct:.1f}%)")
                else:
                    print(f"      {format_solver_name(solver):<15}: +{pct_diff:6.1f}% ({solver_total_time:.6f}s, overhead: {overhead:.6f}s/{overhead_pct:.1f}%)")

def print_summary_table(analyses: List[Dict], solver_names: List[str]):
    """Print a concise summary table."""
    
    successful_analyses = [a for a in analyses if a['status'] == 'SUCCESS']
    if not successful_analyses:
        return
    
    print(f"\nSUMMARY TABLE (Total Time)")
    print("=" * 120)
    print(f"{'Problem':<20} {'Fastest':<12} {'Obj OK':<7} {'SolverT Dev':<11} {'Total Time Differences':<60}")
    print("-" * 120)
    
    for analysis in successful_analyses:
        filename = analysis['filename'][:19]  # Truncate long names
        fastest = format_solver_name(analysis['fastest_solver_by_total'])[:11]
        obj_ok = "✅" if analysis['objective_consistent'] else "❌"
        
        # Show cuOpt solver time deviation flag (if available)
        has_deviations = False
        if analysis['fastest_solver_by_cuopt'] and analysis['cuopt_solver_time_differences']:
            has_deviations = any(diff > 5.0 for diff in analysis['cuopt_solver_time_differences'].values())
        solver_dev = "🚨" if has_deviations else "✅"
        
        # Build time difference string - include ALL solvers in consistent order
        time_diffs = []
        # Sort solvers by name for consistent ordering across problems
        sorted_solvers = sorted(analysis['successful_solvers'])
        for solver in sorted_solvers:
            pct_diff = analysis['total_time_differences'][solver]
            if pct_diff == 0.0:
                time_diffs.append(f"{format_solver_name(solver)}: 0.0%")
            else:
                time_diffs.append(f"{format_solver_name(solver)}: +{pct_diff:.1f}%")
        
        time_diff_str = ", ".join(time_diffs)[:59]  # Truncate if too long
        
        print(f"{filename:<20} {fastest:<12} {obj_ok:<7} {solver_dev:<11} {time_diff_str:<60}")

def print_failure_analysis(analyses: List[Dict], solver_names: List[str]):
    """Print detailed analysis of solver failures."""
    
    if not analyses:
        return
    
    print(f"\nFAILURE ANALYSIS")
    print("=" * 70)
    
    # Collect failure statistics for each solver
    solver_failures = {solver: [] for solver in solver_names}
    total_problems = len(analyses)
    
    for analysis in analyses:
        for solver in solver_names:
            if solver in analysis['failed_solvers']:
                solver_failures[solver].append(analysis['filename'])
    
    # Check if any failures occurred
    any_failures = any(len(failures) > 0 for failures in solver_failures.values())
    
    if not any_failures:
        print("✅ No solver failures detected - all solvers succeeded on all problems!")
        return
    
    print("SOLVER FAILURE SUMMARY:")
    print("-" * 50)
    
    # Sort solvers by failure count for better readability
    solvers_by_failures = sorted(solver_names, key=lambda s: len(solver_failures[s]), reverse=True)
    
    for solver in solvers_by_failures:
        failure_count = len(solver_failures[solver])
        success_count = total_problems - failure_count
        success_rate = (success_count / total_problems) * 100
        
        if failure_count == 0:
            print(f"{format_solver_name(solver):<15}: ✅ {success_count}/{total_problems} successes ({success_rate:.1f}%)")
        else:
            print(f"{format_solver_name(solver):<15}: ❌ {failure_count}/{total_problems} failures ({success_rate:.1f}% success rate)")
    
    # Detail failed problems for each solver that had failures
    print(f"\nDETAILED FAILURE BREAKDOWN:")
    print("-" * 50)
    
    for solver in solvers_by_failures:
        failures = solver_failures[solver]
        if failures:
            print(f"\n{format_solver_name(solver)} failed on {len(failures)} problem(s):")
            # Sort filenames for consistent output
            for filename in sorted(failures):
                print(f"  - {filename}")

def calculate_overall_stats(analyses: List[Dict], solver_names: List[str]):
    """Calculate and print overall statistics."""
    
    successful_analyses = [a for a in analyses if a['status'] == 'SUCCESS']
    if not successful_analyses:
        return
    
    
    print(f"\nOVERALL PERFORMANCE STATISTICS")
    print("=" * 70)
    
    # Initialize speedup statistics for all discovered solvers
    solver_speedups = {solver: [] for solver in solver_names}
    solver_time_speedups = {solver: [] for solver in solver_names}
    overhead_stats = {solver: [] for solver in solver_names}
    overhead_calculation_method = {solver: None for solver in solver_names}  # Track calculation method
    
    for analysis in successful_analyses:
        fastest_total_time = analysis['fastest_total_time']
        
        for solver in analysis['successful_solvers']:
            # Total time speedups
            solver_total_time = analysis['solvers'][solver]['process_total_time']
            speedup_factor = solver_total_time / fastest_total_time
            solver_speedups[solver].append(speedup_factor)
            
            # cuOpt solver time speedups (if available)
            if analysis['fastest_cuopt_solver_time'] and analysis['solvers'][solver]['cuopt_solver_time']:
                cuopt_time = analysis['solvers'][solver]['cuopt_solver_time']
                cuopt_speedup_factor = cuopt_time / analysis['fastest_cuopt_solver_time']
                solver_time_speedups[solver].append(cuopt_speedup_factor)
            
            # Overhead calculation based on available data
            if analysis['solvers'][solver]['interface_overhead'] is not None:
                # Use interface overhead for detailed timing
                overhead_pct = (analysis['solvers'][solver]['interface_overhead'] / analysis['solvers'][solver]['cuopt_solver_time']) * 100 if analysis['solvers'][solver]['cuopt_solver_time'] > 0 else 0
                overhead_calculation_method[solver] = 'markers'  # Using detailed timing markers
            elif analysis['solvers'][solver]['reported_solver_time'] is not None:
                # Use old structure for overhead calculation
                reported_solver_time = analysis['solvers'][solver]['reported_solver_time']
                overhead = solver_total_time - reported_solver_time
                overhead_pct = (overhead / reported_solver_time) * 100 if reported_solver_time > 0 else 0
                overhead_calculation_method[solver] = 'fallback'  # Using total_time - reported_solver_time
            else:
                overhead_pct = 0
                overhead_calculation_method[solver] = 'none'  # No calculation possible
            overhead_stats[solver].append(overhead_pct)
    
    print(f"Total Time Performance:")
    print("-" * 50)
    # Sort by average speedup (lowest to highest)
    solver_performance = []
    for solver in solver_names:
        speedups = solver_speedups[solver]
        if speedups:
            avg_speedup = statistics.mean(speedups)
            median_speedup = statistics.median(speedups)
            solver_performance.append((solver, avg_speedup, median_speedup))
    
    solver_performance.sort(key=lambda x: x[1])  # Sort by average speedup
    for solver, avg_speedup, median_speedup in solver_performance:
        print(f"{format_solver_name(solver):<15}: Avg {avg_speedup:.2f}x, Median {median_speedup:.2f}x relative to fastest")
    
    # Reported Solver Time Analysis - shows cuOpt-reported solve times to identify modeling issues
    reported_solver_times = {solver: [] for solver in solver_names}
    
    for analysis in successful_analyses:
        for solver in analysis['successful_solvers']:
            solver_data = analysis['solvers'][solver]
            if solver_data['reported_solver_time'] is not None:
                reported_solver_times[solver].append(solver_data['reported_solver_time'])
    
    # Only show reported solver time table if there's data
    if any(reported_solver_times.values()):
        print(f"\nReported Solver Time Analysis (cuOpt backend solve times):")
        print("-" * 60)
        
        # Calculate statistics for each solver
        solver_stats = []
        for solver in solver_names:
            times = reported_solver_times[solver]
            if times:
                avg_time = statistics.mean(times)
                median_time = statistics.median(times)
                solver_stats.append((solver, avg_time, median_time))
        
        # Sort by average reported time to identify outliers
        solver_stats.sort(key=lambda x: x[1])
        
        for solver, avg_time, median_time in solver_stats:
            print(f"{format_solver_name(solver):<15}: Avg {avg_time:.4f}s, Median {median_time:.4f}s")
        
        print("\nNote: Large differences may indicate modeling/representation issues in interface code,")
        print("      as all interfaces use the same cuOpt backend solver.")
    
    # Only show solver time performance if any solver has timing marker data
    if any(solver_time_speedups[solver] for solver in solver_names):
        print(f"\nSolve() Time Performance (time in Solve() vs Fastest time in Solve()):")
        print("-" * 50)
        # Sort by average speedup (lowest to highest)
        solver_time_performance = []
        for solver in solver_names:
            speedups = solver_time_speedups[solver]
            if speedups:
                avg_speedup = statistics.mean(speedups)
                median_speedup = statistics.median(speedups)
                solver_time_performance.append((solver, avg_speedup, median_speedup))
        
        solver_time_performance.sort(key=lambda x: x[1])  # Sort by average speedup
        for solver, avg_speedup, median_speedup in solver_time_performance:
            print(f"{format_solver_name(solver):<15}: Avg {avg_speedup:.2f}x, Median {median_speedup:.2f}x relative to fastest")
    
    print(f"\nInterface Overhead Analysis:")
    print("-" * 50)
    # Sort by average overhead (lowest to highest)
    overhead_performance = []
    for solver in solver_names:
        overheads = overhead_stats[solver]
        if overheads:
            avg_overhead = statistics.mean(overheads)
            median_overhead = statistics.median(overheads)
            
            # Add indicator based on calculation method
            method = overhead_calculation_method.get(solver, 'none')
            if method == 'markers':
                indicator = "(M)"  # Using detailed timing markers
            elif method == 'fallback':
                indicator = "(T)"  # Using total_time - reported_solver_time
            else:
                indicator = "(N)"  # No calculation possible
            
            overhead_performance.append((solver, avg_overhead, median_overhead, indicator))
    
    overhead_performance.sort(key=lambda x: x[1])  # Sort by average overhead
    for solver, avg_overhead, median_overhead, indicator in overhead_performance:
        print(f"{format_solver_name(solver):<15}: Avg {avg_overhead:.1f}%, Median {median_overhead:.1f}% overhead {indicator}")
    
    print("\nOverhead calculation methods:")
    print("  (M) = Setup/teardown time - time in Solve()   (T) = Total time - reported solve time   (N) = No data")
    
    # Marker Time vs cuOpt Reported Time Analysis - only show if timing markers exist
    cuopt_call_overhead_stats = {solver: [] for solver in solver_names}
    
    for analysis in successful_analyses:
        for solver in analysis['successful_solvers']:
            solver_data = analysis['solvers'][solver]
            # Only analyze if we have both marker-based cuopt time and cuopt-reported time
            if (solver_data['cuopt_solver_time'] is not None and 
                solver_data['reported_solver_time'] is not None):
                
                marker_time = solver_data['cuopt_solver_time']
                reported_time = solver_data['reported_solver_time']
                
                # Calculate overhead within cuOpt call itself
                cuopt_call_overhead = marker_time - reported_time
                cuopt_call_overhead_pct = (cuopt_call_overhead / reported_time) * 100 if reported_time > 0 else 0
                cuopt_call_overhead_stats[solver].append(cuopt_call_overhead_pct)
    
    # Only print the cuOpt call overhead table if there's data to show
    if any(cuopt_call_overhead_stats.values()):
        print(f"\ncuOpt Call Overhead Analysis (Time in Solve() vs cuOpt Reported Solve Time):")
        print("-" * 70)
        
        # Sort by average overhead (lowest to highest)
        cuopt_overhead_performance = []
        for solver in solver_names:
            overheads = cuopt_call_overhead_stats[solver]
            if overheads:
                avg_overhead = statistics.mean(overheads)
                median_overhead = statistics.median(overheads)
                cuopt_overhead_performance.append((solver, avg_overhead, median_overhead))
        
        cuopt_overhead_performance.sort(key=lambda x: x[1])  # Sort by average overhead
        for solver, avg_overhead, median_overhead in cuopt_overhead_performance:
            print(f"{format_solver_name(solver):<15}: Avg {avg_overhead:.1f}%, Median {median_overhead:.1f}% overhead within cuOpt call")
        
        print("\nNote: This measures overhead between when cuOptSolve() is called and returns")
        print("      vs the solve time cuOpt internally reports. Includes CUDA setup, data transfer, etc.")

def main():
    """Main analysis function."""
    
    parser = argparse.ArgumentParser(
        description='Analyze cuOpt benchmark results',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python analyze_benchmark_results.py                           # Use default CSV file
  python analyze_benchmark_results.py results.csv              # Use specified CSV file
  python analyze_benchmark_results.py --show-failed            # Include failed problems in output

Note: The script analyzes total time performance as the primary metric. 
Solver time deviations >5% are flagged regardless of the primary metric.
        """
    )
    
    parser.add_argument(
        'csv_file', 
        nargs='?', 
        default='cuopt_benchmark_results.csv',
        help='CSV file to analyze (default: cuopt_benchmark_results.csv)'
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
                print(f"Expected columns with patterns: {{solver_name}}_objective and {{solver_name}}_total_time")
                if available_headers:
                    print(f"Available time columns: {', '.join(available_headers)}")
                sys.exit(1)
            
            print(f"Discovered {len(solver_names)} solvers: {', '.join([format_solver_name(s) for s in solver_names])}")
            print(f"Primary Analysis Metric: Total Time")
            print("Note: Solver time deviations >5% and >1ms will be flagged regardless of primary metric.")
            
            for row in reader:
                analysis = analyze_row(row, solver_names, 'total')
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
    print_failure_analysis(analyses, solver_names)
    calculate_overall_stats(analyses, solver_names)
    
    print(f"\nAnalyzed {len(analyses)} problems from {args.csv_file}")

if __name__ == "__main__":
    main()
