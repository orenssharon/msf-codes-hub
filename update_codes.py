import json
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# הגדרת רשימת המקורות לשריפה
SOURCES = [
    {"name": "Dexerto", "url": "https://www.dexerto.com/gaming/marvel-strike-force-codes-1678852/"},
    {"name": "Pocket Tactics", "url": "https://www.pockettactics.com/marvel-strike-force/codes"},
]

# מילות מערכת ומילים נפוצות באנגלית שחובה לחסום
IGNORE_TOKENS = {
    "DOCTYPE", "HTML", "HEAD", "BODY", "ACTIVITIES", "CAMPAIGNS", 
    "MARVEL", "STRIKE", "FORCE", "GAMES", "UPDATE", "NEWS", "GUIDE", 
    "FREE", "REWARDS", "CORES", "ORBS", "SHARDS", "COMMUNITY"
}

# רשימת מילים נפוצות שאתרים משתמשים בהן ולא קשורים לקודים
ENGLISH_WORDS_BLOCKLIST = {
    "ROBLOX", "DISCORD", "PLAYERS", "CHECK", "COMMUNITY", "SHARE", "FIRST", 
    "SELECT", "TERMS", "USEFUL", "ABILITIES", "OBJECTIVES", "POCKET", "SEARCHING", 
    "PCGAMES", "WHILE", "BEFORE", "VENOM", "TUTORIAL", "PROBABLY", "BUILD", 
    "SCOPELY", "DEPENDING", "ENEMIES", "MAYCREDITS", "WEBSASSEMBLE", "GAMERANT", 
    "OFFICIAL", "MEDIA", "PROMOTIONS", "RELEASES", "PHONES", "MISTAKE", "OUTFIT", 
    "THERE", "FIXED", "TEAMS", "UNIVERSE", "BELOW", "STRANGE", "DOESN", "TIKTOK", 
    "AWESOME", "STEPPING", "PLAYERS", "SPIDER", "PLENTY", "EVENTS", "APPEARING", 
    "FRAGMENTS", "CAPTAIN", "WALKS", "SOMETIMES", "ENTER", "GREAT", "SPELLING", 
    "TRACK", "POWER", "UPCOMING", "CORRECTLY", "UPDATED", "POINT", "UNLOCK", 
    "INSTAGRAM", "TABLES", "ACTIVE", "ENJOYS", "ACROSS", "JUNETEENTH", "INCLUDE", 
    "ROSTER", "DIRECTLY", "BLUESKY", "RETURNING", "POSSIBLE", "PASTING", "MODULES", 
    "MILLION", "FAILING", "MODES", "CHALLENGES", "PREVENT", "ANGEL", "EASIEST", 
    "NIGHT", "JOURNALISTIC", "AMAZING", "SMALL", "TAKING", "EVERYTHING", "ABOUT", 
    "GERALT", "GAMING", "ENTERED", "SPECIAL", "INCLUDING", "GOODIES", "COMBINATIONS", 
    "RAIDS", "WEBPLAYABLE", "TIMES", "EXPIRED", "INBOX", "THANKS", "START", "AMERICA", 
    "WARNING", "REDEEM", "NOVEMBER", "CONTENT", "REMOVE", "ORCHIS", "THROUGH", 
    "BASED", "DIFFERENT", "ASSEMBLE", "FINDING", "CAREERS", "VILLAINS", "COMPLETE", 
    "SKYRIM", "FACEBOOK", "DEPUTY", "OTHER", "RECEIVE", "CREDITS", "DOCTOR", 
    "ANNOUNCEMENTS", "ABOVE", "LOVER", "WARGAMER", "LAUNCH", "EDITOR", "ALREADY", 
    "SWITCH", "CHATTING", "FEATURES", "INVITATION", "CHANCE", "EXTRA", "DAILY", 
    "WITHOUT", "THINK", "RESOURCES", "PLAYTIME", "DREAM", "AUDACITY", "WHERE", 
    "HUNDREDS", "MATERIALS", "BATTLE", "COPYING", "UPGRADE", "TESTING", "MAILBOX", 
    "PLAYING", "PARTICULARLY", "WORDS", "THUNDER", "CHECKING", "NETWORK", "PROGRESS", 
    "LATEST", "REGULARLY", "BOOKMARK", "TACTICS", "CHARACTERS", "WRITER", "HEROES", 
    "APPEAR", "POCKET", "LOOKING", "STEPS", "BOOSTS", "NINTENDO", "DURING", "ONEPLUS", 
    "INCREASINGLY", "CELEBRATIONS", "DIFFICULT", "SHARES", "SOCIAL", "THINGS", 
    "JOINED", "CODES", "STAFF", "CELEBRATE", "COLLECT", "EXPIRE", "YOUTUBE", 
    "DISCUSS", "GIFTING", "SCHEDULE", "GIVEAWAYS", "POWERED", "WORKING", "REDEEMING", 
    "SETTINGS", "SERVER", "HAVEN", "BORING", "KAYLEIGH", "FOLLOW", "MILESTONES", 
    "RIVIA", "POPPY", "WELCOME", "JOINING", "GAMBIT", "USUALLY", "LOADOUT", "WORTH", 
    "BUFFS", "GIVES"
}

