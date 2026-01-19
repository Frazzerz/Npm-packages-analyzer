import argparse
from multiprocessing import cpu_count
from pathlib import Path
from datetime import datetime
from utils import FileHandler, setup_logging, close_logging, synchronized_print
from analyze_single_package import analyze_single_package
import time

def main():
    parser = argparse.ArgumentParser(description='Analyzer npm package releases')
    parser.add_argument('--json', required=True)
    parser.add_argument('--output', default='analysis_results', help='Output directory (default: analysis_results)')
    parser.add_argument('--workers', type=int, default=cpu_count(), help=f'Number of workers (default: {cpu_count()})')
    parser.add_argument('--log', default='log.txt', help='Log file (default: log.txt)')
    parser.add_argument('--local', action='store_true', help='Include local versions from local_versions directory (default: False)')
    parser.add_argument('--local-dir', default='./local_versions', help='Directory for local versions (default: ./local_versions)')
    parser.add_argument('--delete-analysis', action='store_true', help='Delete previous analysis results before running (default: False)')
    args = parser.parse_args()

    if args.delete_analysis:
        FileHandler.delete_previous_analysis()
    
    # Setup logging system
    setup_logging(Path(args.log))
    
    try:
        synchronized_print(f"=== LOG ANALYSIS STARTED {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
        
        packages = FileHandler.load_packages_from_json(args.json)
        if not packages:
            raise SystemExit("Error: No package in JSON file")

        synchronized_print('NORMAL WORLD NPM PACKAGE ANALYZER')
        synchronized_print(f'Packages to analyze: {len(packages)}')
        synchronized_print(f'Worker(s): {args.workers}')
        synchronized_print(f'Output directory: {args.output}')
        synchronized_print(f'Include local versions: {args.local}')
        if args.local:
            synchronized_print(f'Local versions directory: {args.local_dir}')
        synchronized_print(f'Log: {args.log}')
        synchronized_print('=' * 50)

        Path(args.output).mkdir(parents=True, exist_ok=True)

        start_time = time.time()
        for i, pkg in enumerate(packages):
            analyze_single_package(pkg, args.output, i+1, len(packages), args.local, args.local_dir, args.workers)
        
        total_time = time.time() - start_time
        synchronized_print(f'=== ANALYSIS COMPLETED. Total time: {total_time:.1f}s ===')
        synchronized_print(f"=== LOG ANALYSIS ENDED {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")

    finally:
        close_logging()

if __name__ == '__main__':
    main()