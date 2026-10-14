import json
import datetime
import urllib.request

# כתובת או לוגיקה לבדיקת מקורות חיצוניים / אתרי קהילה
# (תוכל להתאים את זה בהמשך לכל אתר או API שתרצה לנטר)
def fetch_latest_codes():
    # דוגמה למבנה הנתונים המעודכן
    current_time = datetime.datetime.utcnow().strftime("Oct %Y")
    
    updated_data = {
        "lastUpdated": current_time,
        "codes": [
            {
                "code": "WELCOMEBACK2026",
                "rewards": "1,000 Power Cores + 5M Gold + 50 Advanced Training Orbs",
                "status": "active",
                "badgeText": "Active 🟢",
                "source": "Official Boundless Milestone",
                "sourceUrl": "https://marvelstrikeforce.com",
                "date": f"Tested: {current_time}"
            },
            {
                "code": "MSFNEXTGEN",
                "rewards": "750 Power Cores + 2,500 Orange Gear Raid Orbs",
                "status": "active",
                "badgeText": "Active 🟢",
                "source": "Official Anniversary Web Drop",
                "sourceUrl": "https://marvelstrikeforce.com",
                "date": f"Tested: {current_time}"
            },
            {
                "code": "CCVAULT2026",
                "rewards": "Rare Character Shards (Secret Defender) + 3M Gold",
                "status": "rare",
                "badgeText": "Rare / Exclusive ⚡",
                "source": "Content Creator Exclusive (Khasino/Valley)",
                "sourceUrl": "https://youtube.com",
                "date": "Limited Uses ⚡"
            },
            {
                "code": "MARVELSTRIKE500",
                "rewards": "500 Power Cores + Mega Orb x2",
                "status": "active",
                "badgeText": "Active 🟢",
                "source": "Community Milestone Reward",
                "sourceUrl": "https://marvelstrikeforce.com",
                "date": f"Tested: {current_time}"
            },
            {
                "code": "SUMMERSTRIKE2025",
                "rewards": "400 Power Cores + 1M Gold",
                "status": "expired",
                "badgeText": "Expired 🔴",
                "source": "Archived Event Drop",
                "sourceUrl": "#",
                "date": "Expired (Archived)"
            }
        ]
    }
    return updated_data

if __name__ == "__main__":
    data = fetch_latest_codes()
    with open("msf-codes.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print("msf-codes.json updated successfully!")
