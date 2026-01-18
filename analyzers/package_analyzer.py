from pathlib import Path
from utils import NPMClient
from .version_analyzer import VersionAnalyzer
from utils import synchronized_print

class PackageAnalyzer:
    """Coordinator for analyzing Git and local versions of an npm package"""
    def __init__(self, workers: int = 1, package_name: str = "", output_dir: Path = Path(".")):
        self.pkg_name = package_name
        self.output_dir = output_dir
        self.npm_client = NPMClient(pkg_name=package_name)
        self.version_analyzer = VersionAnalyzer(
            max_processes=workers,
            package_name=package_name,
            output_dir=output_dir
        )
        
    def analyze_package(self) -> None:
        """Analyze all versions of a package"""
        entries = self.npm_client.download_package_versions_tarball()
        if not entries:
            synchronized_print(f"Unable to analyze {self.pkg_name} - No versions available or too few")
            return
        self.version_analyzer.entries = entries
        self.version_analyzer.analyze_versions()