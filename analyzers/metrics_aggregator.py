from typing import List
from models.composed_metrics import FileMetrics, VersionMetrics
from utils import synchronized_print
from models import CodeType

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
        
        # Calculate character totals for weighted averages
        totals = MetricsAggregator._calculate_character_totals(metrics_list)
        
        # Aggregate all metrics
        for fm in metrics_list:
            MetricsAggregator._aggregate_generic_metrics(version_metrics, fm, totals)
            MetricsAggregator._aggregate_evasion_metrics(version_metrics, fm)
            MetricsAggregator._aggregate_payload_metrics(version_metrics, fm)
            MetricsAggregator._aggregate_exfiltration_metrics(version_metrics, fm)
            MetricsAggregator._aggregate_crypto_metrics(version_metrics, fm)
        
        # Post-processing: remove duplicates and compute unique counts
        MetricsAggregator._finalize_metrics(version_metrics)
        
        return version_metrics
    
    @staticmethod
    def _calculate_character_totals(metrics_list: List[FileMetrics]) -> dict:
        """Calculate total character counts for different file variants.
            These totals are used as denominators in weighted average calculations.
            
            Returns dictionary with 6 variants:
            - original: all files as-is
            - no_comments: JS/TS files without comments
            - with_unminified: minified files replaced with their unminified version
            - only_minified: only minified files (original)
            - only_unminified: only minified files after unminification
            - no_minified: only clear files, excludes minified"""
        
        totals = {
            'original': 0,
            'no_comments': 0,
            'with_unminified': 0,
            'only_minified': 0,
            'only_unminified': 0,
            'no_minified': 0,
        }

        has_any_comment = any(fm.generic.number_of_comments > 0 for fm in metrics_list)
        has_any_minified = any(fm.generic.code_type == CodeType.MINIFIED for fm in metrics_list)
        
        for fm in metrics_list:
            # 1. Original: all characters including comments
            totals['original'] += fm.generic.number_of_characters
            
            # 2. No comments: all characters after comment removal
            totals['no_comments'] += fm.generic.number_of_characters_no_comments
            
            # 3. With unminified: use unminified version for minified files, original for others
            if fm.generic.code_type == CodeType.MINIFIED:
                totals['with_unminified'] += fm.generic.number_of_characters_no_comments_unminified
            else:
                totals['with_unminified'] += fm.generic.number_of_characters_no_comments
            
            # 4. Only minified: only count minified files (original)
            if fm.generic.code_type == CodeType.MINIFIED:
                totals['only_minified'] += fm.generic.number_of_characters_no_comments
            
            # 5. Only unminified: only count minified files after unminification
            if fm.generic.code_type == CodeType.MINIFIED:
                totals['only_unminified'] += fm.generic.number_of_characters_no_comments_unminified
            
            # 6. No minified: only clear files, not minified
            if fm.generic.code_type != CodeType.MINIFIED:
                totals['no_minified'] += fm.generic.number_of_characters_no_comments
            
        if not has_any_comment:
            totals['no_comments'] = 0

        if not has_any_minified:
            totals['with_unminified'] = 0
            totals['only_minified'] = 0
            totals['only_unminified'] = 0
            
        return totals
    
    @staticmethod
    def _aggregate_generic_metrics(vm: VersionMetrics, fm: FileMetrics, totals: dict):
        """Aggregate generic metrics including weighted averages"""
        
        # === Basic Counts ===
        vm.generic.total_files += 1
        vm.generic.list_file_types.append(fm.generic.file_type)
        vm.generic.total_dim_bytes_pkg += fm.generic.size_bytes
        vm.generic.total_number_of_characters += fm.generic.number_of_characters
        vm.generic.total_number_of_characters_no_comments += fm.generic.number_of_characters_no_comments
        
        # Plain text vs other files
        if fm.generic.is_plain_text_file:
            vm.generic.total_plain_text_files += 1
            vm.generic.total_dim_plain_text_files += fm.generic.size_bytes
            vm.generic.list_plain_text_files.append(fm.file_path)
        else:
            vm.generic.total_other_files += 1
            vm.generic.total_dim_bytes_other_files += fm.generic.size_bytes
            vm.generic.list_other_files.append(fm.file_path)
        
        # Line counts
        vm.generic.total_number_of_non_blank_lines += fm.generic.total_number_of_non_blank_lines
        vm.generic.total_number_of_comments += fm.generic.number_of_comments
        vm.generic.total_number_of_non_blank_lines_no_comments += fm.generic.number_of_non_blank_lines_no_comments
        
        # Longest line (exclude README.md)
        if fm.file_path != "README.md":
            vm.generic.longest_line_length_no_comments = max(vm.generic.longest_line_length_no_comments, fm.generic.longest_line_length_no_comments)
            
        if fm.generic.code_type == CodeType.MINIFIED:
            vm.generic.longest_line_length_no_comments_only_minified = max(
                vm.generic.longest_line_length_no_comments_only_minified,
                fm.generic.longest_line_length_no_comments
            )
            vm.generic.total_number_of_printable_characters_no_comments_only_minified += fm.generic.number_of_printable_characters_no_comments
            vm.generic.total_number_of_whitespace_characters_no_comments_only_minified += fm.generic.number_of_whitespace_characters_no_comments
        else:
            vm.generic.longest_line_length_no_comments_no_minified = max(
                vm.generic.longest_line_length_no_comments_no_minified,
                fm.generic.longest_line_length_no_comments
            )
            vm.generic.total_number_of_printable_characters_no_comments_no_minified += fm.generic.number_of_printable_characters_no_comments
            vm.generic.total_number_of_whitespace_characters_no_comments_no_minified += fm.generic.number_of_whitespace_characters_no_comments
        
        # Code types
        vm.generic.code_types.append(fm.generic.code_type)
        
        # Character counts (printable + whitespace)
        vm.generic.total_number_of_printable_characters += fm.generic.number_of_printable_characters
        vm.generic.total_number_of_printable_characters_no_comments += fm.generic.number_of_printable_characters_no_comments
        vm.generic.total_number_of_whitespace_characters += fm.generic.number_of_whitespace_characters
        vm.generic.total_number_of_whitespace_characters_no_comments += fm.generic.number_of_whitespace_characters_no_comments
        
        # === Weighted Averages ===
        
        # 1. Original (with comments)
        if totals['original'] > 0:
            weight = fm.generic.number_of_characters / totals['original']
            vm.generic.weighted_avg_shannon_entropy_original += fm.generic.shannon_entropy_original * weight
            vm.generic.weighted_avg_blank_space_and_character_ratio_original += fm.generic.blank_space_and_character_ratio_original * weight
        
        # 2. No comments
        if totals['no_comments'] > 0:
            weight = fm.generic.number_of_characters_no_comments / totals['no_comments']
            vm.generic.weighted_avg_shannon_entropy_no_comments += fm.generic.shannon_entropy_no_comments * weight
            vm.generic.weighted_avg_blank_space_and_character_ratio_no_comments += fm.generic.blank_space_and_character_ratio_no_comments * weight
        
        # 3. With unminified (minified files use their unminified version)
        if totals['with_unminified'] > 0:
            if fm.generic.code_type == CodeType.MINIFIED:
                # Use unminified metrics and character count
                chars = fm.generic.number_of_characters_no_comments_unminified
                entropy = fm.generic.shannon_entropy_no_comments_unminified
                ws_ratio = fm.generic.blank_space_and_character_ratio_no_comments_unminified
            else:
                # Use regular no_comments metrics
                chars = fm.generic.number_of_characters_no_comments
                entropy = fm.generic.shannon_entropy_no_comments
                ws_ratio = fm.generic.blank_space_and_character_ratio_no_comments
            
            weight = chars / totals['with_unminified']
            vm.generic.weighted_avg_shannon_entropy_no_comments_with_unminified += entropy * weight
            vm.generic.weighted_avg_blank_space_and_character_ratio_no_comments_with_unminified += ws_ratio * weight
        
        # 4. Only minified (original minified files)
        if fm.generic.code_type == CodeType.MINIFIED and totals['only_minified'] > 0:
            weight = fm.generic.number_of_characters_no_comments / totals['only_minified']
            vm.generic.weighted_avg_shannon_entropy_no_comments_only_minified += fm.generic.shannon_entropy_no_comments * weight
            vm.generic.weighted_avg_blank_space_and_character_ratio_no_comments_only_minified += fm.generic.blank_space_and_character_ratio_no_comments * weight
        
        # 5. Only unminified (minified files after beautification)
        if fm.generic.code_type == CodeType.MINIFIED and totals['only_unminified'] > 0:
            weight = fm.generic.number_of_characters_no_comments_unminified / totals['only_unminified']
            vm.generic.weighted_avg_shannon_entropy_no_comments_only_unminified += fm.generic.shannon_entropy_no_comments_unminified * weight
            vm.generic.weighted_avg_blank_space_and_character_ratio_no_comments_only_unminified += fm.generic.blank_space_and_character_ratio_no_comments_unminified * weight
        
        # 6. No minified (only clear files)
        if fm.generic.code_type != CodeType.MINIFIED and totals['no_minified'] > 0:
            weight = fm.generic.number_of_characters_no_comments / totals['no_minified']
            vm.generic.weighted_avg_shannon_entropy_no_comments_no_minified += fm.generic.shannon_entropy_no_comments * weight
            vm.generic.weighted_avg_blank_space_and_character_ratio_no_comments_no_minified += fm.generic.blank_space_and_character_ratio_no_comments * weight
    
    @staticmethod
    def _aggregate_evasion_metrics(vm: VersionMetrics, fm: FileMetrics):
        """Aggregate evasion metrics"""
        vm.evasion.obfuscation_patterns_count += fm.evasion.obfuscation_patterns_count
        vm.evasion.list_obfuscation_patterns.extend(fm.evasion.list_obfuscation_patterns)
        if fm.evasion.possible_obfuscated:
            vm.evasion.list_possible_presence_of_obfuscated_files.extend([fm.file_path])
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
        # Remove duplicates from lists
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
        vm.evasion.len_list_possible_presence_of_obfuscated_files_unique = len(vm.evasion.list_possible_presence_of_obfuscated_files)
        vm.evasion.len_list_platform_detections_unique = len(vm.evasion.list_platform_detections)
        vm.payload.len_list_timing_delays_unique = len(vm.payload.list_timing_delays)
        vm.payload.len_list_eval_unique = len(vm.payload.list_eval)
        vm.payload.len_list_shell_commands_unique = len(vm.payload.list_shell_commands)
        vm.exfiltration.len_list_scan_functions_unique = len(vm.exfiltration.list_scan_functions)
        vm.exfiltration.len_list_sensitive_elements_unique = len(vm.exfiltration.list_sensitive_elements)
        vm.exfiltration.len_list_data_transmissions_unique = len(vm.exfiltration.list_data_transmissions)
        vm.crypto.len_list_crypto_addresses_unique = len(vm.crypto.list_crypto_addresses)
        vm.crypto.len_list_cryptocurrency_names_unique = len(vm.crypto.list_cryptocurrency_names)