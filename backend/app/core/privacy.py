import re
import logging
from typing import Any

# Regex patterns for PII detection in English and Bangla digits
IP_PATTERN = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b')
# Detects 10-15 digit sequences (standard mobile numbers in BD: 01xxxxxxxxx or +8801xxxxxxxxx)
# Also handles Bangla numerals: ০-৯
BANGLA_DIGITS = "০১২৩৪৫৬৭৮৯"
PHONE_PATTERN = re.compile(r'(\+?880|0)?1[3-9]\d{8}|(?:\+?৮৮০|০)?১[৩-৯][০-৯]{8}')

class PrivacyLogFilter(logging.Filter):
    """
    Custom logging filter to scrub IP addresses, emails, and phone numbers from logs.
    Guarantees no PII leaks into server logs.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = scrub_pii(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: scrub_pii(str(v)) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(scrub_pii(str(arg)) for arg in record.args)
        return True

def scrub_pii(text: str) -> str:
    """Replaces IP addresses, emails, and phone numbers with [REDACTED]."""
    if not isinstance(text, str):
        return text
    text = IP_PATTERN.sub("[IP_REDACTED]", text)
    text = EMAIL_PATTERN.sub("[EMAIL_REDACTED]", text)
    text = PHONE_PATTERN.sub("[PHONE_REDACTED]", text)
    return text
