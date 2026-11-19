import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.nlu.numbers import parse_spoken_number
from app.nlu.direction import detect_transaction_direction
from app.nlu.dates import resolve_relative_date
from app.db.session import get_db, setup_database
from app.agent.graph import process_utterance

def test_numeral_parsing():
    print("Testing Numeral Engine...")
    assert parse_spoken_number("teen sau chaalis") == 34000
    assert parse_spoken_number("three forty") == 34000
    assert parse_spoken_number("340") == 34000
    assert parse_spoken_number("dhaai sau") == 25000
    assert parse_spoken_number("munnooru nalavattu") == 34000
    assert parse_spoken_number("eradu nooru") == 20000
    print("  ✓ All numeral tests passed!")

def test_direction_guard():
    print("Testing Direction Guard...")
    # Hindi ne/ko rule
    kind1, _ = detect_transaction_direction("Ramesh ne 200 diya")
    assert kind1 == "payment_received"
    kind2, _ = detect_transaction_direction("Ramesh ko 200 diya")
    assert kind2 == "credit_sale"
    # Kannada kottidru/ge rule
    kind3, _ = detect_transaction_direction("Ramesh 200 kottidru")
    assert kind3 == "payment_received"
    kind4, _ = detect_transaction_direction("Ramesh ge 200 baredko")
    assert kind4 == "credit_sale"
    print("  ✓ All direction guard tests passed!")

def test_relative_dates():
    print("Testing Relative Dates...")
    _, off1 = resolve_relative_date("kal 200 diya tha")
    assert off1 == -1
    _, off2 = resolve_relative_date("parso 300 udhaar")
    assert off2 == -2
    _, off3 = resolve_relative_date("aaj subah 500")
    assert off3 == 0
    print("  ✓ All relative date tests passed!")

def test_end_to_end_voice_graph():
    print("Testing End-to-End Voice Graph...")
    setup_database()
    with get_db() as conn:
        # 1. Kannada entry
        res1 = process_utterance("Anand saala mooru nooru baredko", "kn-IN", conn)
        print("  1. Kannada Response:", res1["spoken_reply"])
        assert res1["status"] == "SUCCESS"
        
        # 2. Hindi Ambiguity test (Ramesh Sharma vs Ramesh Verma)
        res2 = process_utterance("Ramesh ka 340 udhaar", "hi-IN", conn)
        print("  2. Ambiguity Response:", res2["spoken_reply"])
        assert res2["intent"] == "AMBIGUOUS"
        
        # 3. Resolve Ambiguity
        res3 = process_utterance("Sharma ji", "hi-IN", conn)
        print("  3. Ambiguity Resolved Response:", res3["spoken_reply"])
        assert res3["status"] == "SUCCESS"
        
        # 4. Mid-sentence correction ("nahi, 430 likhna")
        res4 = process_utterance("nahi, 430 likhna", "hi-IN", conn)
        print("  4. Correction Response:", res4["spoken_reply"])
        assert res4["intent"] == "CORRECTION"
        assert res4["result"]["new_amount_paise"] == 43000
        
        # 5. Spoken Query for Today
        res5 = process_utterance("aaj kitna udhaar gaya?", "hi-IN", conn)
        print("  5. Today Query Response:", res5["spoken_reply"])
        assert res5["intent"] == "QUERY_TODAY_SUMMARY"
        
    print("  ✓ All End-to-End Voice Graph tests passed successfully!")

if __name__ == "__main__":
    test_numeral_parsing()
    test_direction_guard()
    test_relative_dates()
    test_end_to_end_voice_graph()
    print("\n🎉 ALL UNIT & INTEGRATION TESTS PASSED 100%!")
