from pathlib import Path
from typing import List
import multiprocessing as mp
from models.composed_metrics import FileMetrics, VersionMetrics
from reporters import CSVReporter, TextReporter
from utils import FileHandler, synchronized_print, Deobfuscator
from .aggregate_metrics_by_tag import AggregateMetricsByTag
from .code_analyzer import CodeAnalyzer
from models import SourceType, CodeType
class VersionAnalyzer:
    """Handles analysis of versions from a Git repository and local versions"""
    def __init__(self, max_processes: int = 1, package_name: str = "", output_dir: Path = Path(".")):
        self.package_name = package_name
        self.output_dir = output_dir
        self.code_analyzer = CodeAnalyzer()
        self.max_processes = max_processes
        self.entries = []
    
    def analyze_versions(self) -> None:
        """Analyze all versions"""
        if not self.entries:
            synchronized_print(f"No versions to analyze for {self.package_name}")
            return

        for i, entry in enumerate(self.entries):
            synchronized_print(f"  [{i+1}/{len(self.entries)}] Analyzing tag {entry.name}")
            try:
                repo_path = entry.ref / "package"  # entry.ref is the path to the extracted local version
                
                # curr_metrics is the list of FileMetrics for all files in the current version
                # current_metrics e.g. list[FileMetrics(package='example', version='1.0.0', file_path='index.js', ...), FileMetrics(...), ...]
                curr_metrics = self._analyze_version(entry.name, repo_path, entry.source)
                
                # Identify obfuscated JS files and attempt deobfuscation
                obfuscated_files = [f for f in curr_metrics if f.evasion.code_type == CodeType.OBFUSCATED and f.file_path.endswith('.js')]
                if obfuscated_files:
                    synchronized_print(f"    Found {len(obfuscated_files)} obfuscated js files, trying to deobfuscate it...")
                    for f in obfuscated_files:
                        succ = Deobfuscator.deobfuscate(
                            path_original_file= repo_path / f.file_path,  # e.g. other_versions/extracted/package_name/version/package/index.js
                            package_name=self.package_name,               # e.g. package_name
                            version=entry.name,                           # e.g. version-local
                            file_name=f.file_path                         # e.g. index.js
                        )
                        if not succ:
                            synchronized_print(f"    Deobfuscation failed for file: {f.file_path} in version {entry.name}, skipping analysis of this deobfuscated file.")
                            continue
                        path_dir = Path('deobfuscated_files') / self.package_name / entry.name
                        path_file = path_dir / f.file_path.replace('.js', '-deobfuscated.js')
                        deob = self._analyze_single_file(
                            file_path=path_file,
                            version=entry.name,
                            package_dir=path_dir,
                            source=SourceType.DEOBFUSCATED
                        )
                        curr_metrics.append(deob)
                
                synchronized_print(f"    Analyzed {len(curr_metrics)} files")
                
                # aggregate_metrics_by_tag is the aggregation of all metrics from the all files in the current version
                # aggregate_metrics_by_tag e.g. VersionMetrics(package='example', version='1.0.0', code_types=['Clear', ...], obfuscation_patterns_count=5, ...)
                aggregate_metrics_by_tag = AggregateMetricsByTag().aggregate_metrics_by_tag(curr_metrics, repo_path, entry.source)

                # Incremental save detailed metrics for the current tag
                all_metrics_csv = self.output_dir / "file_metrics.csv"
                aggregate_metrics_csv = self.output_dir / "aggregate_metrics_by_single_version.csv"
                CSVReporter.save_csv(all_metrics_csv, curr_metrics)
                CSVReporter.save_csv(aggregate_metrics_csv, aggregate_metrics_by_tag)

            except Exception as e:
                synchronized_print(f"Error analyzing tag {entry.name}: {e}")

        return

    def _analyze_version(self, version: str, package_dir: Path, source: SourceType) -> List[FileMetrics]:
        """Analyze all files of a specific Git version"""

        files = FileHandler().get_all_files(package_dir)
        if self.max_processes > 1:
            file_results = self._analyze_files_parallel(files, version, package_dir, source)
        else:
            file_results = self._analyze_files_sequential(files, version, package_dir, source)
        
        # Filter out None results (failed analyses)
        valid_results = [r for r in file_results if r is not None]    
        return valid_results

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
        # Prepare arguments for each file
        args_list = []
        for file_path in files:
            args_list.append((file_path, version, package_dir, source))
        
        # Use multiprocessing Pool
        with mp.Pool(processes=self.max_processes) as pool:
            results = pool.starmap(self._analyze_single_file_wrapper, args_list)
        
        return results

    def _analyze_single_file_wrapper(self, file_path: Path, version: str, package_dir: Path, source: SourceType) -> FileMetrics:
        """Wrapper function for parallel execution that handles exceptions"""
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