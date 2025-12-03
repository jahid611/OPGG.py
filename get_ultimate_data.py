import json
import os
import time
from collections import defaultdict
from opgg.opgg import OPGG
from opgg.params import Region

DB_FILE = "opgg_database.json"

def main():
    print("--- 🚀 Démarrage Backend OP.GG Clone ---")
    opgg = OPGG()
    
    # --- CONFIGURATION UTILISATEUR ---
    target_name = "Jaydmj23#JSYD"
    target_region = Region.EUW
    # ---------------------------------

    # 1. Charger la mémoire existante
    existing_data = {"history": []}
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding='utf-8') as f:
                existing_data = json.load(f)
            print(f"📂 Mémoire chargée : {len(existing_data.get('history', []))} parties en mémoire.")
        except:
            print("⚠️ Base de données corrompue, on repart avec un historique vide.")
            
    # 2. Récupération Profil Complet (Rank, LP, etc.)
    print(f"📡 Récupération du profil complet de {target_name}...")
    try:
        search_results = opgg.search(target_name, target_region)
        if not search_results: return print("❌ Joueur introuvable.")
        
        # Utilisation de get_summoner pour le profil complet (avec LP, Winrate, Past Seasons)
        summoner_full = opgg.get_summoner(search_results[0])
        my_id = summoner_full.summoner_id
        
        # Extraction du Rang Actuel (Solo Duo)
        solo_rank = {"tier": "Unranked", "lp": "0 LP", "winrate": "", "w": 0, "l": 0}
        
        try:
            if hasattr(summoner_full, 'league_stats') and summoner_full.league_stats:
                for league in summoner_full.league_stats:
                    q_type = getattr(league.queue_info, 'game_type', '') if hasattr(league, 'queue_info') else getattr(league, 'game_type', '')
                    if q_type == "SOLORANKED":
                        t = league.tier_info
                        w, l = league.win or 0, league.lose or 0
                        total = w + l
                        wr = int((w / total) * 100) if total > 0 else 0
                        solo_rank = {"tier": f"{t.tier} {t.division}", "lp": f"{t.lp} LP", "winrate": f"{w}W {l}L ({wr}%)", "w": w, "l": l}
                        break
        except Exception:
             # Si l'extraction de la ligue échoue, on continue avec Unranked
             pass 

        # Extraction des Saisons Passées
        past_ranks = []
        if hasattr(summoner_full, 'previous_seasons') and summoner_full.previous_seasons:
            for s in summoner_full.previous_seasons:
                if hasattr(s, 'tier_info') and s.tier_info:
                    past_ranks.append({
                        "season_id": s.season_id,
                        "tier": f"{s.tier_info.tier} {s.tier_info.division}",
                        "lp": f"{s.tier_info.lp} LP" if s.tier_info.lp is not None else "",
                        "image_url": str(s.tier_info.tier_image_url) if s.tier_info.tier_image_url else ""
                    })
        past_ranks.reverse()

        profile_info = {
            "name": summoner_full.game_name,
            "tag": summoner_full.tagline,
            "level": summoner_full.level,
            "icon_url": str(summoner_full.profile_image_url),
            "rank_solo": solo_rank,
            "past_ranks": past_ranks
        }

    except Exception as e: return print(f"❌ Erreur API Profil : {e}")

    # 3. Récupération des 20 derniers matchs (pour l'accumulation)
    print("📥 Vérification des nouveaux matchs (20 derniers)...")
    try: new_games_raw = opgg.get_recent_games(search_result=search_results[0], results=20)
    except: new_games_raw = []

    # 4. Traitement et Fusion
    known_ids = {g["game_id"] for g in existing_data.get("history", [])}
    processed_new_games = []

    for game in new_games_raw:
        if isinstance(game, list): game = game[0]
        if game.id in known_ids: continue 

        # Extraction Objectifs
        teams_summary = {
            "BLUE": {"kills": 0, "gold": 0, "baron": 0, "dragon": 0, "herald": 0, "grubs": 0},
            "RED":  {"kills": 0, "gold": 0, "baron": 0, "dragon": 0, "herald": 0, "grubs": 0}
        }
        if hasattr(game, 'teams'):
            for team in game.teams:
                key = team.key
                stat = team.game_stat
                teams_summary[key]["kills"] = stat.kill
                teams_summary[key]["gold"] = stat.gold_earned
                teams_summary[key]["baron"] = stat.baron_kill
                teams_summary[key]["dragon"] = stat.dragon_kill
                teams_summary[key]["herald"] = stat.rift_herald_kill
                teams_summary[key]["grubs"] = stat.horde_kill

        damages = [p.stats.total_damage_dealt_to_champions for p in game.participants]
        max_d = max(damages) if damages else 1
        duration_min = max(1, game.game_length_second // 60)

        match_data = {
            "game_id": game.id,
            "timestamp": game.created_at.timestamp() if hasattr(game, 'created_at') else 0,
            "duration": f"{duration_min}m {game.game_length_second % 60}s",
            "summary": teams_summary,
            "teams": {"BLUE": [], "RED": []},
            "my_stats": {},
            "max_damage": max_d
        }

        for p in game.participants:
            stats = p.stats
            cs = stats.minion_kill + (stats.neutral_minion_kill or 0)
            cs_min = round(cs / duration_min, 1)
            team_kills = teams_summary[p.team_key]["kills"]
            p_kill = round(((stats.kill + stats.assist) / team_kills) * 100) if team_kills > 0 else 0
            tier_str = f"{p.tier_info.tier} {p.tier_info.division}" if (hasattr(p, 'tier_info') and p.tier_info and p.tier_info.tier) else "Unranked"
            is_me = (p.summoner.summoner_id == my_id)
            
            p_data = {
                "name": p.summoner.game_name,
                "champion_id": p.champion_id,
                "team": p.team_key, # Clé d'équipe (utilisée ci-dessous)
                "spells": p.spells,
                "items": p.items,
                "runes": p.rune.primary_rune_id if p.rune else None,
                "rune_style": p.rune.primary_page_id if p.rune else None,
                "k": stats.kill, "d": stats.death, "a": stats.assist,
                "kda_ratio": round((stats.kill + stats.assist) / max(1, stats.death), 2),
                "damage": stats.total_damage_dealt_to_champions,
                "wards_placed": stats.ward_place, "wards_control": stats.vision_wards_bought_in_game,
                "cs": cs, "cs_min": cs_min, "op_score": stats.op_score,
                "op_rank": stats.op_score_rank, "p_kill": p_kill,
                "tier": tier_str, "is_me": is_me
            }
            match_data["teams"][p.team_key].append(p_data)
            if is_me: 
                match_data["result"] = stats.result
                match_data["my_stats"] = p_data

        processed_new_games.append(match_data)

    print(f"➕ {len(processed_new_games)} nouvelles parties.")
    all_games = processed_new_games + existing_data.get("history", [])
    all_games.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

    # 5. Calculs Stats Globales
    global_stats = { "total_games": 0, "wins": 0, "losses": 0, "kills": 0, "deaths": 0, "assists": 0 }
    champ_stats_map = defaultdict(lambda: {"g": 0, "w": 0, "k": 0, "d": 0, "a": 0, "cs": 0})
    teammates_map = defaultdict(lambda: {"games": 0, "wins": 0})

    for game in all_games:
        if not game.get("my_stats"): continue
        me = game["my_stats"]
        
        # FIX DE LA KEY ERROR DANS CETTE SECTION
        my_team_key = me.get("team", "BLUE")
        
        global_stats["total_games"] += 1
        if game["result"] == "WIN": global_stats["wins"] += 1
        else: global_stats["losses"] += 1
        global_stats["kills"] += me["k"]; global_stats["deaths"] += me["d"]; global_stats["assists"] += me["a"]
        
        c = champ_stats_map[me["champion_id"]]
        c["g"]+=1; 
        if game["result"] == "WIN": c["w"]+=1
        c["k"]+=me["k"]; c["d"]+=me["d"]; c["a"]+=me["a"]; c["cs"]+=me["cs"]
        
        # Calcul des coéquipiers (maintenant sécurisé)
        if my_team_key in game["teams"]:
            for p in game["teams"][my_team_key]:
                if not p.get("is_me", False):
                    tm = teammates_map[p["name"]]
                    tm["games"] += 1
                    if game["result"] == "WIN": tm["wins"] += 1

    final_champs = []
    for cid, d in champ_stats_map.items():
        kda = round((d["k"]+d["a"])/max(1,d["d"]), 2)
        final_champs.append({"id": cid, "games": d["g"], "winrate": round((d["w"]/d["g"])*100), "kda": f"{kda}:1", "cs": round(d["cs"]/d["g"], 1)})
    final_champs.sort(key=lambda x: x["games"], reverse=True)

    final_mates = []
    for name, data in teammates_map.items():
        if data["games"] > 1: final_mates.append({"name": name, "games": data["games"], "winrate": round((data["wins"]/data["games"])*100), "wins": data["wins"], "losses": data["games"]-data["wins"]})
    final_mates.sort(key=lambda x: x["games"], reverse=True)

    site_data = {
        "profile": profile_info,
        "stats_summary": global_stats,
        "champions_stats": final_champs,
        "recent_teammates": final_mates,
        "history": all_games 
    }

    with open(DB_FILE, "w", encoding='utf-8') as f: json.dump(site_data, f, indent=4, ensure_ascii=False)
    with open("opgg_clone_data.json", "w", encoding='utf-8') as f: json.dump(site_data, f, indent=4, ensure_ascii=False)

    print(f"\n✅ TERMINE ! {len(all_games)} parties prêtes.")

if __name__ == "__main__":
    main()