# מילות מפתח לזיהוי קודי יוצרים או פרסים נדירים
CC_KEYWORDS = {"CC", "CHAMP", "ENVOY", "CREATOR", "EXCLUSIVE"}

def clean_and_validate_code(token):
    """בדיקה האם הטוקן עומד בתנאי הסף לקוד תקין ואמיתי"""
    token = token.upper().strip()
    
    # סינון לפי אורך (קודי MSF בדרך כלל בין 4 ל-25 תווים)
    if not (4 <= len(token) <= 25):
        return None
        
    # חסימת מילים מהרשימות השחורות
    if token in IGNORE_TOKENS or token in ENGLISH_WORDS_BLOCKLIST:
        return None
        
    # מניעת מחרוזות שהן מספרים נקיים בלבד
    if token.isdigit():
        return None
        
    # --- תנאי ברזל חדש: קוד אמיתי חייב להכיל לפחות ספרה אחת או להיות קוד מוכר עם תבנית מיוחדת ---
    # זה מונע ממילים רגילות באנגלית (כמו PLAYERS, ROBLOX) לעבור את המסנן
    has_digit = any(char.isdigit() for char in token)
    is_known_format = any(cc in token for cc in CC_KEYWORDS) or token.startswith("3E") or token.startswith("MSF")
    
    if not (has_digit or is_known_format):
        return None
        
    return token

def scrape_source(source_info):
    """שאיבת קודים ממקור בודד"""
    found_codes = set()
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(source_info["url"], headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for element in soup.find_all(['p', 'li', 'td', 'code', 'strong', 'span']):
                text = element.get_text()
                matches = re.findall(r'\b[A-Z0-9]{5,20}\b', text.upper())
                for match in matches:
                    valid_code = clean_and_validate_code(match)
                    if valid_code:
                        found_codes.add(valid_code)
        print(f"[{source_info['name']}] Found {len(found_codes)} clean codes.")
    except Exception as e:
        print(f"Error scraping {source_info['name']}: {e}")
    
    return found_codes

def main():
    print("Starting MSF Clean Aggregator v8.1...")
    
    code_consensus = {}
    
    for source in SOURCES:
        codes = scrape_source(source)
        for code in codes:
            if code not in code_consensus:
                code_consensus[code] = {"sources": set(), "is_cc": False}
            code_consensus[code]["sources"].add(source["name"])
            
            if any(keyword in code for keyword in CC_KEYWORDS):
                code_consensus[code]["is_cc"] = True

    processed_codes = []
    
    for code, data in code_consensus.items():
        source_count = len(data["sources"])
        is_cc = data["is_cc"]
        
        score = 50 + (source_count * 25)
        if is_cc:
            score += 50
            
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
            "score": score
        })

    # מיון לפי ציון
    processed_codes.sort(key=lambda x: x["score"], reverse=True)

    output_data = {
        "last_updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total_active": len([c for c in processed_codes if c["badge"] == "active"]),
        "total_rare": len([c for c in processed_codes if c["badge"] == "rare"]),
        "codes": processed_codes
    }

    filename = "msf-codes.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully saved {len(processed_codes)} clean codes to {filename}.")

if __name__ == "__main__":
    main()
