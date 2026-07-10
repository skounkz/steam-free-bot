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
    PLATFORMS = ['steam', 'epic-games-store', 'gog', 'itch.io']
    all_games = []

    for platform in PLATFORMS:
        try:
            r = requests.get(
                'https://www.gamerpower.com/api/giveaways',
                params={'platform': platform, 'type': 'game'},
                headers={'User-Agent': 'SteamFreeBot/1.0'},
                timeout=15
            )
            r.raise_for_status()
            giveaways = r.json()
            if not isinstance(giveaways, list):
                continue
            print(f"✅ {platform}: {len(giveaways)} jeu(x)")
            for g in giveaways:
                if not isinstance(g, dict):
                    continue
                if g.get('status', '').lower() != 'active':
                    continue
                url = g.get('open_giveaway', '') or g.get('open_giveaway_url', '')
                all_games.append({
                    'id': str(g['id']),
                    'name': g.get('title', 'Unknown'),
                    'worth': g.get('worth', '?'),
                    'end_date': g.get('end_date', 'N/A'),
                    'platform': platform,
                    'store_url': url,
                    'image': g.get('thumbnail', '')
                })
        except Exception as e:
            print(f"❌ Erreur {platform}: {e}")

    print(f"🔍 {len(all_games)} jeu(x) gratuits au total")
    return all_games
    
def send_notification(game):
    if not WEBHOOK_URL:
        print("❌ DISCORD_WEBHOOK_URL non défini")
        return
    links = []
    if game.get('store_url'):
        links.append(f"[🛒 Steam]({game['store_url']})")
    links.append(f"[📊 SteamDB]({game['steamdb_url']})")
    embed = {
       "title": f"🎮 Free to Keep : {game['name']} ({game['platform']})",
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
