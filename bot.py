import cloudscraper, requests, json, os, re
from bs4 import BeautifulSoup
from datetime import datetime, timezone

WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL')
SEEN_FILE = 'seen_games.json'

def load_seen():
    try:
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    except:
        return set()

def save_seen(seen):
    with open(SEEN_FILE, 'w') as f:
        json.dump(sorted(list(seen)), f)

def get_free_to_keep_games():
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows'}
    )
    try:
        r = scraper.get('https://steamdb.info/upcoming/free/', timeout=30)
        r.raise_for_status()
        print(f"✅ SteamDB OK (status {r.status_code})")
    except Exception as e:
        print(f"❌ SteamDB bloqué: {e}")
        return []

    soup = BeautifulSoup(r.text, 'html.parser')
    print(f"Page: {soup.title.text if soup.title else 'no title'}")

    games = []
    for el in soup.find_all(string=re.compile(r'free\s+to\s+keep', re.IGNORECASE)):
        parent = el.parent
        for _ in range(10):
            if parent is None:
                break
            app_id = parent.get('data-appid') or parent.get('data-ds-appid')
            if not app_id:
                link = parent.find('a', href=re.compile(r'/app/\d+'))
                if link:
                    m = re.search(r'/app/(\d+)', link['href'])
                    if m:
                        app_id = m.group(1)
            if app_id and not any(g['id'] == app_id for g in games):
                name_el = parent.find(['h2', 'h3', 'strong'])
                name = name_el.text.strip() if name_el else f"App {app_id}"
                games.append({
                    'id': app_id, 'name': name,
                    'store_url': f"https://store.steampowered.com/app/{app_id}/",
                    'steamdb_url': f"https://steamdb.info/app/{app_id}/",
                    'image': f"https://cdn.akamai.steamstatic.com/steam/apps/{app_id}/header.jpg"
                })
                break
            parent = parent.parent

    print(f"🔍 {len(games)} jeu(x) Free to Keep trouvé(s)")
    return games

def send_notification(game):
    if not WEBHOOK_URL:
        print("❌ DISCORD_WEBHOOK_URL non défini")
        return
    embed = {
        "title": f"🎮 Free to Keep : {game['name']}",
        "description": f"Gratuit à garder définitivement !\n\n[🛒 Steam]({game['store_url']}) · [📊 SteamDB]({game['steamdb_url']})",
        "color": 0x00adee,
        "image": {"url": game['image']},
        "footer": {"text": "steamdb.info/upcoming/free/"},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    r = requests.post(WEBHOOK_URL, json={
        "username": "Steam Free Games",
        "content": "@everyone 🎮 Jeu **Free to Keep** sur Steam !",
        "embeds": [embed]
    }, timeout=10)
    print(f"{'✅' if r.status_code in (200,204) else '❌'} {game['name']} ({r.status_code})")

def main():
    seen = load_seen()
    new_count = 0
    for game in get_free_to_keep_games():
        if game['id'] not in seen:
            send_notification(game)
            seen.add(game['id'])
            new_count += 1
    print(f"📊 Nouveaux : {new_count} | Total vu : {len(seen)}")
    save_seen(seen)

if __name__ == '__main__':
    main()
