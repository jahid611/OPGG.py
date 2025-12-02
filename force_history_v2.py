import json
import os
import time
import opgg.opgg
from opgg.opgg import OPGG
from opgg.params import Region

DB_FILE = "opgg_database.json"

def main():
    print("--- ☢️ MODE HACKER V2 : FORMAT DATE CORRIGÉ ☢️ ---")
    
    ORIGINAL_URL = opgg.opgg._GAMES_API_URL
    bot = OPGG()
    
    # --- CONFIG ---
    target_name = "Jaydmj23#JSYD"
    target_region = Region.EUW
    # --------------

    print(f"1. Recherche du joueur...")
    try:
        results = bot.search(target_name, target_region)
        if not results: return print("❌ Joueur introuvable.")
        player = results[0].summoner
        my_id = player.summoner_id
    except Exception as e: return print(f"❌ Erreur API: {e}")

    # Chargement base
    all_games = []
    seen_ids = set()
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding='utf-8') as f:
                data = json.load(f)
                all_games = data.get("history", [])
                seen_ids = {g["game_id"] for g in all_games}
                print(f"📂 {len(all_games)} parties en mémoire.")
        except: pass

    # BOUCLE DE RÉCUPÉRATION
    current_cursor = "" 
    
    for batch in range(1, 6): # 5 tours de 20 = 100 games
        print(f"\n📥 Téléchargement Paquet {batch}/5 (20 parties)...")
        
        if current_cursor:
            print(f"   ↳ Demande des parties AVANT le : {current_cursor}")
            # CORRECTION ICI : On injecte la date formatée proprement
            opgg.opgg._GAMES_API_URL = ORIGINAL_URL + f"&ended_at={current_cursor}"
        else:
            opgg.opgg._GAMES_API_URL = ORIGINAL_URL

        try:
            new_games = bot.get_recent_games(search_result=results[0], results=20)
            
            if not new_games:
                print("   ⚠️ Plus de parties disponibles.")
                break

            # On prend la dernière game pour définir le prochain curseur
            last_game = new_games[-1] if isinstance(new_games, list) else new_games
            if isinstance(last_game, list): last_game = last_game[-1]
            
            if hasattr(last_game, 'created_at'):
                # FORMAT ISO 8601 (YYYY-MM-DDTHH:MM:SS) C'est ça que l'API veut !
                current_cursor = last_game.created_at.strftime('%Y-%m-%dT%H:%M:%S')

            batch_added = 0
            for game in new_games:
                if isinstance(game, list): game = game[0]
                if game.id in seen_ids: continue

                # --- EXTRACTION EXPRESS (Même logique que d'habitude) ---
                total_kills_blue = sum(p.stats.kill for p in game.participants if p.team_key == "BLUE")
                total_kills_red = sum(p.stats.kill for p in game.participants if p.team_key == "RED")
                all_dmgs = [p.stats.total_damage_dealt_to_champions for p in game.participants]
                max_dmg = max(all_dmgs) if all_dmgs else 1
                
                match_data = {
                    "game_id": game.id,
                    "timestamp": game.created_at.timestamp() if hasattr(game, 'created_at') else 0,
                    "type": game.game_type,
                    "ago": "Ancien",
                    "duration": f"{game.game_length_second // 60}m {game.game_length_second % 60}s",
                    "result": "UNKNOWN",
                    "teams": {"BLUE": [], "RED": []},
                    "my_stats": {},
                    "total_kills_blue": total_kills_blue,
                    "total_kills_red": total_kills_red,
                    "max_damage": max_dmg
                }

                for p in game.participants:
                    stats = p.stats
                    tier_str = f"{p.tier_info.tier} {p.tier_info.division}" if (hasattr(p, 'tier_info') and p.tier_info and p.tier_info.tier) else "Unranked"
                    is_me = (p.summoner.summoner_id == my_id)
                    
                    p_data = {
                        "name": p.summoner.game_name,
                        "tag": p.summoner.tagline,
                        "champion_id": p.champion_id,
                        "team": p.team_key,
                        "role": p.position,
                        "spells": p.spells,
                        "items": p.items,
                        "runes": p.rune.primary_rune_id if p.rune else None,
                        "rune_style": p.rune.primary_page_id if p.rune else None,
                        "k": stats.kill, "d": stats.death, "a": stats.assist,
                        "kda_ratio": round((stats.kill + stats.assist) / max(1, stats.death), 2),
                        "damage": stats.total_damage_dealt_to_champions,
                        "wards_placed": stats.ward_place,
                        "wards_control": stats.vision_wards_bought_in_game,
                        "cs": stats.minion_kill + (stats.neutral_minion_kill or 0),
                        "op_score": stats.op_score,
                        "op_rank": stats.op_score_rank,
                        "p_kill": 0, # Simplifié pour ce script de force
                        "tier": tier_str,
                        "is_me": is_me
                    }
                    match_data["teams"][p.team_key].append(p_data)
                    if is_me:
                        match_data["result"] = stats.result
                        match_data["my_stats"] = p_data

                all_games.append(match_data)
                seen_ids.add(game.id)
                batch_added += 1
            
            print(f"   ✅ {batch_added} nouvelles parties récupérées.")
            
            # Pause de sécurité
            time.sleep(2)

        except Exception as e:
            print(f"⚠️ Erreur paquet : {e}")
            break

    # SAUVEGARDE FINALE
    opgg.opgg._GAMES_API_URL = ORIGINAL_URL # Reset
    all_games.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    
    print(f"\n🧮 SAUVEGARDE DE {len(all_games)} PARTIES...")
    
    # Recalcul rapide des stats globales pour le JSON
    global_stats = { "total_games": 0, "wins": 0, "losses": 0, "kills": 0, "deaths": 0, "assists": 0 }
    from collections import defaultdict
    champ_stats_map = defaultdict(lambda: {"games": 0, "wins": 0, "kills": 0, "deaths": 0, "assists": 0, "cs": 0})
    teammates_map = defaultdict(lambda: {"games": 0, "wins": 0})
    
    current_rank = {"tier": "Unranked", "lp": ""}

    for idx, game in enumerate(all_games):
        if not game.get("my_stats"): continue
        me = game["my_stats"]
        global_stats["total_games"] += 1
        if game["result"] == "WIN": global_stats["wins"] += 1
        else: global_stats["losses"] += 1
        global_stats["kills"] += me["k"]
        global_stats["deaths"] += me["d"]
        global_stats["assists"] += me["a"]
        
        c = champ_stats_map[me["champion_id"]]
        c["games"] += 1
        if game["result"] == "WIN": c["wins"] += 1
        c["kills"] += me["k"]; c["deaths"] += me["d"]; c["assists"] += me["a"]; c["cs"] += me["cs"]
        
        if idx==0 and me.get("tier") != "Unranked": current_rank = {"tier": me["tier"], "lp": ""}
        
        for p in game["teams"][me["team"]]:
            if not p["is_me"]:
                tm = teammates_map[p["name"]]
                tm["games"] += 1
                if game["result"] == "WIN": tm["wins"] += 1

    final_champs = []
    for cid, data in champ_stats_map.items():
        final_champs.append({"id": cid, "games": data["games"], "winrate": round((data["wins"]/data["games"])*100), "kda": f"{round((data['kills']+data['assists'])/max(1,data['deaths']),2)}:1", "cs": round(data["cs"]/data["games"],1)})
    final_champs.sort(key=lambda x: x["games"], reverse=True)

    final_mates = []
    for name, data in teammates_map.items():
        if data["games"] > 1: final_mates.append({"name": name, "games": data["games"], "winrate": round((data["wins"]/data["games"])*100), "wins": data["wins"], "losses": data["games"]-data["wins"]})
    final_mates.sort(key=lambda x: x["games"], reverse=True)

    site_data = {
        "profile": { "name": player.game_name, "tag": player.tagline, "level": player.level, "icon_url": str(player.profile_image_url), "ranks": [{"queue": "Ranked Solo", "tier": current_rank["tier"], "lp": ""}] },
        "stats_summary": global_stats, "champions_stats": final_champs, "recent_teammates": final_mates, "history": all_games 
    }

    with open(DB_FILE, "w", encoding='utf-8') as f: json.dump(site_data, f, indent=4, ensure_ascii=False)
    with open("opgg_clone_data.json", "w", encoding='utf-8') as f: json.dump(site_data, f, indent=4, ensure_ascii=False)

    print(f"✅ TERMINE ! Relancez votre site web.")

if __name__ == "__main__":
    main()