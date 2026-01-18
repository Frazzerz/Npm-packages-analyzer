import re
from typing import Dict, List, Pattern
from utils import UtilsForAnalyzer
from utils import synchronized_print
from models.domains import PayloadMetrics
class PayloadAnalyzer:
    """Analyze payload delivery and execution techniques"""
    
    TIMING_DELAYS_PATTERNS: List[Pattern] = [
        # await new Promise( (resolve) => { setTimeout( resolve, 1000); } );
        #re.compile(r'await\s+new\s+Promise\s*\(\s*(\w+)\s*=>\s*\{?\s*[\s\S]*?setTimeout\w*\s*\(\s*\1[\s\S]*?\}?\s*\)', re.IGNORECASE),
        re.compile(r'await\s+new\s+Promise\s*\(\s*(\w+)\s*=>\s*\{?\s*[\s\S]{0,500}?setTimeout\w*\s*\(\s*\1[\s\S]{0,100}?\}?\s*\)', re.IGNORECASE),
        # (\w+) capture the variable name (resolve)
        # \w* zero or more alphanumeric characters (or underscore)
        # [\s\S] any character (space or non-space). Used to match newlines as well
        # *? Non-greedy quantifier (takes the minimum necessary), stop as soon as you find setTimeout, do not take the following ones
        # \1 Backreference to the captured variable (resolve)
        # ?: Indicates a non-capturing group (returns the entire match, not just the group)
    ]
    
    EVAL_PATTERNS: List[Pattern] = [re.compile(r'eval\s*\([\s\S]*?\)')]
    
    SHELL_COMMANDS_PATTERNS: List[Pattern] = [
        # obj.exec(command, args)
        # Bun is a JavaScript runtime similar to Node.js, and it has a function to execute system commands
        # await Bun.$`command`
        # Not to be confused with RegExp.exec(), which is a method for searching for patterns in a string
        re.compile(
            r'(?:'
            r'(?:child_process|exec|spawn|shell)\.exec\s*\(\s*\w{1,50}\s*,\s*\w{1,50}\s*\)|'  # Limit \w+
            r'\w{0,50}\s*Bun\.\$\s*`[^`]{0,200}`'  # Limit backtick content
            r')',
            re.IGNORECASE
        )
    ]
    '''
        re.compile(
            r'(?:'
            #r'(\w+)?.?exec\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)|'                                     # Original
            #r'(?!(?:RegExp|re|regexp)\.exec\b)(\w+)?\.?exec\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)|'    # Explicit avoid matching RegExp.exec
            r'(?:child_process|exec|spawn|shell)\.exec\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)|'          # Whitelist
            r'(\w+)?\s*Bun\.\$\s*\`[\s\S]*?\`'
            r')',
            re.IGNORECASE
        )
    '''

    PREINSTALL_PATTERNS: List[Pattern] = [re.compile(r'"preinstall"\s*:\s*"[^"]*"\s*,?', re.IGNORECASE)]    # [^"]*  Any text between quotes
    
    def analyze(self, content: str, package_info: Dict) -> PayloadMetrics:
        payload = PayloadMetrics()
        
        payload.timing_delays_count, payload.list_timing_delays = UtilsForAnalyzer.detect_patterns(content, self.TIMING_DELAYS_PATTERNS)
        payload.eval_count, payload.list_eval = UtilsForAnalyzer.detect_patterns(content, self.EVAL_PATTERNS)
        payload.shell_commands_count, payload.list_shell_commands = UtilsForAnalyzer.detect_patterns(content, self.SHELL_COMMANDS_PATTERNS)

        if(package_info['file_name'] == 'package.json'):
            _, preinstall_scripts = UtilsForAnalyzer.detect_patterns(content, self.PREINSTALL_PATTERNS)
            #Take only the first occurrence, there should be only one preinstall script in package.json
            if preinstall_scripts:
                payload.preinstall_scripts = [preinstall_scripts[0]]
        
        return payload