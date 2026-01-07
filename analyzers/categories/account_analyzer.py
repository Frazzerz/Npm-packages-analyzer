from typing import Dict, Optional
from zipfile import Path
from utils import NPMClient
from datetime import datetime, timezone
from utils import synchronized_print
import re
from models import SourceType
from models.composed_metrics.aggregate_metrics.account import AccountVersion

class AccountAnalyzer:
    """Analyzes account compromise & release integrity anomalies"""
    '''
    _npm_cache: Dict[str, Dict] = {}
    UTC_MIN_DATETIME = datetime.min.replace(tzinfo=timezone.utc)

    def __init__(self, pkg_name: str = ""):
        self.package_name = pkg_name
        self.npm_client = NPMClient(pkg_name=pkg_name)   
    
    def _get_npm_data_cached(self) -> Optional[Dict]:
        """Fetch NPM data with caching"""
        # If it's already cached, it will return immediately.
        if self.package_name in AccountAnalyzer._npm_cache:
            #synchronized_print(f"Using cached NPM data for {self.package_name}")
            return AccountAnalyzer._npm_cache[self.package_name]
        
        # Otherwise, fetch from NPM
        #synchronized_print(f"Fetching NPM data for {self.package_name}")
        npm_data = self.npm_client.get_npm_package_data()
        
        AccountAnalyzer._npm_cache[self.package_name] = npm_data
        return npm_data
    '''
    def analyze(self, version: str, git_repo_path: Path, source: SourceType) -> AccountVersion:
        account = AccountVersion()
        return account  # Temporary return to skip analysis
    
        #if source in (SourceType.LOCAL, SourceType.DEOBFUSCATED):
        #    return account
        '''
        # Get GitHub metrics
        if git_repo_path and source == SourceType.GIT:
            repo = Repo(str(git_repo_path))
            
            # Take the cotributors from the git repository
            #contributors_names = set()
            #contributors_emails = set()            
            #for commit in repo.iter_commits():
            #    if commit.author:
            #        contributors_names.add(commit.author.name)
            #        contributors_emails.add(commit.author.email)
            #return len(contributors_names), list(contributors_names), list(contributors_emails)
            
            try:
                tag = repo.tags[version]
                #commit = tag.commit
                # test github_release_date, take the release time from GitHub repository  -  2021-11-04T17:48:07+07:00
                #release_time = self._parse_date(commit.committed_datetime.isoformat())
                metrics['github_hash_commit'] = tag.commit.hexsha
            except Exception as e:
                synchronized_print(f"    Error getting GitHub data for version {version}: {e}")
        '''
        # Get npm metrics
        npm_data = self._get_npm_data_cached()
        
        if npm_data and 'versions' in npm_data:
            version = self.normalize_version(version)
            if version not in npm_data['versions']:
                #synchronized_print(f"    NPM data for version {version} not found in package data")
                #synchronized_print(f"    Available versions: {list(npm_data['versions'].keys())}")
                version = self.extract_version(version)
                if version not in npm_data['versions']:
                    print(f"    NPM data for extracted version {version} still not found, skipping NPM metrics")
                    return account

            version_data = npm_data['versions'][version]
            # Get maintainers/owners
            maintainers = version_data.get('maintainers', [])
            account.npm_maintainers = len(maintainers)
            account.npm_hash_commit = version_data.get('gitHead', "")
            if 'time' in npm_data and version in npm_data['time']:
                account.npm_release_date = self._parse_date(npm_data['time'][version])
            #metrics['npm_maintainers_nicks'] = [maintainer.get('name', '') for maintainer in maintainers if maintainer.get('name')]
            #metrics['npm_maintainers_emails'] = [maintainer.get('email', '') for maintainer in maintainers if maintainer.get('email')] 
            # Get publisher info
            #npm_user = version_data.get('_npmUser', {})
            #metrics['npm_maintainer_published_release'] = npm_user.get('name', '') if npm_user else ''
        return account

    def _parse_date(self, date_str: str) -> datetime:
        if not date_str:
            return AccountAnalyzer.UTC_MIN_DATETIME
        try:
            # Handle 'Z' suffix for UTC
            if date_str.endswith("Z"):
                date_str = date_str[:-1] + "+00:00"

            # Parse the ISO format string
            dt = datetime.fromisoformat(date_str)
            
            # If it has no timezone, assume UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            # Convert to UTC timezone
            return dt.astimezone(timezone.utc)

        except Exception as e:
            print(f"Error parsing date {date_str}: {e}")
            return AccountAnalyzer.UTC_MIN_DATETIME
    
    def normalize_version(self, version: str) -> str:
        """Normalize version string"""
        version = version.strip('v')                        # Normalize version by removing leading 'v'
        version = version.replace(self.package_name, '')    # Remove package name if present
        version = version.strip('@')                        # Remove leading '@' if present
        '''
        if self.package_name in version:
            version = version.split(self.package_name)[-1]
        '''
        return version
    
    def extract_version(self, version: str) -> str:
        """Extract numeric version string"""
        #synchronized_print(f"    Trying to extract numeric version from {version}")
        match = re.search(r'\d+(\.\d+)*', version)
        if match:
            #synchronized_print(f"    Extracted version for NPM data: {match.group(0)}")
            return match.group(0)
        return version
