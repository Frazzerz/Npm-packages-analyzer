from typing import List, Pattern, Tuple
from utils import synchronized_print, OutputTarget
import signal
class UtilsForAnalyzer:
    
    @staticmethod
    def detect_patterns_with_timeout(content: str, patterns: List[Pattern], timeout_seconds: int = 5) -> Tuple[int, List[str]]:
        """Detect patterns with timeout protection"""
        matches = []
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Regex timeout")
        
        for pattern in patterns:
            try:
                # Set timeout
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(timeout_seconds)
                
                for match in pattern.finditer(content):
                    matches.append(match.group(0))
                
                # Cancel timeout
                signal.alarm(0)
                
            except TimeoutError:
                signal.alarm(0)
                synchronized_print(f"    Regex timeout on pattern: {pattern.pattern[:50]}...", OutputTarget.FILE_ONLY)
                # Continue with other patterns
                
            except Exception as e:
                signal.alarm(0)
                synchronized_print(f"    Regex error: {e}", OutputTarget.FILE_ONLY)

        return len(matches), matches
    
    @staticmethod
    def detect_patterns(content: str, patterns: List[Pattern]) -> Tuple[int, List[str]]:
        return UtilsForAnalyzer.detect_patterns_with_timeout(content, patterns, timeout_seconds=5)
    
    '''
    @staticmethod
    def detect_patterns(content: str, patterns: List[Pattern]) -> Tuple[int, List[str]]:
        matches = []
        for pattern in patterns:
            for match in pattern.finditer(content):
                matches.append(match.group(0))
        return len(matches), matches
    '''

    @staticmethod
    def detect_count_patterns(content: str, patterns: List[Pattern]) -> int:
        return sum(1 for pattern in patterns for _ in pattern.finditer(content))

'''
Best practices for writing efficient regex patterns:
Limitare i quantificatori illimitati
 MALE: \w+ può matchare migliaia di caratteri
    r'(\w+)\.(exec)'
 
 BENE: Limita a 30 caratteri (nessun nome variabile è così lungo)
    r'\w{1,30}\.(exec)'

Evitare gruppi di cattura se non necessari
 MALE: Cattura inutile
    r'(\w+)\.(post|get)'

 BENE: Rimuovi gruppo se non usi il valore
    r'\w{1,30}\.(post|get)'

Limitare pattern "match anything"
 MALE: [^;]* può essere infinito
    r'\(([^;]*);'

 BENE: Limita a 200 caratteri
    r'\([^;]{0,200}'

Rimuovere spazi opzionali finali
 MALE: \s* alla fine può causare backtracking
    r'homedir\s*\(?\s*\)?\s*'

 BENE: Rimuovi se non serve
    r'homedir\s*\(?\s*\)?'
'''