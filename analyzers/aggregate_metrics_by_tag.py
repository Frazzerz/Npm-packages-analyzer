from zipfile import Path
from models.composed_metrics import FileMetrics, VersionMetrics
from typing import List
from analyzers.categories import AccountAnalyzer
from utils import synchronized_print
from models import CodeType, SourceType

class AggregateMetricsByTag:

    @staticmethod
    def aggregate_metrics_by_tag(metrics_list: List[FileMetrics], repo_path: Path, source: SourceType) -> VersionMetrics:
        """Aggregation of all metrics from the all files in the current version into a single VersionMetrics object"""

        if not metrics_list:
            synchronized_print("Warning: Empty metrics list provided to aggregate_metrics_by_tag")
            return None

        version_metrics = VersionMetrics()
        version_metrics.package = metrics_list[0].package
        #version_metrics.version = str(metrics_list[0].version) # Ensure it's a string, not a git.refs.tag.TagReference
        version_metrics.version = metrics_list[0].version # Ensure it's a string, not a git.refs.tag.TagReference


        # Calculate metrics for account categories
        account = AccountAnalyzer()#(pkg_name=version_metrics.package)
        account_metrics = account.analyze(version_metrics.version, repo_path, source)
        version_metrics.account.npm_maintainers = account_metrics.npm_maintainers
        version_metrics.account.npm_hash_commit = account_metrics.npm_hash_commit
        #version_metrics.account.github_hash_commit = account_metrics.github_hash_commit
        version_metrics.account.npm_release_date = account_metrics.npm_release_date
    
        # Calculate total file sizes for weighted averages
        for fm in metrics_list:
                # Filter for deobfuscated files, I don't consider the deobfuscated files for these metrics below
                if fm.evasion.code_type != CodeType.DEOBFUSCATED:
                    version_metrics.generic.total_size_chars += fm.generic.size_chars
                    version_metrics.evasion.code_types.append(fm.evasion.code_type)
                    version_metrics.generic.total_files += 1
                    version_metrics.generic.total_size_bytes += fm.generic.size_bytes
                    version_metrics.generic.longest_line_length = max(version_metrics.generic.longest_line_length, fm.generic.longest_line_length)

        for fm in metrics_list:
            version_metrics.evasion.obfuscation_patterns_count += fm.evasion.obfuscation_patterns_count
            version_metrics.evasion.platform_detections_count += fm.evasion.platform_detections_count
            
            version_metrics.payload.timing_delays_count += fm.payload.timing_delays_count
            version_metrics.payload.eval_count += fm.payload.eval_count
            version_metrics.payload.shell_commands_count += fm.payload.shell_commands_count
            version_metrics.payload.preinstall_scripts.extend(fm.payload.preinstall_scripts)

            version_metrics.exfiltration.scan_functions_count += fm.exfiltration.scan_functions_count
            version_metrics.exfiltration.sensitive_elements_count += fm.exfiltration.sensitive_elements_count
            version_metrics.exfiltration.data_transmission_count += fm.exfiltration.data_transmission_count

            version_metrics.crypto.crypto_addresses += fm.crypto.crypto_addresses
            version_metrics.crypto.list_crypto_addresses.extend(fm.crypto.list_crypto_addresses)
            version_metrics.crypto.cryptocurrency_name += fm.crypto.cryptocurrency_name
            version_metrics.crypto.wallet_detection += fm.crypto.wallet_detection
            version_metrics.crypto.replaced_crypto_addresses += fm.crypto.replaced_crypto_addresses
            version_metrics.crypto.hook_provider += fm.crypto.hook_provider
            
            # weighted averages
            if fm.evasion.code_type != CodeType.DEOBFUSCATED:
                # To calculate the average blank space ratio for the version, we need to calculate the weighted average based on character size,
                # so a larger file will have a larger weight on average
                version_metrics.generic.weighted_avg_blank_space_and_character_ratio += fm.generic.blank_space_and_character_ratio * fm.generic.size_chars / version_metrics.generic.total_size_chars if version_metrics.generic.total_size_chars > 0 else 0.0
                # To calculate the shannon entropy of the version, we need to calculate the weighted average based on character size,
                # represent the average information content per character in the version
                version_metrics.generic.weighted_avg_shannon_entropy += fm.generic.shannon_entropy * fm.generic.size_chars / version_metrics.generic.total_size_chars if version_metrics.generic.total_size_chars > 0 else 0.0

        # Remove duplicates in lists (set function)
        version_metrics.evasion.code_types = list(set(version_metrics.evasion.code_types))

        return version_metrics