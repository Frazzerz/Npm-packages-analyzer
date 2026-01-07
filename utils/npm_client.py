from pathlib import Path
from typing import Dict, Optional
from git import Repo
import requests
import subprocess
import os
from .logging_utils import OutputTarget, synchronized_print
from models import VersionEntry, SourceType

class NPMClient:
    """Cloning Git repos associated with a pkg and retrieving ordered tags"""
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
    
    # No more used
    def get_package_git_url(self) -> Optional[str]:
        """Extracts and normalizes the Git repository URL for an NPM package"""
        '''
        try:
            # Asks NPM for package metadata and gets the repository URL
            result = subprocess.run(
                ['npm', 'view', package_name, 'repository.url', '--json'],
                capture_output=True,
                text=True,
                check=True
            )
            git_url = json.loads(result.stdout.strip())
        '''
        data = self.get_npm_package_data()
        if not data:
            return None
        
        git_url = data.get('repository', {}).get('url', '')
        if not git_url:
            return None

        # Remove common prefixes
        prefixes = ["git+https://", "git+ssh://", "git://", "git+","ssh://git@", "http://"]

        for prefix in prefixes:
            if git_url.startswith(prefix):
                git_url = git_url[len(prefix):]
        
        # Remove any fragment (#readme, #master, etc.)
        git_url = git_url.split('#')[0]
        
        # For GitHub URLs
        if 'github.com' in git_url:
            # Ensure it starts with https://
            if not git_url.startswith('https://'):
                git_url = f'https://{git_url}'
            # Ensure it ends with .git
            if not git_url.endswith('.git'):
                git_url = f'{git_url}.git'
        git_url = git_url.rstrip('/')
        
        return git_url

    # No more used
    def clone_package_repo(self, repos_dir: Path = Path("repos")) -> Optional[Repo]:
        """Clone an NPM package's Git repository in the `repos/` directory. If the repository has already been cloned previously, reuse it"""
        
        git_url = self.get_package_git_url()
        if not git_url:
            print(f"No Git URL found for {self.pkg_name}")
            return None
        
        repos_dir.mkdir(exist_ok=True)
        repo_name = self.pkg_name.replace('/', '_')
        repo_path = repos_dir / repo_name

        # Reuse the repository if it already exists
        if repo_path.exists() and (repo_path / ".git").exists():
            print(f"Existing repository found for {self.pkg_name}")
            return Repo(repo_path)

        try:
            
            # Set environment variables to prevent interactive authentication
            #env = os.environ.copy()
            #env['GIT_TERMINAL_PROMPT'] = '0'  # Disable interactive prompt
            #env['GIT_ASKPASS'] = 'echo'       # Return empty password
            synchronized_print(f"Cloning repository for {self.pkg_name} from {git_url}...")
            '''
            # Clone with GitPython, no timeout
            repo = Repo.clone_from(git_url, repo_path)
            synchronized_print(f"Repository cloned for {self.pkg_name}")
            return repo
            '''
            # Clone with subprocess, with timeout
            result = subprocess.run(
                ['git', 'clone', git_url, str(repo_path)],
                capture_output=True,
                text=True,
                timeout=120, # seconds
                env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'}
            )
            if result.returncode == 0:
                synchronized_print(f"Repository cloned for {self.pkg_name}")
                return Repo(repo_path)

        except Exception as e:
            
            error_msg = str(e).lower()
            if 'authentication' in error_msg or 'credentials' in error_msg:
                print(f"Repository for {self.pkg_name} requires authentication")
            elif 'timed out' in error_msg:
                print(f"Cloning repository for {self.pkg_name} timed out")
            else:
                print(f"Error cloning {self.pkg_name}: {e}")
            # Alternative tests could be done to try to download it via other means

            # Clean up partial clone if it exists
            if repo_path.exists():
                import shutil
                try:
                    shutil.rmtree(repo_path)
                except:
                    pass    
            return None
        
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
        versions = list(data['versions'].keys())[-20:] # Get the last 20 versions, if more exist. No error if less. Assuming they are in order

        pkg_dir = download_dir / self.pkg_name.replace('/', '_')
        pkg_dir.mkdir(parents=True, exist_ok=True)
        synchronized_print(f"Downloading tarballs for {self.pkg_name} {len(versions)} versions...")

        for version in versions:
            version_data = data['versions'][version]
            tarball_url = version_data.get('dist', {}).get('tarball', '')
            if not tarball_url:
                synchronized_print(f"No tarball URL for version {version} of {self.pkg_name}", target=OutputTarget.FILE_ONLY)
                continue

            tarball_path = pkg_dir / f"{version}.tgz"
            if tarball_path.exists():
                synchronized_print(f"Tarball already downloaded for {self.pkg_name} version {version}", target=OutputTarget.FILE_ONLY)
                continue
            
            try:
                #synchronized_print(f"Downloading tarball for {self.pkg_name} version {version}...")
                response = requests.get(tarball_url, timeout=10)
                response.raise_for_status()
                
                with open(tarball_path, 'wb') as f:
                    f.write(response.content)
                
                synchronized_print(f"Downloaded tarball for {self.pkg_name} version {version}", target=OutputTarget.FILE_ONLY)

            except Exception as e:
                synchronized_print(f"Error downloading tarball for {self.pkg_name} version {version}: {e}", target=OutputTarget.FILE_ONLY)

        synchronized_print(f"Finished downloading tarballs for {self.pkg_name}")        
        extract_dir = download_dir / self.pkg_name.replace('/', '_') / "extracted" 
        extract_dir.mkdir(parents=True, exist_ok=True)
        entries = []
        for version in versions:
            tarball_path = pkg_dir / f"{version}.tgz"
            if tarball_path.exists():
                entries.append(self.extract_tarball(tarball_path, extract_dir))
        synchronized_print(f"Extracted tarballs for {self.pkg_name}", target=OutputTarget.FILE_ONLY)
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