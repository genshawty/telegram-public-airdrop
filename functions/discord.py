import requests
token = "discord token"
guild_id = 959392470137982997 #cheeele
# guild_id = 1052208146443145226 # my testing

def search_discord_member(tg_name, logger, name, discr):
    logger.info(f"tg: {tg_name}, {name}#{discr} - started checking discord")
    headers = {
        "Authorization": f"Bot {token}"
    }
    url = f"https://discord.com/api/guilds/{guild_id}/members/search"
    params = {
        "query": name,
        "limit": 50
    }
    r = requests.get(url, headers=headers, params=params)
    data = r.json()
    
    if len(data) == 0:
        return False
    for user in data:
        if str(user["user"]["discriminator"]) == str(discr):
            logger.info(f"tg: {tg_name}, {name}#{discr} - discord is found")
            return True
    logger.info(f"tg: {tg_name}, {name}#{discr} - discord not found")
    return False