import requests

# Ekhane apnar Riot Developer Portal theke pawa "Development API Key" ta boshan
API_KEY = "RGAPI-2456eb51-7456-497b-9d41-c31e41653136"

GAME_NAME = "1W Pandaaa"
TAG_LINE = "8787"

headers = {
    "X-Riot-Token": API_KEY
}

print(f"Testing Riot API for {GAME_NAME}#{TAG_LINE}...\n")

# Step 1: Riot ID theke PUUID ber kora (Account API - Asia cluster)
print("Fetching PUUID...")
account_url = f"https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{GAME_NAME}/{TAG_LINE}"
response = requests.get(account_url, headers=headers)

if response.status_code != 200:
    print(f"❌ Failed to get PUUID. Error: {response.status_code}")
    print(response.json())
    exit()

puuid = response.json().get("puuid")
print(f"✅ PUUID Found: {puuid[:15]}...\n")

# Step 2: PUUID diye Last Match ID ber kora (Valorant AP Region)
print("Fetching Last Match...")
matchlist_url = f"https://ap.api.riotgames.com/val/match/v1/matchlists/by-puuid/{puuid}"
response = requests.get(matchlist_url, headers=headers)

if response.status_code != 200:
    print(f"❌ Failed to get Matchlist. Error: {response.status_code}")
    exit()

history = response.json().get("history", [])
if not history:
    print("❌ No recent competitive matches found in the last few days.")
    exit()

latest_match_id = history[0]["matchId"]
print(f"✅ Latest Match ID Found: {latest_match_id}\n")

# Step 3: Match ID diye purangsho Match Details ber kora
print("Fetching Match Details...")
match_url = f"https://ap.api.riotgames.com/val/match/v1/matches/{latest_match_id}"
response = requests.get(match_url, headers=headers)

if response.status_code != 200:
    print(f"❌ Failed to get Match Details. Error: {response.status_code}")
    exit()

match_data = response.json()
print("✅ Match Data Downloaded Successfully!\n")

# Step 4: JSON theke apnar KDA extract kora
players = match_data.get("players", [])
for player in players:
    if player.get("puuid") == puuid:
        stats = player.get("stats", {})
        kills = stats.get("kills", 0)
        deaths = stats.get("deaths", 0)
        assists = stats.get("assists", 0)
        score = stats.get("score", 0)

        print("-" * 30)
        print(f"🎮 YOUR STATS IN LAST MATCH:")
        print("-" * 30)
        print(f"IGN: {player.get('gameName')}#{player.get('tagLine')}")
        print(f"Kills:   {kills}")
        print(f"Deaths:  {deaths}")
        print(f"Assists: {assists}")
        print(f"Combat Score: {score}")
        print("-" * 30)
        break

print("\n🚀 Test Complete! Backend Engine is alive.")