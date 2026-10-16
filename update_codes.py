#!/usr/bin/env python3
"""MSF Code Collector v7.2

Collects strict Marvel Strike Force redemption-code candidates from public
third-party pages, filtering out ordinary English words and numeric IDs.
Standard-library only; no pip installation required.
"""

import copy
import datetime as dt
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
from html.parser import HTMLParser

FILENAME = "msf-codes.json"
TIMEOUT_SECONDS = 20

SOURCES = [
    {
        "name": "Dexerto",
        "url": "https://www.dexerto.com/codes/marvel-strike-force-codes-3297218/",
    },
    {
        "name": "Pocket Tactics",
        "url": "https://www.pockettactics.com/marvel-strike-force/codes",
    },
]

# MSF codes typically mix letters and numbers, or follow specific formats.
TOKEN_RE = re.compile(r"(?<![A-Z0-9])[A-Z0-9]{6,14}(?![A-Z0-9])", re.I)
SPACE_RE = re.compile(r"\s+")

# Expanded ignore list to block common article words, HTML tags, and metadata
IGNORE_TOKENS = {
    "DOCTYPE", "HTML", "HTTPS", "HTTP", "JSON", "MARVEL", "STRIKE",
    "FORCE", "DISCORD", "PYTHON", "WINDOWS", "EXPIRED", "ACTIVE",
    "MOBILE", "ANDROID", "APPLE", "GOOGLE", "YOUTUBE", "SHARDS",
    "CORES", "POCKET", "TACTICS", "DEXERTO", "ARTICLE", "CONTENT",
    "REWARDS", "REDEEM", "REDEMPTION", "WORKING", "LATEST", "UPDATED",
    "FOLLOW", "SUBMIT", "BUTTON", "SERVER", "SOURCE", "STATUS",
    "UNKNOWN", "VERIFY", "VERIFIED", "SCOPELY", "SCOP​​ELY", "CHARACTERS",
    "PLAYER", "PLAYERS", "ACCOUNT", "GAMING", "WEBSITE", "OFFICIAL",
    "COMMUNITY", "REWARD", "CODES", "CODE", "GIFT", "CLAIM", "LOGIN",
    "REGISTER", "DOWNLOAD", "SUPPORT", "PRIVACY", "TERMS", "COOKIE",
    "COOKIES", "NEWSLETTER", "FACEBOOK", "TWITTER", "INSTAGRAM", "REDDIT",
    "ACTIVITIES", "CAMPAIGNS", "ANNOUNCEMENTS", "APPEARING", "AVAILABLE",
    "BOOKMARKED", "CELEBRATIONS", "CHALLENGES", "CHARACTER", "COLLECTOR",
    "COMBINATIONS", "CORRECTLY", "DEPENDING", "DIFFERENT", "DIFFICULT",
    "DIMENSION", "ELSEWHERE", "ENCOUNTER", "EVERYTHING", "FRAGMENTS",
    "IMMORTALITY", "INCLUDING", "INCREASINGLY", "INVESTMENT", "MATERIALS",
    "MILESTONES", "OBJECTIVES", "OCCASIONS", "PARTICULARLY", "PARTLETON",
    "PREFERRED", "PREPARING", "PROGRESSION", "PROMOTIONAL", "PROMOTIONS",
    "REDEEMING", "REGULARLY", "RESOURCES", "RETURNING", "SOMETIMES",
    "STRONGEST", "SURVIVING", "UNLOCKING", "WEBPLAYABLE", "WEBSASSEMBLE",
    "WELCOME",
}

CONTEXT_RE = re.compile(
    r"\b(code|codes|redeem|redemption|gift code|promo code|promotional code|"
    r"enter the code|use the code|claim the code|working codes|expired codes|"
    r"active codes|code list|code:|codes:)\b",
    re.I,
)

BLOCK_PHRASES = (
    "access denied",
    "verify you are human",
    "unusual traffic",
    "request blocked",
    "complete the captcha",
    "enable javascript and cookies to continue",
)

IGNORED_TAGS = {
    "script", "style", "noscript", "svg", "iframe", "nav", "header",
    "footer", "aside", "form", "button", "select", "option",
}


def now_utc():
    return dt.datetime.now(dt.timezone.utc)


def utc_iso():
    return now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_date():
    return now_utc().strftime("%b %d, %Y")


