import requests, json, os
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

def get_free_specials():
    """Récupère les jeux Steam passés à 0€ via promo (prix original > 0)."""
    r = requests.get(
        "https://store.steampowered.com/search/results/",
        params={"maxprice": "free", "specials": "1", "json": "1", "count": "50", "cc": "fr"},
        headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "fr-FR,fr;q=0.9"},
        timeout=20
    )
    html = r.json().get('results_html', '')
    soup = BeautifulSoup(html, 'html.parser')

    games = []
    for item in soup.select('a[data-ds-appid]'):
        app_id = item.get('data-ds-appid')
        name_el = item.select_one('.title')
        strike_el = item.select_one('strike')  # prix original barré = était payant

        if not (app_id and name_el and strike_el):
            continue  # si pas de prix barré = jeu F2P de base, on skip

        games.append({
            'id': app_id,
            'name': name_el.text.strip(),
            'original_price': strike_el.text.strip(),
            'store_url': f"https://store.steampowered.com/app/{app_id}/",
            'steamdb_url': f"https://steamdb.info/app/{app_id}/",
            'image': f"https://cdn.akamai.steamstatic.com/steam/apps/{app_id}/header.jpg"
        })

    print(f"🔍 {len(games)} jeu(x) à 0€ trouvé(s)")
    return games

def send_notification(game):
    embed = {
        "title": f"🎮 {game['name']}",
        "description": (
            f"Prix habituel : ~~{game['original_price']}~~ → **Gratuit !**\n\n"
            f"🔎 Vérifie si c'est **Free to Keep** ou juste un weekend d'essai :\n"
            f"> [SteamDB]({game['steamdb_url']})  ·  [Page Steam]({game['store_url']})"
        ),
        "color": 0x00adee,
        "image": {"url": game['image']},
        "footer": {"text": "Vérifie 'Free to Keep' sur steamdb.info/upcoming/free/"},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    r = requests.post(WEBHOOK_URL, json={
        "username": "Steam Free Games",
        "content": "@everyone 🎮 Un jeu est passé gratuit sur Steam !",
        "embeds": [embed]
    }, timeout=10)
    print(f"{'✅' if r.status_code in (200, 204) else '❌'} {game['name']} ({r.status_code})")

def main():
    seen = load_seen()
    for game in get_free_specials():
        if game['id'] not in seen:
            send_notification(game)
            seen.add(game['id'])
    save_seen(seen)

if __name__ == '__main__':
    main()
