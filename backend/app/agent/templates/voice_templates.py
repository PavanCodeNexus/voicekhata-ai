from typing import Dict, Any, List

AI_DISCLOSURES = {
    "kn-IN": "Namaskara! Naanu nimma AI Voice Khata sahayaka. Neevu maathaadi hisab baredkolbahudu.",
    "hi-IN": "Namaste! Main aapka AI Voice Khata sahayak hoon. Aap bolkar hisab darj kar sakte hain.",
    "en-IN": "Hello! I am your AI Voice Khata assistant. You can speak to record credit and payments."
}

def get_ai_disclosure(lang: str = "kn-IN") -> str:
    return AI_DISCLOSURES.get(lang, AI_DISCLOSURES["kn-IN"])

def format_spoken_response(intent_result: Dict[str, Any], lang: str = "kn-IN") -> str:
    """
    Sub-2s response formatter for Timbre v3.0 TTS.
    """
    intent = intent_result.get("intent")
    
    # 1. Correction
    if intent == "CORRECTION":
        c_name = intent_result.get("customer_name", "Customer")
        amt = int(intent_result.get("new_amount_paise", 0) / 100)
        bal = int(intent_result.get("new_balance_rupees", 0))
        if "kn" in lang:
            return f"Thappu thiddalagidhe. {c_name} avrige {amt} rupaayi baredhidhene. Eega mottha baaki {bal} rupaayi."
        elif "hi" in lang:
            return f"Theek kar diya. {c_name} ka {amt} rupaye darj ho gaya. Kul baaki ab {bal} rupaye hai."
        else:
            return f"Corrected: {c_name}, {amt} rupees recorded. Total balance is now {bal} rupees."

    # 2. Ambiguity
    elif intent == "AMBIGUOUS":
        candidates = intent_result.get("candidates", [])
        names = [f"{c['name']} ({c.get('alias', '')})" for c in candidates]
        choices = " athava ".join(names) if "kn" in lang else " ya fir ".join(names)
        if "kn" in lang:
            return f"Eradu hesaru ide: {choices}. Yaarige baredkolli?"
        elif "hi" in lang:
            return f"Do log hain: {choices}. Kaunse wale ka hisab likhna hai?"
        else:
            return f"Multiple customers found: {choices}. Which one would you like to update?"

    # 3. Query: Today's Summary
    elif intent == "QUERY_TODAY_SUMMARY":
        credit = int(intent_result.get("today_credit_rupees", 0))
        payment = int(intent_result.get("today_payment_rupees", 0))
        cnt = intent_result.get("today_count", 0)
        if "kn" in lang:
            return f"Ivatthu {cnt} vyavaharadalli {credit} rupaayi saala aagidhe, matthu {payment} rupaayi jama aagidhe."
        elif "hi" in lang:
            return f"Aaj kul {cnt} transactions mein {credit} rupaye udhaar gaya hai, aur {payment} rupaye jama hue hain."
        else:
            return f"Today in {cnt} transactions, {credit} rupees credit given, and {payment} rupees collected."

    # 4. Query: Customer Balance
    elif intent == "QUERY_CUSTOMER_BALANCE":
        cust = intent_result.get("customer", {})
        c_name = cust.get("name", "Grahak")
        bal = int(cust.get("balance_rupees", 0))
        if "kn" in lang:
            return f"{c_name} avaru {bal} rupaayi kodbeku."
        elif "hi" in lang:
            return f"{c_name} ka kul baaki {bal} rupaye hai."
        else:
            return f"{c_name} owes {bal} rupees."

    # 5. Transactions
    elif intent in ["TRANSACTION", "COMPOUND_TRANSACTION"]:
        records = intent_result.get("records", [])
        if not records:
            return "Kshama maadi, hisab artha aaglilla." if "kn" in lang else "Hisab samajh nahi aaya."
            
        phrases = []
        for r in records:
            c_name = r.get("customer", {}).get("name", "Grahak")
            amt = int(r.get("amount_rupees", 0))
            bal = int(r.get("new_balance_rupees", 0))
            is_credit = r.get("kind") == "credit_sale"
            
            if "kn" in lang:
                k_word = "saala" if is_credit else "jama"
                phrases.append(f"{c_name} avrige {amt} rupaayi {k_word} baredhidhene. Baaki {bal} rupaayi.")
            elif "hi" in lang:
                k_word = "udhaar" if is_credit else "jama"
                phrases.append(f"{c_name} ke {amt} rupaye {k_word} darj hue. Kul baaki {bal} rupaye.")
            else:
                k_word = "credit" if is_credit else "payment"
                phrases.append(f"{c_name}, {amt} rupees {k_word} recorded. New balance {bal} rupees.")
        return " ".join(phrases)

    return "Hisab artha aaglilla, mathomme heli." if "kn" in lang else "Hisab samajh nahi aaya, kripya dobara bolein."
