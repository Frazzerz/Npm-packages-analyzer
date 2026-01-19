from pathlib import Path
from typing import List
from models.composed_metrics import FileMetrics, VersionMetrics
from utils import FileTypeDetector, synchronized_print

class MetricsAggregator:
    """Aggregates file-level metrics into version-level metrics"""
    
    @staticmethod
    def aggregate_version_metrics(metrics_list: List[FileMetrics]) -> VersionMetrics:
        """Aggregate all metrics from files in a version into a single VersionMetrics object"""
        if not metrics_list:
            synchronized_print("Warning: blank metrics list provided to aggregate")
            return None
        
        version_metrics = VersionMetrics()
        version_metrics.package = metrics_list[0].package
        version_metrics.version = metrics_list[0].version
        
        # Calculate totals first (needed for weighted averages)
        total_chars, total_chars_nc = MetricsAggregator._calculate_character_totals(metrics_list)
        
        # Aggregate all metrics
        for fm in metrics_list:
            MetricsAggregator._aggregate_generic_metrics(version_metrics, fm, total_chars, total_chars_nc)
            MetricsAggregator._aggregate_evasion_metrics(version_metrics, fm)
            MetricsAggregator._aggregate_payload_metrics(version_metrics, fm)
            MetricsAggregator._aggregate_exfiltration_metrics(version_metrics, fm)
            MetricsAggregator._aggregate_crypto_metrics(version_metrics, fm)
        
        # Post-processing: remove duplicates and compute unique counts
        MetricsAggregator._finalize_metrics(version_metrics)
        
        return version_metrics
    
    @staticmethod
    def _calculate_character_totals(metrics_list: List[FileMetrics]) -> tuple[int, int]:
        """Calculate total characters for weighted averages"""
        total_chars = sum(fm.generic.number_of_characters for fm in metrics_list)
        total_chars_nc = sum(fm.generic.number_of_characters_no_comments for fm in metrics_list)
        return total_chars, total_chars_nc
    
    @staticmethod
    def _aggregate_generic_metrics(vm: VersionMetrics, fm: FileMetrics, total_chars: int, total_chars_nc: int):
        """Aggregate generic metrics"""
        vm.generic.total_files += 1
        vm.generic.list_file_types.append(fm.generic.file_type)
        vm.generic.total_dim_bytes_pkg += fm.generic.size_bytes
        vm.generic.total_number_of_characters += fm.generic.number_of_characters
        vm.generic.total_number_of_characters_no_comments += fm.generic.number_of_characters_no_comments
        
        if FileTypeDetector.is_valid_file_for_analysis(fm.generic.file_type):
            vm.generic.total_plain_text_files += 1
            vm.generic.total_dim_plain_text_files += fm.generic.size_bytes
        else:
            vm.generic.total_other_files += 1
            vm.generic.total_dim_bytes_other_files += fm.generic.size_bytes
        
        vm.generic.total_number_of_non_blank_lines += fm.generic.total_number_of_non_blank_lines
        vm.generic.total_number_of_comments += fm.generic.number_of_comments
        vm.generic.total_number_of_non_blank_lines_no_comments += fm.generic.number_of_non_blank_lines_no_comments
        
        if fm.file_path != "README.md":
            vm.generic.longest_line_length_no_comments = max(
                vm.generic.longest_line_length_no_comments,
                fm.generic.longest_line_length_no_comments
            )
        
        vm.generic.code_types.append(fm.generic.code_type)
        vm.generic.total_number_of_printable_characters += fm.generic.number_of_printable_characters
        vm.generic.total_number_of_printable_characters_no_comments += fm.generic.number_of_printable_characters_no_comments
        vm.generic.total_number_of_whitespace_characters += fm.generic.number_of_whitespace_characters
        vm.generic.total_number_of_whitespace_characters_no_comments += fm.generic.number_of_whitespace_characters_no_comments
        
        # Weighted averages
        if total_chars > 0:
            weight = fm.generic.number_of_characters / total_chars
            vm.generic.weighted_avg_shannon_entropy_original += fm.generic.shannon_entropy_original * weight
            vm.generic.weighted_avg_blank_space_and_character_ratio_original += fm.generic.blank_space_and_character_ratio_original * weight
        
        if total_chars_nc > 0:
            weight_nc = fm.generic.number_of_characters_no_comments / total_chars_nc
            vm.generic.weighted_avg_shannon_entropy_no_comments += fm.generic.shannon_entropy_no_comments * weight_nc
            vm.generic.weighted_avg_blank_space_and_character_ratio_no_comments += fm.generic.blank_space_and_character_ratio_no_comments * weight_nc
    
    @staticmethod
    def _aggregate_evasion_metrics(vm: VersionMetrics, fm: FileMetrics):
        """Aggregate evasion metrics"""
        vm.evasion.obfuscation_patterns_count += fm.evasion.obfuscation_patterns_count
        vm.evasion.list_obfuscation_patterns.extend(fm.evasion.list_obfuscation_patterns)
        vm.evasion.platform_detections_count += fm.evasion.platform_detections_count
        vm.evasion.list_platform_detections.extend(fm.evasion.list_platform_detections)
    
    @staticmethod
    def _aggregate_payload_metrics(vm: VersionMetrics, fm: FileMetrics):
        """Aggregate payload metrics"""
        vm.payload.timing_delays_count += fm.payload.timing_delays_count
        vm.payload.list_timing_delays.extend(fm.payload.list_timing_delays)
        vm.payload.eval_count += fm.payload.eval_count
        vm.payload.list_eval.extend(fm.payload.list_eval)
        vm.payload.shell_commands_count += fm.payload.shell_commands_count
        vm.payload.list_shell_commands.extend(fm.payload.list_shell_commands)
        vm.payload.preinstall_scripts.extend(fm.payload.preinstall_scripts)
    
    @staticmethod
    def _aggregate_exfiltration_metrics(vm: VersionMetrics, fm: FileMetrics):
        """Aggregate exfiltration metrics"""
        vm.exfiltration.scan_functions_count += fm.exfiltration.scan_functions_count
        vm.exfiltration.list_scan_functions.extend(fm.exfiltration.list_scan_functions)
        vm.exfiltration.sensitive_elements_count += fm.exfiltration.sensitive_elements_count
        vm.exfiltration.list_sensitive_elements.extend(fm.exfiltration.list_sensitive_elements)
        vm.exfiltration.data_transmission_count += fm.exfiltration.data_transmission_count
        vm.exfiltration.list_data_transmissions.extend(fm.exfiltration.list_data_transmissions)
    
    @staticmethod
    def _aggregate_crypto_metrics(vm: VersionMetrics, fm: FileMetrics):
        """Aggregate crypto metrics"""
        vm.crypto.crypto_addresses += fm.crypto.crypto_addresses
        vm.crypto.list_crypto_addresses.extend(fm.crypto.list_crypto_addresses)
        vm.crypto.cryptocurrency_name += fm.crypto.cryptocurrency_name
        vm.crypto.list_cryptocurrency_names.extend(fm.crypto.list_cryptocurrency_names)
        vm.crypto.wallet_detection += fm.crypto.wallet_detection
        vm.crypto.replaced_crypto_addresses += fm.crypto.replaced_crypto_addresses
        vm.crypto.hook_provider += fm.crypto.hook_provider
    
    @staticmethod
    def _finalize_metrics(vm: VersionMetrics):
        """Remove duplicates and compute unique counts"""
        # Remove duplicates
        vm.generic.list_file_types = list(set(vm.generic.list_file_types))
        vm.generic.code_types = list(set(vm.generic.code_types))
        vm.evasion.list_obfuscation_patterns = list(set(vm.evasion.list_obfuscation_patterns))
        vm.evasion.list_platform_detections = list(set(vm.evasion.list_platform_detections))
        vm.payload.list_timing_delays = list(set(vm.payload.list_timing_delays))
        vm.payload.list_eval = list(set(vm.payload.list_eval))
        vm.payload.list_shell_commands = list(set(vm.payload.list_shell_commands))
        vm.exfiltration.list_scan_functions = list(set(vm.exfiltration.list_scan_functions))
        vm.exfiltration.list_sensitive_elements = list(set(vm.exfiltration.list_sensitive_elements))
        vm.exfiltration.list_data_transmissions = list(set(vm.exfiltration.list_data_transmissions))
        vm.crypto.list_crypto_addresses = list(set(vm.crypto.list_crypto_addresses))
        vm.crypto.list_cryptocurrency_names = list(set(vm.crypto.list_cryptocurrency_names))
        
        # Compute unique lengths
        vm.generic.len_list_file_types_unique = len(vm.generic.list_file_types)
        vm.generic.len_list_code_types_unique = len(vm.generic.code_types)
        vm.evasion.len_list_obfuscation_patterns_unique = len(vm.evasion.list_obfuscation_patterns)
        vm.evasion.len_list_platform_detections_unique = len(vm.evasion.list_platform_detections)
        vm.payload.len_list_timing_delays_unique = len(vm.payload.list_timing_delays)
        vm.payload.len_list_eval_unique = len(vm.payload.list_eval)
        vm.payload.len_list_shell_commands_unique = len(vm.payload.list_shell_commands)
        vm.exfiltration.len_list_scan_functions_unique = len(vm.exfiltration.list_scan_functions)
        vm.exfiltration.len_list_sensitive_elements_unique = len(vm.exfiltration.list_sensitive_elements)
        vm.exfiltration.len_list_data_transmissions_unique = len(vm.exfiltration.list_data_transmissions)
        vm.crypto.len_list_crypto_addresses_unique = len(vm.crypto.list_crypto_addresses)
        vm.crypto.len_list_cryptocurrency_names_unique = len(vm.crypto.list_cryptocurrency_names)
        
        # Compute deltas
        vm.generic.entropy_delta = vm.generic.weighted_avg_shannon_entropy_original - vm.generic.weighted_avg_shannon_entropy_no_comments
        vm.generic.blank_space_ratio_delta = vm.generic.weighted_avg_blank_space_and_character_ratio_original - vm.generic.weighted_avg_blank_space_and_character_ratio_no_comments