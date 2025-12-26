#!/usr/bin/env python3
"""Benchmark runner script for EduSched."""

import argparse
from datetime import datetime
from edusched.benchmarking.benchmark_runner import BenchmarkRunner, BenchmarkReporter


def main():
    parser = argparse.ArgumentParser(description="Run benchmarks for EduSched solvers")
    parser.add_argument("--output", "-o", type=str, default="benchmark_results", 
                        help="Output directory for benchmark results")
    parser.add_argument("--runs", "-r", type=int, default=5, 
                        help="Number of runs per problem")
    parser.add_argument("--format", "-f", type=str, choices=["json", "text"], default="json",
                        help="Output format for reports")
    
    args = parser.parse_args()
    
    print("Starting EduSched benchmark suite...")
    
    runner = BenchmarkRunner()
    reporter = BenchmarkReporter()
    
    # Generate benchmark problems
    print("Generating benchmark problems...")
    small_problem = runner.problem_generator.generate_small_problem()
    medium_problem = runner.problem_generator.generate_medium_problem()
    large_problem = runner.problem_generator.generate_large_problem()
    
    problems = [small_problem, medium_problem, large_problem]
    
    # Define solver backends to test
    solver_backends = ["heuristic", "genetic"]  # Add "ortools" if available
    
    print(f"Running benchmarks with {args.runs} runs per problem...")
    suite_result = runner.run_benchmark_suite(
        solver_backends=solver_backends,
        problems=problems,
        runs_per_problem=args.runs
    )
    
    # Generate and save reports
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_filename = f"{args.output}/benchmark_{timestamp}.json"
    text_filename = f"{args.output}/benchmark_{timestamp}.txt"
    
    reporter.save_report(suite_result, json_filename, "json")
    reporter.save_report(suite_result, text_filename, "text")
    
    print(f"Benchmark complete! Results saved to {args.output}/")
    print(reporter.generate_text_report(suite_result))


if __name__ == "__main__":
    main()