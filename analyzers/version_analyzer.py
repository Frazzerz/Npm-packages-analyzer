from pathlib import Path
from typing import List
import multiprocessing as mp
from models.composed_metrics import FileMetrics
from reporters import CSVReporter
from utils import FileHandler, synchronized_print
from .code_analyzer import CodeAnalyzer
from .metrics_aggregator import MetricsAggregator
from models import SourceType, VersionEntry

class VersionAnalyzer:
    """Handles analysis of versions from tarballs and local versions"""    
    def __init__(self, max_processes: int = 1, include_local: bool = False, 
                 local_versions_dir: str = "./local_versions", package_name: str = "", 
                 output_dir: Path = Path(".")):
        self.package_name = package_name
        self.output_dir = output_dir
        self.code_analyzer = CodeAnalyzer()
        self.max_processes = max_processes
        self.include_local = include_local
        self.local_versions_dir = local_versions_dir
        self.entries: List[VersionEntry] = []

    def _find_package_root(self, extract_path: Path) -> Path:
        """Find the actual package root directory inside the extracted tarball"""
        # Standard "package" folder for npm packages
        package_dir = extract_path / "package"
        if package_dir.exists() and package_dir.is_dir() and (package_dir / "package.json").exists():
            return package_dir
        
        # Look for first subdirectory containing package.json
        for item in extract_path.iterdir():
            if item.is_dir() and (item / "package.json").exists():
                synchronized_print(f"    Found package root: {item.name}")
                return item
        
        raise FileNotFoundError(f"Could not find package.json in {extract_path} or subdirectories")
    
    def analyze_versions(self) -> None:
        """Analyze all versions"""
        if not self.entries:
            synchronized_print(f"No versions to analyze for {self.package_name}")
            return

        for i, entry in enumerate(self.entries):
            synchronized_print(f"  [{i+1}/{len(self.entries)}] Analyzing tag {entry.name}")
            try: 
                repo_path = self._find_package_root(entry.ref)
                
                # Analyze all files in version
                curr_metrics = self._analyze_version(entry.name, repo_path, entry.source)
                synchronized_print(f"    {len(curr_metrics)} files analyzed.")
                
                # Aggregate metrics for the version
                aggregate_metrics = MetricsAggregator.aggregate_version_metrics(curr_metrics)

                # Save metrics incrementally
                CSVReporter.save_csv(self.output_dir / "file_metrics.csv", curr_metrics)
                CSVReporter.save_csv(self.output_dir / "aggregate_metrics_by_single_version.csv", aggregate_metrics)
                
            except FileNotFoundError as e:
                synchronized_print(f"Skipping tag {entry.name}: {e}")
                return
            except Exception as e:
                synchronized_print(f"Error analyzing tag {entry.name}: {e}")
                return

    def _analyze_version(self, version: str, package_dir: Path, source: SourceType) -> List[FileMetrics]:
        """Analyze all files of a specific version"""
        files = FileHandler().get_all_files(package_dir)
        
        if self.max_processes > 1:
            file_results = self._analyze_files_parallel(files, version, package_dir, source)
        else:
            file_results = self._analyze_files_sequential(files, version, package_dir, source)
        
        return [r for r in file_results if r is not None]

    def _analyze_files_sequential(self, files: List[Path], version: str, package_dir: Path, source: SourceType) -> List[FileMetrics]:
        """Sequential analysis of files"""
        results = []
        for file_path in files:
            try:
                result = self._analyze_single_file(file_path, version, package_dir, source)
                results.append(result)
            except Exception as e:
                print(f"Error analyzing {file_path}: {e}")
                results.append(None)
        return results

    def _analyze_files_parallel(self, files: List[Path], version: str, package_dir: Path, source: SourceType) -> List[FileMetrics]:
        """Parallel analysis of files"""
        args_list = [(file_path, version, package_dir, source) for file_path in files]
        
        with mp.Pool(processes=self.max_processes) as pool:
            results = pool.starmap(self._analyze_single_file_wrapper, args_list)
        
        return results

    def _analyze_single_file_wrapper(self, file_path: Path, version: str, package_dir: Path, source: SourceType) -> FileMetrics:
        """Wrapper function for parallel execution with error handling"""
        try:
            return self._analyze_single_file(file_path, version, package_dir, source)
        except Exception as e:
            rel_path = file_path.relative_to(package_dir) if package_dir in file_path.parents else file_path
            print(f"Error analyzing {rel_path}: {type(e).__name__}: {e}")
            return None

    def _analyze_single_file(self, file_path: Path, version: str, package_dir: Path, source: SourceType) -> FileMetrics:
        """Analyze a single file"""
        rel_path = str(file_path.relative_to(package_dir))
        package_info = {
            'name': self.package_name,
            'version': version,
            'git_repo_path': str(package_dir),
            'file_name': rel_path,
            'info': source
        }
        return self.code_analyzer.analyze_file(file_path, package_info)