class VisibleTextParser(HTMLParser):
    ARTICLE_CLASSES = {"entry-content", "article-content", "article__content", "post-content"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.all_text = []
        self.article_text = []
        self.stack = []
        self.blocked_depth = 0
        self.article_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs = dict(attrs)
        classes = set((attrs.get("class") or "").lower().split())
        itemprop = (attrs.get("itemprop") or "").lower()
        hidden = "hidden" in attrs or attrs.get("aria-hidden", "").lower() == "true"
        style = (attrs.get("style") or "").replace(" ", "").lower()
        hidden = hidden or "display:none" in style or "visibility:hidden" in style
        blocked = tag in IGNORED_TAGS or hidden
        article = (
            tag in {"article", "main"}
            or itemprop == "articlebody"
            or bool(classes & self.ARTICLE_CLASSES)
        )
        void_tags = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
        if tag not in void_tags:
            self.stack.append((tag, blocked, article))
            if blocked:
                self.blocked_depth += 1
            if article:
                self.article_depth += 1

    def handle_endtag(self, tag):
        tag = tag.lower()
        index = next((i for i in range(len(self.stack) - 1, -1, -1) if self.stack[i][0] == tag), None)
        if index is None:
            return
        removed = self.stack[index:]
        del self.stack[index:]
        for _, blocked, article in reversed(removed):
            if blocked:
                self.blocked_depth = max(0, self.blocked_depth - 1)
            if article:
                self.article_depth = max(0, self.article_depth - 1)

    def handle_data(self, data):
        if self.blocked_depth:
            return
        value = SPACE_RE.sub(" ", data).strip()
        if not value:
            return
        self.all_text.append(value)
        if self.article_depth:
            self.article_text.append(value)

    def get_text(self):
        article = SPACE_RE.sub(" ", " ".join(self.article_text)).strip()
        full = SPACE_RE.sub(" ", " ".join(self.all_text)).strip()
        return article if len(article) >= 400 else full


def extract_visible_text(html):
    parser = VisibleTextParser()
    parser.feed(html)
    parser.close()
    return parser.get_text()


def load_existing_vault(filename=FILENAME):
    if not os.path.exists(filename):
        return {}
    try:
        with open(filename, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Existing vault cannot be read safely ({exc}); original file preserved."
        ) from exc

    if not isinstance(data, dict) or not isinstance(data.get("codes"), list):
        raise RuntimeError("Existing vault must be a JSON object containing a 'codes' array.")

    vault = {}
    for item in data["codes"]:
        if not isinstance(item, dict):
            continue
        code = item.get("code")
        if not isinstance(code, str) or not code.strip():
            continue
        normalized = code.strip().upper()
        record = copy.deepcopy(item)
        record["code"] = normalized
        vault[normalized] = record
    return vault


def fetch_source(source):
    request = urllib.request.Request(
        source["url"],
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            status = getattr(response, "status", 200)
            raw = response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ValueError(f"HTTP request failed: {exc}") from exc

    if not 200 <= status < 300:
        raise ValueError(f"Unexpected HTTP status: {status}")

    html = raw.decode("utf-8", errors="replace")
    if len(html) < 2500:
        raise ValueError("Response is unexpectedly short")

    text = extract_visible_text(html)
    low = text.lower()
    if len(text) < 350:
        raise ValueError("Visible page content is too short")
    if any(phrase in low for phrase in BLOCK_PHRASES):
        raise ValueError("Page appears to be a block/CAPTCHA page")
    if "marvel strike force" not in low and "marvelstrikeforce" not in low:
        raise ValueError("Expected Marvel Strike Force article text not found")
    return text


def is_valid_code_candidate(code):
    """Strict validation to block pure numbers, pure common words, and plain text."""
    if code in IGNORE_TOKENS:
        return False
    
    # Block purely numeric strings (MSF codes are alphanumeric or specific strings)
    if code.isdigit():
        return False

    # Block purely alphabetic strings unless they are very specific/short (most English words are alphabetic)
    if code.isalpha() and len(code) < 12:
        return False

    return True


def extract_candidates(text):
    candidates = {}
    for match in TOKEN_RE.finditer(text):
        code = match.group(0).upper()
        
        if not is_valid_code_candidate(code):
            continue

        start = max(0, match.start() - 220)
        end = min(len(text), match.end() + 220)
        context = SPACE_RE.sub(" ", text[start:end]).strip()
        if not CONTEXT_RE.search(context):
            continue

        candidates.setdefault(code, context[:320])
    return candidates


def update_source_history(record, source, seen_at, seen_date):
    source_list = record.get("sources")
    if not isinstance(source_list, list):
        source_list = []
        record["sources"] = source_list

    source_record = next(
        (item for item in source_list if isinstance(item, dict) and item.get("name") == source["name"]),
        None,
    )
    if source_record is None:
        source_list.append({
            "name": source["name"], "url": source["url"],
            "firstSeen": seen_date, "firstSeenAt": seen_at,
            "lastSeen": seen_date, "lastSeenAt": seen_at,
        })
    else:
        source_record["url"] = source["url"]
        source_record.setdefault("firstSeen", seen_date)
        source_record.setdefault("firstSeenAt", seen_at)
        source_record["lastSeen"] = seen_date
        source_record["lastSeenAt"] = seen_at


def merge_candidate(vault, code, evidence, source, seen_at, seen_date):
    is_new = code not in vault
    if is_new:
        vault[code] = {
            "code": code,
            "rewards": "Discovered via public guide — check in-game rewards",
            "status": "active",
            "source": source["name"],
            "sourceUrl": source["url"],
            "date": seen_date,
            "firstSeen": seen_date,
            "firstSeenAt": seen_at,
            "lastSeen": seen_date,
            "lastSeenAt": seen_at,
            "evidence": evidence,
            "verificationMethod": "source_discovery",
            "sources": [],
        }

    record = vault[code]
    record.setdefault("firstSeen", seen_date)
    record.setdefault("firstSeenAt", seen_at)
    record["lastSeen"] = seen_date
    record["lastSeenAt"] = seen_at
    record["evidence"] = evidence
    update_source_history(record, source, seen_at, seen_date)
    return is_new


def atomic_write_json(filename, data):
    directory = os.path.dirname(os.path.abspath(filename))
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=directory,
            prefix=os.path.basename(filename) + ".", suffix=".tmp", delete=False,
        ) as handle:
            temp_path = handle.name
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        with open(temp_path, "r", encoding="utf-8") as handle:
            checked = json.load(handle)
        if not isinstance(checked, dict) or not isinstance(checked.get("codes"), list):
            raise ValueError("Generated JSON failed structural validation")
        os.replace(temp_path, filename)
        temp_path = None
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def scrape_and_classify_codes(filename=FILENAME):
    # Start fresh or load existing valid ones, but clear out pure numeric/word debris
    vault = load_existing_vault(filename)
    
    # Clean out legacy junk tokens from existing vault automatically
    cleaned_vault = {}
    for code, rec in vault.items():
        if is_valid_code_candidate(code):
            cleaned_vault[code] = rec
    vault = cleaned_vault

    successful_sources = []
    failed_sources = []
    new_codes = 0

    for source in SOURCES:
        try:
            text = fetch_source(source)
            candidates = extract_candidates(text)
            if not candidates:
                raise ValueError("No contextual code candidates found")

            seen_at = utc_iso()
            seen_date = utc_date()
            successful_sources.append(source["name"])
            source_new = 0
            for code, evidence in candidates.items():
                if merge_candidate(vault, code, evidence, source, seen_at, seen_date):
                    new_codes += 1
                    source_new += 1
            print(f"OK: {source['name']}: {len(candidates)} candidates; {source_new} new.")
        except Exception as exc:
            failed_sources.append(source["name"])
            print(f"WARNING: {source['name']} skipped: {exc}")

    if not successful_sources:
        print("CRITICAL: No source yielded usable candidates. Existing vault was not changed.")
        return None

    return {
        "lastUpdated": now_utc().strftime("%b %d, %Y - %H:%M UTC"),
        "lastUpdatedAt": utc_iso(),
        "collectionStatus": "partial" if failed_sources else "success",
        "successfulSources": successful_sources,
        "failedSources": failed_sources,
        "candidateCount": len(vault),
        "codes": sorted(vault.values(), key=lambda item: item.get("code", "")),
    }


def main():
    try:
        updated = scrape_and_classify_codes()
        if updated is None:
            return 1
        atomic_write_json(FILENAME, updated)
        print(f"SUCCESS: Vault safely updated. Total valid codes: {len(updated['codes'])}")
        return 0
    except Exception as exc:
        print(f"CRITICAL: Update aborted: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
