import argparse
from multiprocessing import cpu_count
import sys
from pathlib import Path
from datetime import datetime
from utils import TeeOutput, FileHandler
from analyze_single_package import analyze_single_package
import time

def main():
    parser = argparse.ArgumentParser(description='Analyzer npm package releases')
    parser.add_argument('--json', required=True)
    parser.add_argument('--output', default='analysis_results', help='Output directory (default: analysis_results)')
    parser.add_argument('--workers', type=int, default=cpu_count(), help=f'Number of workers (default: {cpu_count()})')
    parser.add_argument('--log', default='log.txt', help='Log file (default: log.txt)')
    parser.add_argument('--delete-analysis', action='store_true', help='Delete previous analysis results before running (default: False)')
    args = parser.parse_args()

    if args.delete_analysis:
        FileHandler.delete_previous_analysis()
    
    # setup log
    original_stdout = sys.stdout
    log_path = Path(args.log)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = TeeOutput(log_path)
    sys.stdout = log_file
    print(f"=== LOG ANALYSIS STARTED {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")

    try:
        packages = FileHandler.load_packages_from_json(args.json)
        if not packages:
            raise SystemExit("Error: No package in JSON file")

        print('NORMAL WORLD NPM PACKAGE ANALYZER')
        print(f'Packages to analyze: {len(packages)}')
        print(f'Worker(s): {args.workers}')
        print(f'Output directory: {args.output}')
        if args.log:
            print(f'Log: {args.log}')
        print('=' * 50)

        Path(args.output).mkdir(parents=True, exist_ok=True)

        start_time = time.time()
        for i, pkg in enumerate(packages):
            analyze_single_package(pkg, args.output, i+1, len(packages), args.workers)
        
        total_time = time.time() - start_time
        print(f'=== ANALYSIS COMPLETED. Total time: {total_time:.1f}s ===')

    finally:
        if args.log:
            print(f"=== LOG ANALYSIS ENDED {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
            sys.stdout = original_stdout
            log_file.close()

if __name__ == '__main__':
    main()