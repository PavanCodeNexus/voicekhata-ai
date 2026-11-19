import re
from typing import Tuple

CREDIT_WORDS = [
    # Hindi
    "udhaar", "udhar", "baaki", "khata", "likh lo", "likhna", "likh", "daal do", "baad me",
    # Kannada
    "saala", "udri", "baredko", "kodbeku", "haaku", "haakko",
    # Tamil
    "kadan", "ezhudhiko", "tharanum", "pottuko",
    # Telugu
    "appu", "raayi", "ivvali", "veeyi",
    # English
    "credit", "borrow", "on account", "tab", "owes"
]

PAYMENT_WORDS = [
    # Hindi
    "jama", "diya", "de diya", "chukta", "chuka", "wapas", "lotaya", "gpay", "phonepe", "paytm",
    # Kannada
    "kottidhaane", "kotta", "kottidru", "theerisidha", "jama maadidha",
    # Tamil
    "kuduthaachu", "kuduthan", "theethutaanga", "kuduthutu",
    # Telugu
    "ichadu", "kattadu", "chellinchadu", "jama chesadu",
    # English
    "paid", "cleared", "settled", "received", "deposit", "payment"
]

CASH_SALE_WORDS = ["nagad", "cash", "rokkha", "cash sale"]
EXPENSE_WORDS = ["kharcha", "expense", "chai", "shop expense"]

def detect_transaction_direction(clause: str) -> Tuple[str, float]:
    """
    Returns (kind, confidence)
    Kinds: 'credit_sale', 'payment_received', 'cash_sale', 'expense'
    """
    clean = clause.lower()

    # Cash sale and expense checks
    if any(re.search(rf'\b{w}\b', clean) for w in EXPENSE_WORDS):
        return ("expense", 0.95)
    if any(re.search(rf'\b{w}\b', clean) for w in CASH_SALE_WORDS) and not any(w in clean for w in CREDIT_WORDS):
        return ("cash_sale", 0.95)

    # Direction Guard: Hindi grammatical markers:
    # "Ramesh ne 200 diye" -> he paid (payment_received)
    if re.search(r'\bne\b.*\b(diye|diya|chukaye)\b', clean):
        return ("payment_received", 0.98)
    # "Ramesh ko 200 diye" -> store gave him credit (credit_sale)
    if re.search(r'\bko\b.*\b(diye|diya)\b', clean):
        return ("credit_sale", 0.95)

    # Kannada grammatical markers:
    # "Ramesh 200 kottidru" -> he paid (payment_received)
    if re.search(r'\b(kottidru|kottidhaane|kotta)\b', clean):
        return ("payment_received", 0.98)
    # "Ramesh ge 200 kotte" -> credit_sale
    if re.search(r'\bge\b.*\b(kotte|baredko)\b', clean):
        return ("credit_sale", 0.95)

    # Generic keyword match
    is_payment = any(re.search(rf'\b{w}\b', clean) for w in PAYMENT_WORDS)
    is_credit = any(re.search(rf'\b{w}\b', clean) for w in CREDIT_WORDS)

    if is_payment and not is_credit:
        return ("payment_received", 0.95)
    if is_credit and not is_payment:
        return ("credit_sale", 0.95)

    # If both appear: e.g. "udhaar jama kiya" or order matters
    if is_payment:
        return ("payment_received", 0.85)
    if is_credit:
        return ("credit_sale", 0.90)

    # Default in Kirana context is credit_sale with lower confidence
    return ("credit_sale", 0.70)
