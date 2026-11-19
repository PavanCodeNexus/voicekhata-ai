import datetime
import re
from typing import Tuple

RELATIVE_DATES = {
    # Yesterday (-1)
    "kal": -1, "ninne": -1, "netru": -1, "ninna": -1, "yesterday": -1,
    # Day before yesterday (-2)
    "parso": -2, "monne": -2, "mundha netru": -2, "monna": -2,
    # Today (0)
    "aaj": 0, "ivatthu": 0, "ivathu": 0, "innikki": 0, "iniku": 0, "eeroju": 0, "today": 0
}

def resolve_relative_date(clause: str) -> Tuple[str, int]:
    """
    Returns (ISO date string YYYY-MM-DD, offset_days).
    """
    clean = clause.lower()
    
    # Check if future tense: e.g. "kal dega" / "naale kodthini"
    is_future = bool(re.search(r'\b(dega|dunga|naale|kodthini|tharuvaan)\b', clean))
    
    for word, offset in RELATIVE_DATES.items():
        if re.search(rf'\b{word}\b', clean):
            # If "kal" is used with future verb, it means tomorrow (+1), not yesterday
            effective_offset = 1 if (word == "kal" and is_future) else offset
            target_date = (datetime.date.today() + datetime.timedelta(days=effective_offset)).isoformat()
            return (target_date, effective_offset)
            
    today_str = datetime.date.today().isoformat()
    return (today_str, 0)
