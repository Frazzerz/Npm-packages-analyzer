from pathlib import Path
from typing import List
import multiprocessing as mp
from models.composed_metrics import FileMetrics, VersionMetrics
from reporters import CSVReporter
from utils import FileHandler, synchronized_print, FileTypeDetector, OutputTarget
from .code_analyzer import CodeAnalyzer
from models import SourceType, VersionEntry
class VersionAnalyzer:
    """Handles analysis of versions from a Git repository and local versions"""
    def __init__(self, max_processes: int = 1, include_local: bool = False, local_versions_dir: str = "./local_versions", package_name: str = "", output_dir: Path = Path(".")):
        self.package_name = package_name
        self.output_dir = output_dir
        self.code_analyzer = CodeAnalyzer()
        self.max_processes = max_processes
        self.include_local = include_local
        self.local_versions_dir = local_versions_dir
        self.entries: List[VersionEntry] = []

    def _find_package_root(self, extract_path: Path) -> Path:
        """Find the actual package root directory inside the extracted tarball"""
        # "package" folder is the standard root for npm packages
        package_dir = extract_path / "package"
        if package_dir.exists() and package_dir.is_dir() and (package_dir / "package.json").exists():
            return package_dir
        
        # If not found, look for the first subdirectory that contains package.json
        for item in extract_path.iterdir():
            if item.is_dir() and (item / "package.json").exists():
                synchronized_print(f"    Found package root: {item.name}", target=OutputTarget.TERMINAL_ONLY) #FILE_ONLY
                return item
         
        raise FileNotFoundError(f"Could not find package.json in {extract_path} or any of its subdirectories")
    
    def analyze_versions(self) -> None:
        """Analyze all versions"""
        if not self.entries:
            synchronized_print(f"No versions to analyze for {self.package_name}")
            return

        for i, entry in enumerate(self.entries):
            synchronized_print(f"  [{i+1}/{len(self.entries)}] Analyzing tag {entry.name}")
            try: 
                repo_path = self._find_package_root(entry.ref)      # entry.ref is the path to the extracted local version

                # curr_metrics is the list of FileMetrics for all files in the current version
                # current_metrics e.g. list[FileMetrics(package='example', version='1.0.0', file_path='index.js', ...), FileMetrics(...), ...]
                curr_metrics = self._analyze_version(entry.name, repo_path, entry.source)
                #if curr_metrics == -1:
                #    break
                synchronized_print(f"    {len(curr_metrics)} files present in version analyzed.")
                # aggregate_metrics_by_tag is the aggregation of all metrics from the all files in the current version
                # aggregate_metrics_by_tag e.g. VersionMetrics(package='example', version='1.0.0', code_types=['Clear', ...], obfuscation_patterns_count=5, ...)
                aggregate_metrics_by_tag = self.aggregate_metrics_by_tag(curr_metrics, repo_path, entry.source)

                # Incremental save detailed metrics for the current tag
                all_metrics_csv = self.output_dir / "file_metrics.csv"
                aggregate_metrics_csv = self.output_dir / "aggregate_metrics_by_single_version.csv"
                CSVReporter.save_csv(all_metrics_csv, curr_metrics)
                CSVReporter.save_csv(aggregate_metrics_csv, aggregate_metrics_by_tag)
            except FileNotFoundError as e:
                synchronized_print(f"Skipping tag {entry.name}: {e}")
                return
            except Exception as e:
                synchronized_print(f"Error analyzing tag {entry.name}: {e}")
                return
        return

    def _analyze_version(self, version: str, package_dir: Path, source: SourceType) -> List[FileMetrics]:
        """Analyze all files of a specific Git version"""
        #try:
        files = FileHandler().get_all_files(package_dir)
        #except TooManyFilesError as e:
        #    synchronized_print(f"    {e}. Skipping analysis...")
        #    return -1
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
        '''
        import time
        start = time.time()
        try:
            synchronized_print(f"[START] Analyzing {file_path.name}")
            result = self._analyze_single_file(file_path, version, package_dir, source)
            elapsed = time.time() - start
            synchronized_print(f"[DONE] {file_path.name} in {elapsed:.2f}s")
            return result
        except Exception as e:
            synchronized_print(f"[ERROR] {file_path.name}: {e}")
            return None
        '''
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
    

    def aggregate_metrics_by_tag(self, metrics_list: List[FileMetrics], repo_path: Path, source: SourceType) -> VersionMetrics:
        """Aggregation of all metrics from the all files in the current version into a single VersionMetrics object"""

        if not metrics_list:
            synchronized_print("Warning: blank metrics list provided to aggregate_metrics_by_tag")
            return None
        
        version_metrics = VersionMetrics()
        version_metrics.package = metrics_list[0].package
        version_metrics.version = metrics_list[0].version # Ensure it's a string, not a git.refs.tag.TagReference

        # Calculate total_number_of_characters and total_number_of_characters_no_comments first for weighted averages
        for fm in metrics_list:
                version_metrics.generic.total_number_of_characters += fm.generic.number_of_characters
                version_metrics.generic.total_number_of_characters_no_comments += fm.generic.number_of_characters_no_comments
        
        for fm in metrics_list:
            version_metrics.generic.total_files += 1
            version_metrics.generic.list_file_types.append(fm.generic.file_type)
            version_metrics.generic.total_dim_bytes_pkg += fm.generic.size_bytes
            if (FileTypeDetector.is_valid_file_for_analysis(fm.generic.file_type)):
                version_metrics.generic.total_plain_text_files += 1
                version_metrics.generic.total_dim_plain_text_files += fm.generic.size_bytes
            else:
                version_metrics.generic.total_other_files += 1
                version_metrics.generic.total_dim_bytes_other_files += fm.generic.size_bytes

            version_metrics.generic.total_number_of_non_blank_lines += fm.generic.total_number_of_non_blank_lines
            version_metrics.generic.total_number_of_comments += fm.generic.number_of_comments
            version_metrics.generic.total_number_of_non_blank_lines_no_comments += fm.generic.number_of_non_blank_lines_no_comments
            if fm.file_path != "README.md":
                version_metrics.generic.longest_line_length_no_comments = max(version_metrics.generic.longest_line_length_no_comments, fm.generic.longest_line_length_no_comments)
            version_metrics.generic.code_types.append(fm.generic.code_type)
            version_metrics.generic.total_number_of_printable_characters += fm.generic.number_of_printable_characters
            version_metrics.generic.total_number_of_printable_characters_no_comments += fm.generic.number_of_printable_characters_no_comments
            version_metrics.generic.total_number_of_whitespace_characters += fm.generic.number_of_whitespace_characters
            version_metrics.generic.total_number_of_whitespace_characters_no_comments += fm.generic.number_of_whitespace_characters_no_comments

            version_metrics.evasion.obfuscation_patterns_count += fm.evasion.obfuscation_patterns_count
            version_metrics.evasion.list_obfuscation_patterns.extend(fm.evasion.list_obfuscation_patterns)
            version_metrics.evasion.platform_detections_count += fm.evasion.platform_detections_count
            version_metrics.evasion.list_platform_detections.extend(fm.evasion.list_platform_detections)
            
            version_metrics.payload.timing_delays_count += fm.payload.timing_delays_count
            version_metrics.payload.list_timing_delays.extend(fm.payload.list_timing_delays)
            version_metrics.payload.eval_count += fm.payload.eval_count
            version_metrics.payload.list_eval.extend(fm.payload.list_eval)
            version_metrics.payload.shell_commands_count += fm.payload.shell_commands_count
            version_metrics.payload.list_shell_commands.extend(fm.payload.list_shell_commands)
            version_metrics.payload.preinstall_scripts.extend(fm.payload.preinstall_scripts)    # only one element

            version_metrics.exfiltration.scan_functions_count += fm.exfiltration.scan_functions_count
            version_metrics.exfiltration.list_scan_functions.extend(fm.exfiltration.list_scan_functions)
            version_metrics.exfiltration.sensitive_elements_count += fm.exfiltration.sensitive_elements_count
            version_metrics.exfiltration.list_sensitive_elements.extend(fm.exfiltration.list_sensitive_elements)
            version_metrics.exfiltration.data_transmission_count += fm.exfiltration.data_transmission_count
            version_metrics.exfiltration.list_data_transmissions.extend(fm.exfiltration.list_data_transmissions)

            version_metrics.crypto.crypto_addresses += fm.crypto.crypto_addresses
            version_metrics.crypto.list_crypto_addresses.extend(fm.crypto.list_crypto_addresses)
            version_metrics.crypto.cryptocurrency_name += fm.crypto.cryptocurrency_name
            version_metrics.crypto.list_cryptocurrency_names.extend(fm.crypto.list_cryptocurrency_names)
            version_metrics.crypto.wallet_detection += fm.crypto.wallet_detection
            version_metrics.crypto.replaced_crypto_addresses += fm.crypto.replaced_crypto_addresses
            version_metrics.crypto.hook_provider += fm.crypto.hook_provider
            
            # weighted averages
            # To calculate the shannon entropy of the version, we need to calculate the weighted average based on character size,
            # represent the average information content per character in the version
            version_metrics.generic.weighted_avg_shannon_entropy_original += fm.generic.shannon_entropy_original * fm.generic.number_of_characters / version_metrics.generic.total_number_of_characters if version_metrics.generic.total_number_of_characters > 0 else 0.0
            version_metrics.generic.weighted_avg_shannon_entropy_no_comments += fm.generic.shannon_entropy_no_comments * fm.generic.number_of_characters_no_comments / version_metrics.generic.total_number_of_characters_no_comments if version_metrics.generic.total_number_of_characters_no_comments > 0 else 0.0
            # To calculate the average blank space ratio for the version, we need to calculate the weighted average based on character size,
            # so a larger file will have a larger weight on average
            version_metrics.generic.weighted_avg_blank_space_and_character_ratio_original += fm.generic.blank_space_and_character_ratio_original * fm.generic.number_of_characters / version_metrics.generic.total_number_of_characters if version_metrics.generic.total_number_of_characters > 0 else 0.0
            version_metrics.generic.weighted_avg_blank_space_and_character_ratio_no_comments += fm.generic.blank_space_and_character_ratio_no_comments * fm.generic.number_of_characters_no_comments / version_metrics.generic.total_number_of_characters_no_comments if version_metrics.generic.total_number_of_characters_no_comments > 0 else 0.0
            
        # Remove duplicates in lists (set function)
        version_metrics.generic.list_file_types = list(set(version_metrics.generic.list_file_types))
        version_metrics.generic.code_types = list(set(version_metrics.generic.code_types))
        
        version_metrics.evasion.list_obfuscation_patterns = list(set(version_metrics.evasion.list_obfuscation_patterns))
        version_metrics.evasion.list_platform_detections = list(set(version_metrics.evasion.list_platform_detections))

        version_metrics.payload.list_timing_delays = list(set(version_metrics.payload.list_timing_delays))
        version_metrics.payload.list_eval = list(set(version_metrics.payload.list_eval))
        version_metrics.payload.list_shell_commands = list(set(version_metrics.payload.list_shell_commands))

        version_metrics.exfiltration.list_scan_functions = list(set(version_metrics.exfiltration.list_scan_functions))
        version_metrics.exfiltration.list_sensitive_elements = list(set(version_metrics.exfiltration.list_sensitive_elements))
        version_metrics.exfiltration.list_data_transmissions = list(set(version_metrics.exfiltration.list_data_transmissions))
        
        version_metrics.crypto.list_crypto_addresses = list(set(version_metrics.crypto.list_crypto_addresses))
        version_metrics.crypto.list_cryptocurrency_names = list(set(version_metrics.crypto.list_cryptocurrency_names))
        
        # Compute unique lengths
        version_metrics.generic.len_list_file_types_unique = len(version_metrics.generic.list_file_types)
        version_metrics.generic.len_list_code_types_unique = len(version_metrics.generic.code_types)

        version_metrics.evasion.len_list_obfuscation_patterns_unique = len(version_metrics.evasion.list_obfuscation_patterns)
        version_metrics.evasion.len_list_platform_detections_unique = len(version_metrics.evasion.list_platform_detections)

        version_metrics.payload.len_list_timing_delays_unique = len(version_metrics.payload.list_timing_delays)
        version_metrics.payload.len_list_eval_unique = len(version_metrics.payload.list_eval)
        version_metrics.payload.len_list_shell_commands_unique = len(version_metrics.payload.list_shell_commands)

        version_metrics.exfiltration.len_list_scan_functions_unique = len(version_metrics.exfiltration.list_scan_functions)
        version_metrics.exfiltration.len_list_sensitive_elements_unique = len(version_metrics.exfiltration.list_sensitive_elements)
        version_metrics.exfiltration.len_list_data_transmissions_unique = len(version_metrics.exfiltration.list_data_transmissions)
        
        version_metrics.crypto.len_list_crypto_addresses_unique = len(version_metrics.crypto.list_crypto_addresses)
        version_metrics.crypto.len_list_cryptocurrency_names_unique = len(version_metrics.crypto.list_cryptocurrency_names)

        # Deltas
        version_metrics.generic.entropy_delta = version_metrics.generic.weighted_avg_shannon_entropy_original - version_metrics.generic.weighted_avg_shannon_entropy_no_comments
        version_metrics.generic.blank_space_ratio_delta = version_metrics.generic.weighted_avg_blank_space_and_character_ratio_original - version_metrics.generic.weighted_avg_blank_space_and_character_ratio_no_comments

        return version_metrics