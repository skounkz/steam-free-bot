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
    headers = {'User-Agent': 'SteamFreeBot/1.0 Discord notification bot'}
    try:
        r = requests.get(
            'https://www.reddit.com/r/FreeGamesOnSteam/new.json?limit=25',
            headers=headers, timeout=15
        )
        r.raise_for_status()
        posts = r.json()['data']['children']
    except Exception as e:
        print(f"❌ Erreur Reddit: {e}")
        return []

    games = []
    for post in posts:
        d = post['data']
        title = d.get('title', '')
        if 'free to keep' not in title.lower():
            continue  # ignore les weekends d'essai

        post_id = d.get('id', '')
        url = d.get('url', '')
        reddit_url = f"https://reddit.com{d.get('permalink', '')}"
        game_name = re.sub(r'\[.*?\]|\(.*?\)', '', title).strip(' -–')
        match = re.search(r'store\.steampowered\.com/app/(\d+)', url)
        app_id = match.group(1) if match else None

        games.append({
            'id': post_id,
            'name': game_name or title,
            'store_url': url if app_id else None,
            'steamdb_url': f"https://steamdb.info/app/{app_id}/" if app_id else "https://steamdb.info/upcoming/free/",
            'image': f"https://cdn.akamai.steamstatic.com/steam/apps/{app_id}/header.jpg" if app_id else None,
            'reddit_url': reddit_url
        })

    print(f"🔍 {len(games)} jeu(x) Free to Keep trouvé(s)")
    return games

def send_notification(game):
    if not WEBHOOK_URL:
        print("❌ DISCORD_WEBHOOK_URL non défini")
        return

    links = []
    if game.get('store_url'):
        links.append(f"[🛒 Page Steam]({game['store_url']})")
    links.append(f"[📊 SteamDB]({game['steamdb_url']})")
    links.append(f"[💬 Reddit]({game['reddit_url']})")

    embed = {
        "title": f"🎮 Free to Keep : {game['name']}",
        "description": "Gratuit à garder définitivement !\n\n" + " · ".join(links),
        "color": 0x00adee,
        "footer": {"text": "Source: r/FreeGamesOnSteam"},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    if game.get('image'):
        embed["image"] = {"url": game['image']}

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
