import requests, json, os, re
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
    try:
        r = requests.get(
            'https://www.gamerpower.com/api/giveaways',
            params={'platform': 'steam', 'type': 'game'},
            headers={'User-Agent': 'SteamFreeBot/1.0'},
            timeout=15
        )
        r.raise_for_status()
        giveaways = r.json()
        print(f"✅ GamerPower OK: {len(giveaways)} jeu(x) trouvé(s)")
    except Exception as e:
        print(f"❌ Erreur GamerPower: {e}")
        return []

    games = []
    for g in giveaways:
        if g.get('status', '').lower() != 'active':
            continue
        url = g.get('open_giveaway', '') or g.get('open_giveaway_url', '')
        match = re.search(r'store\.steampowered\.com/app/(\d+)', url)
        app_id = match.group(1) if match else None
        games.append({
            'id': str(g['id']),
            'name': g.get('title', 'Unknown'),
            'worth': g.get('worth', '?'),
            'end_date': g.get('end_date', 'N/A'),
            'store_url': url if app_id else None,
            'steamdb_url': f"https://steamdb.info/app/{app_id}/" if app_id else "https://steamdb.info/upcoming/free/",
            'image': g.get('thumbnail', '')
        })

    print(f"🔍 {len(games)} jeu(x) gratuits à garder sur Steam")
    return games

def send_notification(game):
    if not WEBHOOK_URL:
        print("❌ DISCORD_WEBHOOK_URL non défini")
        return
    links = []
    if game.get('store_url'):
        links.append(f"[🛒 Steam]({game['store_url']})")
    links.append(f"[📊 SteamDB]({game['steamdb_url']})")
    embed = {
        "title": f"🎮 Free to Keep : {game['name']}",
        "description": (
            f"Prix habituel : ~~{game['worth']}~~ → **Gratuit !**\n"
            f"Expire : {game['end_date']}\n\n" + " · ".join(links)
        ),
        "color": 0x00adee,
        "thumbnail": {"url": game['image']},
        "footer": {"text": "Source: GamerPower"},
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
