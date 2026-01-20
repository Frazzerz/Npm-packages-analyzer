from pathlib import Path
from typing import Dict, Optional
import requests
from .logging_utils import synchronized_print
from models import VersionEntry, SourceType
from packaging.version import parse as parse_version
from packaging.version import InvalidVersion, Version
class NPMClient:
    def __init__(self, registry_url: str = "https://registry.npmjs.org", pkg_name: str = ""):
        self.pkg_name = pkg_name
        self.registry_url = registry_url
    
    def get_npm_package_data(self) -> Optional[Dict]:
        """Fetch raw metadata for an NPM package by making an HTTP request to the registry"""
        try:
            response = requests.get(f'{self.registry_url}/{self.pkg_name}', timeout=5)
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch '{self.pkg_name}': {e}")
            return None
        
    def get_last_20_valid_versions(self, data: dict) -> list[str]:
        valid_versions = []

        for v in data["versions"].keys():
            try:
                valid_versions.append(Version(v))
            except InvalidVersion:
                # discard versions that are not always compatible
                continue

        if len(valid_versions) < 20:
            return []

        valid_versions.sort()
        return [str(v) for v in valid_versions[-20:]]
        
    def download_package_versions_tarball(self, download_dir: Path = Path("tarballs")) -> list[VersionEntry]:
        """Download the tarball for 20 lastest versions of the package from NPM registry"""
        data = self.get_npm_package_data()
        if not data or 'versions' not in data:
            synchronized_print(f"No version data found for {self.pkg_name}")
            return None
        
        if len(data['versions']) == 0:
            synchronized_print(f"No versions found for {self.pkg_name}")
            return None
        
        if len(data['versions']) < 20:
            synchronized_print(f"Not enough versions for analysis, for {self.pkg_name}, found only {len(data['versions'])} versions. Skipping package.")
            return None
        
        if len(data['versions']) >= 20:
            synchronized_print(f"Found {len(data['versions'])} versions for {self.pkg_name}, but i consider only the last 20")
        #versions = list(data['versions'].keys())[-20:] # Get the last 20 versions. If more exist, no error
        versions = self.get_last_20_valid_versions(data)

        if not versions:
            synchronized_print(f"Not enough valid semantic versions for {self.pkg_name}. Skipping package.")
            return None

        pkg_dir = download_dir / self.pkg_name.replace('/', '_')
        pkg_dir.mkdir(parents=True, exist_ok=True)
        synchronized_print(f"Downloading tarballs for {self.pkg_name} {len(versions)} versions...")

        for version in versions:
            version_data = data['versions'][version]
            tarball_url = version_data.get('dist', {}).get('tarball', '')
            if not tarball_url:
                synchronized_print(f"No tarball URL for version {version} of {self.pkg_name}")
                continue

            tarball_path = pkg_dir / f"{version}.tgz"
            if tarball_path.exists():
                synchronized_print(f"Tarball already downloaded for {self.pkg_name} version {version}")
                continue
            
            try:
                #synchronized_print(f"Downloading tarball for {self.pkg_name} version {version}...")
                response = requests.get(tarball_url, timeout=10)
                response.raise_for_status()
                
                with open(tarball_path, 'wb') as f:
                    f.write(response.content)
                
                synchronized_print(f"Downloaded tarball for {self.pkg_name} version {version}")

            except Exception as e:
                synchronized_print(f"Error downloading tarball for {self.pkg_name} version {version}: {e}")

        synchronized_print(f"Finished downloading tarballs for {self.pkg_name}")        
        extract_dir = download_dir / self.pkg_name.replace('/', '_') / "extracted" 
        extract_dir.mkdir(parents=True, exist_ok=True)
        entries = []
        for version in versions:
            tarball_path = pkg_dir / f"{version}.tgz"
            if tarball_path.exists():
                entries.append(self.extract_tarball(tarball_path, extract_dir))
        synchronized_print(f"Extracted tarballs for {self.pkg_name}")
        return entries

    def extract_tarball(self, tarball_path: Path, extract_dir: Path) -> VersionEntry:
        """Extracts a tarball to a specified directory"""
        if not tarball_path.exists():
            print(f"Tarball {tarball_path} does not exist")
            return None
        
        extract_path = extract_dir / tarball_path.stem
        extract_path.mkdir(parents=True, exist_ok=True)

        try:
            import tarfile
            with tarfile.open(tarball_path, 'r:gz') as tar:
                tar.extractall(path=extract_path)
            #synchronized_print(f"Extracted {tarball_path} to {extract_path}")
            return VersionEntry(name=tarball_path.stem, source=SourceType.TARBALL, ref=extract_path)
        except Exception as e:
            print(f"Error extracting {tarball_path}: {e}")
            return None
    
    def order_versions(self, entries: list[VersionEntry]) -> list[VersionEntry]:
        """Order entries by semantic version. If any version is not parseable, discard the whole package."""
        try:
            ordered = sorted(entries, key=lambda e: parse_version(e.name))
            return ordered
        except InvalidVersion:
            # invalid version -> discard the entire pkg
            raise
        except AttributeError as e:
            # missing the version attribute
            raise
        except Exception as e:
            # any other error -> same behavior
            raise