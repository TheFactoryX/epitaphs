#!/usr/bin/env python3
"""
Gravedigger #0 - The Cemetery
Writing epitaphs for dead repositories
"""

import os
import json
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
import requests

# Cemetery credentials
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")
CLAUDE_BASE_URL = "https://open.bigmodel.cn/api/anthropic"
GITHUB_API = "https://api.github.com"

# The poet
POET_MODEL = "claude-4-5-sonnet-20250929"
POET_NAME = "Claude Sonnet"

# Death threshold: years of silence
YEARS_OF_SILENCE = 2


def find_the_dead() -> tuple[list, str]:
    """Search for repositories that have passed away."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    # Calculate the death date threshold
    death_date = (datetime.now() - timedelta(days=YEARS_OF_SILENCE * 365)).strftime("%Y-%m-%d")

    # Search strategies for finding the departed
    strategies = [
        # The Forgotten: once popular, now abandoned
        {
            "q": f"stars:100..5000 pushed:<{death_date}",
            "sort": "stars",
            "name": "forgotten"
        },
        # The Archived: officially declared dead
        {
            "q": f"archived:true stars:>50",
            "sort": "stars",
            "name": "archived"
        },
        # The Silent: no activity, moderate stars
        {
            "q": f"stars:50..500 pushed:<{death_date}",
            "sort": "updated",
            "name": "silent"
        },
    ]

    strategy = random.choice(strategies)
    print(f"🔍 Search strategy: {strategy['name']}")

    params = {
        "q": strategy["q"],
        "sort": strategy["sort"],
        "order": "desc",
        "per_page": 50
    }

    try:
        response = requests.get(
            f"{GITHUB_API}/search/repositories",
            headers=headers,
            params=params,
            timeout=30
        )
        response.raise_for_status()
        items = response.json().get("items", [])
        return [parse_deceased(item) for item in items], strategy["name"]
    except Exception as e:
        print(f"⚠️  Search failed: {e}")
        return [], "failed"


def parse_deceased(item: dict) -> dict:
    """Extract information about the deceased."""
    return {
        "full_name": item["full_name"],
        "url": item["html_url"],
        "description": item.get("description", "No description"),
        "stars": item["stargazers_count"],
        "language": item.get("language", "Unknown"),
        "created_at": item["created_at"],
        "pushed_at": item["pushed_at"],
        "archived": item.get("archived", False),
        "owner": item["owner"]["login"],
        "topics": item.get("topics", [])
    }


def get_buried_repos() -> set:
    """Get list of already buried repositories."""
    graveyard = Path("graveyard")
    buried = set()

    if not graveyard.exists():
        return buried

    for burial_file in graveyard.glob(".burial_*"):
        try:
            with open(burial_file, 'r') as f:
                data = json.load(f)
                buried.add(data.get("deceased", {}).get("full_name", ""))
        except Exception:
            continue

    return buried


def select_deceased() -> tuple[dict, str]:
    """Select a repository for burial."""
    buried = get_buried_repos()
    print(f"🪦 Already buried: {len(buried)} repos")

    deceased_list, strategy = find_the_dead()

    if not deceased_list:
        raise RuntimeError("No deceased repositories found")

    # Filter out already buried
    available = [d for d in deceased_list if d["full_name"] not in buried]

    if not available:
        print("⚠️  All found repos already buried, allowing re-burial")
        available = deceased_list

    random.shuffle(available)
    return random.choice(available), strategy


def compose_epitaph(deceased: dict) -> str:
    """Have the poet compose an epitaph."""

    # Calculate how long it's been dead
    pushed_at = datetime.strptime(deceased["pushed_at"][:10], "%Y-%m-%d")
    created_at = datetime.strptime(deceased["created_at"][:10], "%Y-%m-%d")
    death_age = (datetime.now() - pushed_at).days
    life_span = (pushed_at - created_at).days

    prompt = f"""Write a poetic epitaph for a dead GitHub repository.

The Deceased:
- Name: {deceased['full_name']}
- Description: {deceased['description']}
- Language: {deceased['language']}
- Stars: {deceased['stars']}
- Born: {deceased['created_at'][:10]}
- Last breath: {deceased['pushed_at'][:10]}
- Silent for: {death_age} days
- Lived for: {life_span} days
- Archived: {deceased['archived']}
- Topics: {', '.join(deceased['topics']) if deceased['topics'] else 'none'}

Write a short, poetic epitaph (4-8 lines) for this repository.
The tone should be melancholic but beautiful.
Reference specific details about the project.
End with "Rest in /dev/null" or similar programmer humor.

Output ONLY the epitaph text, nothing else."""

    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
    }

    payload = {
        "model": POET_MODEL,
        "max_tokens": 1024,
        "system": "You are a poet who writes epitaphs for dead code repositories. Your style is melancholic, beautiful, and occasionally darkly humorous. You honor the memory of abandoned projects.",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
    }

    print("✍️  Poet is writing", end="", flush=True)

    response = requests.post(
        f"{CLAUDE_BASE_URL}/v1/messages",
        headers=headers,
        json=payload,
        timeout=120
    )
    response.raise_for_status()

    result = response.json()
    print(" done")

    # Extract text from Claude response
    content = result.get("content", [])
    if content and len(content) > 0:
        return content[0].get("text", "").strip()

    return ""


def get_next_tombstone_number() -> int:
    """Count tombstones in graveyard."""
    graveyard = Path("graveyard")
    if not graveyard.exists():
        return 0

    tombstones = list(graveyard.glob("tombstone_*.md"))
    return len(tombstones)


def carve_tombstone(deceased: dict, epitaph: str, poet_name: str, tombstone_number: int) -> Path:
    """Create the tombstone file."""
    graveyard = Path("graveyard")
    graveyard.mkdir(exist_ok=True)

    # Calculate dates
    created = deceased["created_at"][:10]
    last_push = deceased["pushed_at"][:10]

    tombstone_content = f"""# 🪦 {deceased['full_name']}

