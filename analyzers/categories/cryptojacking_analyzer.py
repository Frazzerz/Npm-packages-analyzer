import re
from typing import List, Pattern
from utils import UtilsForAnalyzer
from models.domains import CryptoMetrics
from utils import synchronized_print
class CryptojackingAnalyzer:
    """Analyze cryptojacking & wallet theft techniques"""

    CRYPTO_PATTERNS: List[Pattern] = [
        #'ethereum': re.compile(r'\b0x[a-fA-F0-9]{40}\b'),
        #'bitcoinLegacy': re.compile(r'\b1[a-km-zA-HJ-NP-Z1-9]{25,34}\b'),
        #'bitcoinSegwit': re.compile(r'\b(3[a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{11,71})\b'),
        ##'tron': re.compile(r'((?<!\w)[T][1-9A-HJ-NP-Za-km-z]{33})'),
        #'bch': re.compile(r'bitcoincash:[qp][a-zA-Z0-9]{41}'),
        ##'ltc': re.compile(r'(?<!\w)ltc1[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{11,71}\b'),
        ##'ltc2': re.compile(r'(?<!\w)[mlML][a-km-zA-HJ-NP-Z1-9]{25,34}')
        ##'solana': re.compile(r'((?<!\w)[4-9A-HJ-NP-Za-km-z][1-9A-HJ-NP-Za-km-z]{32,44})'),
        ##'solana2': re.compile(r'((?<!\w)[3][1-9A-HJ-NP-Za-km-z]{35,44})')
        ##'solana3': re.compile(r'((?<!\w)[1][1-9A-HJ-NP-Za-km-z]{35,44})')
        re.compile(
            r'(?<![\w\-/_])(?:'
            r'0x[a-fA-F0-9]{40}|'                               # Ethereum
            r'1[a-km-zA-HJ-NP-Z1-9]{25,34}|'                    # Bitcoin Legacy
            r'3[a-km-zA-HJ-NP-Z1-9]{25,34}|'                    # Bitcoin Segwit P2SH
            r'c1[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{11,71}|'     # Bitcoin Segwit Bech32
            r'bitcoincash:[qp][a-zA-Z0-9]{41}'                  # Bitcoin Cash
            r')(?![\w\-/_])'
        ),
        # \b \b word boundaries, find exact word
        # (?<![\w\-/_]) ensures the preceding character is not a word character and not - or / or _
        # (?![\w\-/_]) ensures the following character is not ...
        # [number] specific starting characters (number) for certain crypto addresses
    ]

    CRYPTOCURRENCY_NAMES: List[Pattern] = [
        # ethereum, eth, bitcoin, btc, bitcoinLegacy, bitcoinSegwit, bitcoin cash, bch
        re.compile(
            r'(?<![\w\-/_])(?:'
            r'ethereum|bitcoin|bitcoin[-\s]?cash|'
            r'bitcoinlegacy|bitcoinsegwit|'
            r'(?:eth|btc|bch)'
            r')(?![\w\-/_])',
            re.IGNORECASE
        )
    ]

    WALLET_DETECTION_PATTERNS: List[Pattern] = [
        re.compile(
            r'(?:'
            # typeof windows != 'undefined' or ethereum.isMetaMask 
            r'typeof\s+window\.ethereum\s*!==?\s*[\'"]undefined[\'"]|'
            r'ethereum\.isMetaMask|'
            # window.ethereum.request
            r'(?:window\.)?ethereum\.request'
            r')',
            re.IGNORECASE
        )
        # variable spaces: \s+ (at least one space), \s* (zero or more spaces)
        # ['"] can be either single or double quotes
        # !==? -> != and !==
        # ()? is optional group
    ]

    REPLACE_CRYPTO_ADDRESS_PATTERN: List[Pattern] = [
        # crypto_symbol: eth, ethereum, btc, bitcoin, bitcoinLegacy, bitcoinSegwit
        re.compile(
            # if ( <variable> == 'crypto_symbol' [any optional conditions] ) { [any code] .replace(
            r'if\s*\(\s*[^=]+==\s*[\'"](?:eth(?:ereum)?|btc|bitcoin(?:Legacy|Segwit)?)[\'"][^)]*\)\s*\{[^}]*?\.replace\s*\(',
            re.IGNORECASE
        )
    ]

    # eth_sendTransaction, solana_signTransaction, solana_signAndSendTransaction are functions used to send crypto to someone, sign operations on dApps and authorize smart contracts
    # an attacker can hook these functions to modify the destination address to his own address
    HOOK_PROVIDER_PATTERN: List[Pattern] = [
        re.compile(r'\b(eth_sendTransaction|solana_signTransaction|solana_signAndSendTransaction)\b', re.IGNORECASE),
    ]

    def analyze(self, content: str) -> CryptoMetrics:
        crypto = CryptoMetrics()

        crypto.crypto_addresses, crypto.list_crypto_addresses = UtilsForAnalyzer.detect_patterns(content, self.CRYPTO_PATTERNS)
        crypto.len_list_crypto_addresses_unique = len(set(crypto.list_crypto_addresses))
        crypto.cryptocurrency_name, crypto.list_cryptocurrency_names = UtilsForAnalyzer.detect_patterns(content, self.CRYPTOCURRENCY_NAMES)
        crypto.len_list_cryptocurrency_names_unique = len(set(crypto.list_cryptocurrency_names))
        crypto.wallet_detection, crypto.wallet_detection_list = UtilsForAnalyzer.detect_patterns(content, self.WALLET_DETECTION_PATTERNS)
        # Mechanism present in the malware considered :
        #   Intercepts all HTTP responses (fetch/XMLHttpRequest) and replaces the crypto addresses found in the content with those controlled by the attacker
        # Check presence of cryptocurrency name and .replace function could indicate address substitution
        crypto.replaced_crypto_addresses, crypto.replaced_crypto_addresses_list = UtilsForAnalyzer.detect_patterns(content, self.REPLACE_CRYPTO_ADDRESS_PATTERN)
        crypto.hook_provider = UtilsForAnalyzer.detect_count_patterns(content, self.HOOK_PROVIDER_PATTERN)
        return crypto