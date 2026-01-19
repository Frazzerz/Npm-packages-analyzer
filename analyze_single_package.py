from pathlib import Path
import time
from analyzers import PackageAnalyzer
from utils import FileHandler, synchronized_print

def analyze_single_package(package: str, out_dir: str, package_index: int, total_packages: int, include_local: bool, local_dir: str, workers: int) -> None:
    """Analyze a single npm package"""
    pkg_dir = Path(out_dir) / package.replace('/', '_')
    pkg_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.time()
    synchronized_print(f"[{package_index}/{total_packages}] Analyzing {package}...")
    
    analyzer = PackageAnalyzer(include_local=include_local, local_versions_dir=local_dir, workers=workers, package_name=package, output_dir=pkg_dir)
    analyzer.analyze_package()
    
    FileHandler().delete_exctracted_dir(package)

    elapsed_time = time.time() - start_time
    synchronized_print(f"[{package_index}/{total_packages}] Completed: {package} ({elapsed_time:.1f}s)")