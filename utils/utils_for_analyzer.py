from typing import List, Pattern, Tuple
from utils import synchronized_print, OutputTarget
import signal
from tree_sitter import Language, Parser
import tree_sitter_typescript as tstypescript

class UtilsForAnalyzer:
    JS_LANGUAGE = Language(tstypescript.language_typescript())
    
    @staticmethod
    def remove_comments(content: str, file_path_name: str) -> Tuple[str, int]:
        """Strips comments from JS/TS code while keeping the original layout intact.
        Special handling is included to preserve Triple Slash Directives in .d.ts files."""
        if not content:
            return "", 0

        parser = Parser(UtilsForAnalyzer.JS_LANGUAGE)
        content_bytes = content.encode("utf8")
        
        try:
            tree = parser.parse(content_bytes)
        except Exception:
            return content, 0
        
        comment_ranges = []
        cursor = tree.walk()
        reached_root = False
        is_index_d_ts = file_path_name.lower() == "index.d.ts"

        # Walk the AST iteratively to avoid stack overflow on massive files
        while not reached_root:
            if "comment" in cursor.node.type:
                start_b = cursor.node.start_byte
                end_b = cursor.node.end_byte
                
                # In index.d.ts files, we must ignore '///' directives as they are functional
                is_triple_slash = False
                if is_index_d_ts and content_bytes[start_b:start_b+3] == b"///":
                    is_triple_slash = True
                
                if not is_triple_slash:
                    comment_ranges.append((start_b, end_b))
            
            # Depth-first search traversal logic
            if cursor.goto_first_child():
                continue
            if cursor.goto_next_sibling():
                continue
            
            retracing = True
            while retracing:
                if not cursor.goto_parent():
                    reached_root = True
                    retracing = False
                if cursor.goto_next_sibling():
                    retracing = False

        if not comment_ranges:
            return content, 0

        # Use bytearray for efficient in-place deletions
        new_content_bytes = bytearray(content_bytes)
        
        # Process ranges in reverse to keep byte offsets valid after each deletion
        for start, end in reversed(comment_ranges):
            # Check if the comment is on its own line to prevent leaving blank lines
            has_newline_after = (end < len(new_content_bytes) and new_content_bytes[end:end+1] == b'\n')
            
            # Look backwards to see if there's only whitespace before the comment on the same line
            prefix_idx = start - 1
            only_whitespace_before = True
            while prefix_idx >= 0 and new_content_bytes[prefix_idx:prefix_idx+1] != b'\n':
                if new_content_bytes[prefix_idx:prefix_idx+1] not in [b' ', b'\t', b'\r']:
                    only_whitespace_before = False
                    break
                prefix_idx -= 1

            if only_whitespace_before and has_newline_after:
                # Full-line comment: remove the indentation and the trailing newline too
                actual_start = prefix_idx + 1 if prefix_idx >= 0 else 0
                del new_content_bytes[actual_start : end + 1]
            else:
                # Inline comment: just remove the comment text, leave the surrounding code
                del new_content_bytes[start:end]
        
        return new_content_bytes.decode("utf8"), len(comment_ranges)

     
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