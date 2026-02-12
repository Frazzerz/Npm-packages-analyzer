from utils import synchronized_print
import os
import re
import tarfile
from pathlib import Path
from typing import List, Dict, Optional
from models import VersionEntry
from models import SourceType

class LocalVersionAnalyzer:
    """Manages loading and extracting local versions"""
    def __init__(self, local_versions_dir: str = "./local_versions", pkg_name: str = ""):
        self.pkg_name = pkg_name
        self.local_versions_dir = Path(local_versions_dir)
        self.local_extract_dir = self.local_versions_dir / "extracted"
        self._local_versions = {}
        
    def setup_local_versions(self) -> None:
        """Sets up local versions for analysis"""
        local_versions = self._get_local_versions_for_package()
        if not local_versions:
            synchronized_print(f"No local versions found for {self.pkg_name}")
            return

        synchronized_print(f"Found {len(local_versions)} local versions for {self.pkg_name}")
        self.local_extract_dir.mkdir(parents=True, exist_ok=True)

        for local_version in local_versions:
            try:
                extracted_path = self._extract_local_version(
                    local_version,
                    self.local_extract_dir
                )
                version_with_suffix = f"{local_version['version']}"
                # test
                #version_with_suffix = f"{local_version['version']}+local"
                #version_with_suffix = f"v{local_version['version']}-local"
                self._local_versions[version_with_suffix] = extracted_path
                #synchronized_print(f"Added local version {version_with_suffix}")
            except Exception as e:
                synchronized_print(f"Error extracting {local_version['filename']}: {e}")

    def _get_local_versions_for_package(self) -> List[Dict]:
        """Finds all local versions for a package"""
        if not self.local_versions_dir.exists():
            return []
        
        target_clean = re.sub(r'[@/_.-]', '', self.pkg_name.lower())
        target_short = self.pkg_name.split('/')[-1].lower().replace('_', '').replace('-', '')
        local_versions = []

        for filename in os.listdir(self.local_versions_dir):
            if not filename.endswith('.tgz'):
                continue
            
            name_without_ext = filename[:-4]
            parsed = self._parse_local_filename(name_without_ext)
            
            if parsed:
                file_package, file_version = parsed
                file_pkg_clean = re.sub(r'[@/_.-]', '', file_package.lower())
                
                if file_pkg_clean == target_clean or file_pkg_clean == target_short:
                    full_path = self.local_versions_dir / filename
                    local_versions.append({
                        'version': file_version,
                        'path': full_path,
                        'filename': filename,
                        'package_detected': file_package
                    })
        
        return local_versions

    def _parse_local_filename(self, filename: str) -> Optional[tuple]:
        """Extracts name and version by searching for the last number block"""
        name = filename.replace('.tgz', '')
        
        match = re.search(r'-(?P<ver>\d+\.\d+\.\d+.*)$', name)        
        if match:
            version = match.group('ver')
            package = name[:match.start()]
            return package, version
        
        if '@' in name:
            parts = name.rsplit('@', 1)
            if len(parts) == 2 and self._is_valid_version(parts[1]):
                return parts[0], parts[1]
                
        return None
    
    def _is_valid_version(self, version_str: str) -> bool:
        """Checks if the string is a valid version"""
        return bool(re.match(r'^\d+\.\d+', version_str))    # Begin with one or more digits, followed by a dot , followed by one or more digits and they may have something else after them
    
    def _extract_local_version(self, local_version_info: Dict, destination_dir: Path) -> Path:
        """Extracts a local version"""
        tgz_path = local_version_info['path']
        version = local_version_info['version']
        package = local_version_info.get('package_detected', 'unknown')
        
        extract_path = destination_dir / f"{package}-{version}-local"
        extract_path.mkdir(parents=True, exist_ok=True)
        
        with tarfile.open(tgz_path, 'r:gz') as tar:
            tar.extractall(path=extract_path)
        
        return extract_path

    def extract_numeric_version(self, version_str: str) -> str:
        """Extract numeric part of version string (e.g., '1.2.3' from 'v1.2.3-candidate')"""
        # Pattern to match version numbers like 1, 1.2, 1.2.3, etc.
        match = re.search(r'(\d+(?:\.\d+)*)', version_str)
        return match.group(1) if match else "0"
    
    def compare_versions(self, v1: str, v2: str) -> int:
        """Compare two version strings. Returns -1 if v1 < v2, 0 if equal, 1 if v1 > v2"""
        v1_num = self.extract_numeric_version(v1)
        v2_num = self.extract_numeric_version(v2)
        
        v1_parts = list(map(int, v1_num.split('.')))
        v2_parts = list(map(int, v2_num.split('.')))
        
        # Compare each numeric part
        for i in range(max(len(v1_parts), len(v2_parts))):
            v1_val = v1_parts[i] if i < len(v1_parts) else 0
            v2_val = v2_parts[i] if i < len(v2_parts) else 0
            
            if v1_val < v2_val:
                return -1
            elif v1_val > v2_val:
                return 1
        
        # If numeric parts are equal, compare the full strings
        # This handles cases like "1.0.0" vs "1.0.0-candidate"
        return -1 if v1 < v2 else (1 if v1 > v2 else 0)

    def unite_versions(self, entries: List[VersionEntry]) -> List[VersionEntry]:
        """Combines tarball and local versions into a single sorted list of VersionEntry"""
        if self._local_versions:
            for l_name, l_path in self._local_versions.items():
                inserted = False
                for i, entry in enumerate(entries):
                    # If the version in the entry is newer than the local version
                    if self.compare_versions(entry.name, l_name) > 0:
                        entries.insert(i, VersionEntry(name=l_name, source=SourceType.LOCAL, ref=l_path))
                        inserted = True
                        break
                
                # It is the most recent version, I add it at the end
                if not inserted:
                    entries.append(VersionEntry(name=l_name, source=SourceType.LOCAL, ref=l_path))

        return entries
        # OLD 
        # I can't use packaging.version here because some versions have a suffix that makes them invalid e.g. 2.1.0-candidate
        # For this reason, I skip the pkg that contains unparseable versions
        #return sorted(entries, key=lambda e: Version(str(e.name)))
        #return sorted(entries, key=lambda e: str(e.name)) # Sort by name as string
    