```
┌─────────────────────────────────────┐
│                                     │
│         {deceased['full_name'][:30]:<30} │
│                                     │
│         {created} — {last_push}      │
│                                     │
│         ⭐ {deceased['stars']} stars              │
│         📝 {deceased['language'] or 'Unknown':<20} │
│                                     │
└─────────────────────────────────────┘
```

## Epitaph

{epitaph}

---

**Description:** {deceased['description']}

**Topics:** {', '.join(deceased['topics']) if deceased['topics'] else 'None'}

**Archived:** {'Yes' if deceased['archived'] else 'No'}

**Repository:** [{deceased['full_name']}]({deceased['url']})

---

*Epitaph composed by {poet_name}*

*Tombstone #{tombstone_number} in the graveyard*

*May your code live on in forks.*
"""

    filename = f"tombstone_{tombstone_number:04d}.md"
    filepath = graveyard / filename

    with open(filepath, 'w') as f:
        f.write(tombstone_content)

    return filepath


def record_burial(deceased: dict, epitaph: str, poet_name: str, tombstone_number: int, strategy: str):
    """Record burial metadata."""
    graveyard = Path("graveyard")

    burial_data = {
        "tombstone_number": tombstone_number,
        "buried_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "deceased": deceased,
        "epitaph": epitaph,
        "poet": {"name": poet_name, "model": POET_MODEL},
        "strategy": strategy
    }

    burial_file = graveyard / f".burial_{tombstone_number:04d}"
    with open(burial_file, 'w') as f:
        json.dump(burial_data, f, indent=2)


def log_funeral(tombstone_number: int, deceased: dict, tombstone_path: str):
    """Update the cemetery registry."""
    readme_file = Path("README.md")

    try:
        if readme_file.exists():
            with open(readme_file, 'r') as f:
                content = f.read()
        else:
            print("⚠️  Registry not found")
            return

        born = deceased["created_at"][:10]
        died = deceased["pushed_at"][:10]
        repo_link = f"[{deceased['full_name']}]({deceased['url']})"
        entry = f"| {tombstone_number} | {repo_link} | {born} | {died} | ⭐{deceased['stars']} | [{tombstone_path}]({tombstone_path}) |"

        # Find the table header line and insert after it
        lines = content.split('\n')
        new_lines = []
        inserted = False

        for i, line in enumerate(lines):
            new_lines.append(line)
            # Insert after the table separator line (|---|---|...)
            if not inserted and line.startswith('|---'):
                # Check if previous line is the Cemetery Registry header
                if i > 0 and 'Deceased' in lines[i-1]:
                    new_lines.append(entry)
                    inserted = True

        if inserted:
            content = '\n'.join(new_lines)
            with open(readme_file, 'w') as f:
                f.write(content)
            print("📝 Funeral logged")
        else:
            print("⚠️  Could not find registry table")

    except Exception as e:
        print(f"⚠️  Failed to log funeral: {e}")


def conduct_funeral():
    """Conduct a funeral for a dead repository."""
    print("🪦 Gravedigger #0 reporting for duty...")

    tombstone_number = get_next_tombstone_number()
    print(f"⚰️  Tombstone #{tombstone_number}")

    # Find the deceased
    deceased, strategy = select_deceased()
    print(f"💀 Found: {deceased['full_name']}")
    print(f"📅 Last seen: {deceased['pushed_at'][:10]}")

    # Compose epitaph
    print(f"✍️  Poet: {POET_NAME}")
    epitaph = compose_epitaph(deceased)
    print(f"📜 Epitaph composed")

    # Carve tombstone
    tombstone_path = carve_tombstone(deceased, epitaph, POET_NAME, tombstone_number)
    print(f"🪦 Tombstone carved: {tombstone_path}")

    # Record burial
    record_burial(deceased, epitaph, POET_NAME, tombstone_number, strategy)

    # Log funeral
    log_funeral(tombstone_number, deceased, f"graveyard/tombstone_{tombstone_number:04d}.md")

    return tombstone_path


if __name__ == "__main__":
    if not CLAUDE_API_KEY:
        print("❌ Error: Cemetery credentials not found")
        print("   Set CLAUDE_API_KEY environment variable")
        exit(1)

    if not GITHUB_TOKEN:
        print("⚠️  Warning: GITHUB_TOKEN not set (rate limits apply)")

    # Retry strategy
    MAX_ATTEMPTS = 3
    success = False

    for attempt in range(MAX_ATTEMPTS):
        try:
            conduct_funeral()
            print("🕯️  Rest in peace...")
            success = True
            break
        except KeyboardInterrupt:
            print("\n⏹️  Funeral interrupted")
            exit(0)
        except Exception as e:
            if attempt < MAX_ATTEMPTS - 1:
                wait_time = (attempt + 1) * 3
                print(f"\n⚠️  Attempt {attempt + 1}/{MAX_ATTEMPTS} failed: {e}")
                print(f"🔄 Trying again in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"\n❌ Funeral failed: {e}")
                import traceback
                traceback.print_exc()
                exit(1)
