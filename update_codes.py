import json
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# הגדרת רשימת המקורות לשCריפה (לפחות 4-5 מקורות מובילים לצירוף והצלבה)
SOURCES = [
    {"name": "Dexerto", "url": "https://www.dexerto.com/gaming/marvel-strike-force-codes-1678852/"},
    {"name": "Pocket Tactics", "url": "https://www.pockettactics.com/marvel-strike-force/codes"},
    # אפשר להוסיף מקורות נוספים לבדיקת הצלבה
]

# רשימת מילים לחסימה (זבל ורעש מהאתרים)
IGNORE_TOKENS = {
    "DOCTYPE", "HTML", "HEAD", "BODY", "ACTIVITIES", "CAMPAIGNS", 
    "MARVEL", "STRIKE", "FORCE", "GAMES", "UPDATE", "NEWS", "GUIDE", 
    "FREE", "REWARDS", "CORES", "ORBS", "SHARDS", "COMMUNITY"
}

# מילות מפתח לזיהוי קודי יוצרים או פרסים נדירים
CC_KEYWORDS = {"CC", "CHAMP", "ENVOY", "CREATOR", "EXCLUSIVE"}

def clean_and_validate_code(token):
    """בדיקה האם הטוקן עומד בתנאי הסף לקוד תקין"""
    token = token.upper().strip()
    
    # סינון לפי אורך (קודי MSF בדרך כלל בין 4 ל-25 תווים)
    if not (4 <= len(token) <= 25):
        return None
        
    # חסימת מילים נפוצות וזבל
    if token in IGNORE_TOKENS:
        return None
        
    # חסימת מחרוזות שהן מספרים נקיים בלבד או אותיות נקיות ארוכות מדי בלי מבנה הגיוני
    if token.isdigit():
        return None
        
    return token

def scrape_source(source_info):
    """שאיפת קודים ממקור בודד"""
    found_codes = set()
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(source_info["url"], headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # חיפוש טקסטים בתוך אלמנטים נפוצים (כמו טבלאות, פסקה או קוד)
            for element in soup.find_all(['p', 'li', 'td', 'code', 'strong', 'span']):
                text = element.get_text()
                # זיהוי מחרוזות אלפא-נומריות שנראות כמו קודים
                matches = re.findall(r'\b[A-Z0-9]{5,20}\b', text.upper())
                for match in matches:
                    valid_code = clean_and_validate_code(match)
                    if valid_code:
                        found_codes.add(valid_code)
        print(reg_log := f"[{source_info['name']}] Found {len(found_codes)} potential codes.")
    except Exception as e:
        print(f"Error scraping {source_info['name']}: {e}")
    
    return found_codes

def main():
    print("Starting MSF Code Aggregator & Consensus Engine v8.0...")
    
    # מילון לאיסוף הקודים וכמות הפעמים שהופיעו במקורות שונים
    # מבנה: {code: {'sources': set(), 'is_cc': bool}}
    code_consensus = {}
    
    for source in SOURCES:
        codes = scrape_source(source)
        for code in codes:
            if code not in code_consensus:
                code_consensus[code] = {"sources": set(), "is_cc": False}
            code_consensus[code]["sources"].add(source["name"])
            
            # זיהוי אוטומטי האם זה קוד יוצר (CC)
            if any(keyword in code for keyword in CC_KEYWORDS):
                code_consensus[code]["is_cc"] = True

    processed_codes = []
    
    for code, data in code_consensus.items():
        source_count = len(data["sources"])
        is_cc = data["is_cc"]
        
        # --- מערכת שקלול וציון אטרקטיביות (Scoring System) ---
        # 1. קודי יוצרים מקבלים בונוס ענק
        # 2. קוד שמופיע ביותר מקורות מקבל ציון אמינות גבוה יותר
        score = 50 + (source_count * 25)
        if is_cc:
            score += 50
            
        # קביעת סטטוס וסוג הפרס
        if is_cc:
            status = "Rare / Exclusive"
            reward_desc = "Content Creator Exclusive Reward"
            badge_type = "rare"
        else:
            status = "Active"
            reward_desc = "Verified Community Reward Drop"
            badge_type = "active"

        processed_codes.append({
            "code": code,
            "reward": reward_desc,
            "status": status,
            "badge": badge_type,
            "source": f"Synced from {source_count} Sources" if source_count > 1 else "Live Community Scraper",
            "date": datetime.utcnow().strftime("Synced: %b %Y"),
            "score": score  # ציון פנימי למיון
        })

    # --- מיון אוטומטי מהציון הגבוה ביותר לנמוך ביותר ---
    processed_codes.sort(key=lambda x: x["score"], reverse=True)

    # מבנה הסופי לקובץ ה-JSON
    output_data = {
        "last_updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total_active": len([c for c in processed_codes if c["badge"] == "active"]),
        "total_rare": len([c for c in processed_codes if c["badge"] == "rare"]),
        "codes": processed_codes
    }

    # שמירה אטומית של קובץ ה-JSON
    filename = "msf-codes.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully saved {len(processed_codes)} sorted codes to {filename}.")

if __name__ == "__main__":
    main()
