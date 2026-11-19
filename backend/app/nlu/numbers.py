import re
from typing import Optional

# Comprehensive Indic and English number word dictionaries
NUMBER_WORDS = {
    # English
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90, "hundred": 100, "thousand": 1000,
    
    # Hindi / Hinglish numerals
    "ek": 1, "do": 2, "teen": 3, "chaar": 4, "paanch": 5,
    "chhah": 6, "saat": 7, "aath": 8, "nau": 9, "das": 10,
    "gyaarah": 11, "baarah": 12, "terah": 13, "chaudah": 14, "pandrah": 15,
    "solah": 16, "satrah": 17, "athaarah": 18, "unnees": 19, "bees": 20,
    "tees": 30, "chaalis": 40, "chalis": 40, "pachaas": 50, "saath": 60, "sattar": 70,
    "assi": 80, "nabbe": 90, "sau": 100, "hazaar": 1000,
    
    # Kannada numerals
    "ondu": 1, "eradu": 2, "mooru": 3, "naalaku": 4, "aidu": 5,
    "aaru": 6, "eeLu": 7, "entu": 8, "ombhatthu": 9, "hatthu": 10,
    "ippatthu": 20, "moovatthu": 30, "nalavatthu": 40, "aivatthu": 50,
    "aravatthu": 60, "eppatthu": 70, "enbhatthu": 80, "thombhatthu": 90,
    "nooru": 100, "saavira": 1000,
    
    # Tamil numerals
    "ondru": 1, "onnu": 1, "irandu": 2, "rendu": 2, "moondru": 3, "moonu": 3,
    "naangu": 4, "naalu": 4, "aindhu": 5, "anju": 5, "aaru": 6, "ezhu": 7,
    "ettu": 8, "onbadhu": 9, "patthu": 10, "aimbadhu": 50, "aayiram": 1000,
    
    # Telugu numerals
    "okati": 1, "rendu": 2, "moodu": 3, "naalugu": 4, "aidu": 5,
    "aaru": 6, "yedu": 7, "enimidi": 8, "thommidi": 9, "padi": 10,
    "nalabhai": 40, "yaabhai": 50, "vandha": 100, "veyi": 1000
}

# Special Indian compound idioms mapped directly to rupees
SPECIAL_INDIAN_NUMERALS = {
    "teen sau chaalis": 340,
    "teen sau chalis": 340,
    "chaar sau tees": 430,
    "char sau tees": 430,
    "three forty": 340,
    "four thirty": 430,
    "dhaai sau": 250,
    "dhai sau": 250,
    "dedh sau": 150,
    "paune teen sau": 275,
    "sawa teen sau": 325,
    "munnooru nalavattu": 340,
    "munnooru nalavattu": 340,
    "eradu nooru": 200,
    "mooru nooru": 300,
    "erandu nooru": 200,
    "rendu nooru": 200,
    "moodu vandhalu": 300
}

def parse_spoken_number(text: str) -> Optional[int]:
    """
    Parses spoken number from Indic/English string and returns integer PAISE (1 rupee = 100 paise).
    e.g. '340' -> 34000 paise, 'dhaai sau' -> 25000 paise.
    """
    clean = text.lower().replace("-", " ").replace("₹", "").replace("rs.", "").replace("rs", "").strip()
    
    # 1. Match special colloquial idioms first
    for phrase, val in SPECIAL_INDIAN_NUMERALS.items():
        if phrase in clean:
            return int(val * 100)
            
    # 2. Match exact numeric digits: e.g. "340", "340.50"
    match = re.search(r'\b\d+(\.\d+)?\b', clean)
    if match:
        try:
            rupees = float(match.group(0))
            return int(round(rupees * 100))
        except ValueError:
            pass
            
    # 3. Multi-word compounding: e.g. "chaar sau tees"
    words = clean.split()
    total = 0.0
    current_multiplier = 0.0
    found_number = False

    for w in words:
        if w in ["sau", "hundred", "nooru", "vandha", "vandhalu"]:
            if current_multiplier == 0:
                total += 100
            else:
                total += current_multiplier * 100
                current_multiplier = 0
            found_number = True
        elif w in ["hazaar", "thousand", "saavira", "aayiram", "veyi"]:
            if current_multiplier == 0:
                total += 1000
            else:
                total += current_multiplier * 1000
                current_multiplier = 0
            found_number = True
        elif w in NUMBER_WORDS:
            val = NUMBER_WORDS[w]
            current_multiplier += val
            found_number = True

    total += current_multiplier
    if found_number and total > 0:
        return int(round(total * 100))
        
    return None
