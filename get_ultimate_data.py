import json
import os
import time
from collections import defaultdict
from opgg.opgg import OPGG
from opgg.params import Region

# Nom du fichier de sauvegarde
DB_FILE = "opgg_database.json"

def main():
    print("--- 🚀 Démarrage Extraction Massive (Boucle par 20) ---")
    opgg = OPGG()
    
    # --- TA CONFIG ---
    target_name = "Jaydmj23#JSYD"
    target_region = Region.EUW
    target_total_games = 100  # Combien on en veut au total
    # ---------------

    # 1. Charger la mémoire existante
    existing_data = {"history": []}
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding='utf-8') as f:
                existing_data = json.load(f)
            print(f"📂 Mémoire chargée : {len(existing_data['history'])} parties déjà stockées.")
        except:
            print("⚠️ Mémoire vide ou illisible.")

    known_ids = {g["game_id"] for g in existing_data["history"]}

    # 2. Recherche du joueur
    print(f"📡 Recherche du profil {target_name}...")
    try:
        search_results = opgg.search(target_name, target_region)
        if not search_results: return print("❌ Joueur introuvable.")
        player = search_results[0].summoner
        my_id = player.summoner_id
    except Exception as e: return print(f"❌ Erreur API: {e}")

    # 3. Récupération par paquets de 20 (La boucle magique)
    all_new_games_raw = []
    
    # On détermine la date du dernier match connu pour ne pas tout retélécharger inutilement
    last_known_timestamp = 0
    if existing_data["history"]:
        # On suppose que l'historique est trié du plus récent au plus vieux
        # Mais pour la pagination OP.GG, on utilise souvent l'ID de la dernière game téléchargée comme curseur
        pass 

    print(f"📥 Démarrage du téléchargement par paquets de 20...")
    
    # OP.GG utilise souvent un système où on demande les games APRÈS une certaine date ou ID.
    # Cependant, la librairie OPGG.py actuelle ne semble pas exposer facilement le paramètre "ended_at" pour la pagination.
    # ASTUCE : On va faire une boucle simple. Si la librairie ne gère pas la pagination interne,
    # on est limité à ce qu'elle offre. 
    # MAIS : Essayons de forcer la limite à 20 plusieurs fois si possible, ou acceptons les 20/40 dispos.
    
    # Note technique : La librairie OPGG.py semble coder en dur la logique de requête.
    # Si get_recent_games ne permet pas de dire "donne moi les games AVANT telle date", on est coincé à 20 par appel.
    # Tentons une approche différente : récupérer le JSON complet via la méthode interne si possible,
    # ou se contenter d'accumuler jour après jour.
    
    # Solution pragmatique : On lance la requête standard. Si elle limite à 20,
    # c'est que l'API interne bloque.
    # Cependant, accumuler les données JOUR APRÈS JOUR remplira les 100 games en 5 jours.
    
    # Tentative de forcer la limite max acceptée (souvent 40 ou 50)
    try:
        # On tente 40, souvent le max toléré avant 422
        print("   Tentative de récupération de 40 matchs...")
        new_games_raw = opgg.get_recent_games(search_result=search_results[0], results=40)
    except:
        print("   ⚠️ Repli sur 20 matchs (limite stricte API).")
        new_games_raw = opgg.get_recent_games(search_result=search_results[0], results=20)

    # 4. Analyse et Fusion
    processed_new_games = []
    new_count = 0

    print("🔄 Traitement des données...")

    for i, game in enumerate(new_games_raw):
        if isinstance(game, list): game = game[0]
        
        # Anti-doublon CRITIQUE ici
        if game.id in known_ids:
            continue

        # --- Extraction (Identique au script précédent) ---
        total_kills_blue = sum(p.stats.kill for p in game.participants if p.team_key == "BLUE")
        total_kills_red = sum(p.stats.kill for p in game.participants if p.team_key == "RED")
        
        all_damages = [p.stats.total_damage_dealt_to_champions for p in game.participants]
        max_damage = max(all_damages) if all_damages else 1
        
        duration_min = game.game_length_second // 60
        
        match_data = {
            "game_id": game.id,
            "timestamp": game.created_at.timestamp() if hasattr(game, 'created_at') else 0,
            "type": game.game_type,
            "ago": "Récemment",
            "duration": f"{duration_min}m {game.game_length_second % 60}s",
            "result": "UNKNOWN",
            "teams": {"BLUE": [], "RED": []},
            "my_stats": {},
            "total_kills_blue": total_kills_blue,
            "total_kills_red": total_kills_red,
            "max_damage": max_damage
        }

        for p in game.participants:
            stats = p.stats
            cs = stats.minion_kill + (stats.neutral_minion_kill or 0)
            cs_min = round(cs / (duration_min if duration_min > 0 else 1), 1)
            
            team_kills = total_kills_blue if p.team_key == "BLUE" else total_kills_red
            p_kill = 0
            if team_kills > 0: p_kill = round(((stats.kill + stats.assist) / team_kills) * 100)

            tier_str = "Unranked"
            if hasattr(p, 'tier_info') and p.tier_info and p.tier_info.tier:
                tier_str = f"{p.tier_info.tier} {p.tier_info.division}"

            is_me = (p.summoner.summoner_id == my_id)
            
            p_data = {
                "name": p.summoner.game_name or p.summoner.internal_name,
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
                "cs": cs, "cs_min": cs_min,
                "op_score": stats.op_score,
                "op_rank": stats.op_score_rank,
                "p_kill": p_kill,
                "tier": tier_str,
                "is_me": is_me
            }
            
            if is_me and hasattr(p, 'tier_info') and p.tier_info:
                 p_data["lp"] = p.tier_info.lp

            match_data["teams"][p.team_key].append(p_data)

            if is_me:
                match_data["result"] = stats.result
                match_data["my_stats"] = p_data

        processed_new_games.append(match_data)
        new_count += 1

    print(f"➕ {new_count} nouvelles parties ajoutées à la base.")

    # 5. Fusion & Calculs
    all_games = processed_new_games + existing_data["history"]
    # Tri chronologique inverse (plus récent en premier)
    all_games.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

    print(f"🧮 Base de données totale : {len(all_games)} parties.")
    
    global_stats = { "total_games": 0, "wins": 0, "losses": 0, "kills": 0, "deaths": 0, "assists": 0 }
    champ_stats_map = defaultdict(lambda: {"games": 0, "wins": 0, "kills": 0, "deaths": 0, "assists": 0, "cs": 0})
    teammates_map = defaultdict(lambda: {"games": 0, "wins": 0})
    current_rank_info = {"tier": "Unranked", "lp": "0 LP"}

    for idx, game in enumerate(all_games):
        if "my_stats" not in game or not game["my_stats"]: continue
        
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
        c["kills"] += me["k"]
        c["deaths"] += me["d"]
        c["assists"] += me["a"]
        c["cs"] += me["cs"]

        if idx == 0 and "tier" in me and me["tier"] != "Unranked":
            current_rank_info = { "tier": me["tier"], "lp": f"{me.get('lp', 0)} LP" }

        my_team = me["team"]
        for p in game["teams"][my_team]:
            if not p["is_me"]:
                tm = teammates_map[p["name"]]
                tm["games"] += 1
                if game["result"] == "WIN": tm["wins"] += 1

    final_champs = []
    for cid, data in champ_stats_map.items():
        wr = round((data["wins"] / data["games"]) * 100)
        kda = round((data["kills"] + data["assists"]) / max(1, data["deaths"]), 2)
        cs = round(data["cs"] / data["games"], 1)
        final_champs.append({"id": cid, "games": data["games"], "winrate": wr, "kda": f"{kda}:1", "cs": cs})
    final_champs.sort(key=lambda x: x["games"], reverse=True)

    final_mates = []
    for name, data in teammates_map.items():
        if data["games"] > 1:
            wr = round((data["wins"] / data["games"]) * 100)
            final_mates.append({"name": name, "games": data["games"], "winrate": wr, "wins": data["wins"], "losses": data["games"]-data["wins"]})
    final_mates.sort(key=lambda x: x["games"], reverse=True)

    site_data = {
        "profile": {
            "name": player.game_name,
            "tag": player.tagline,
            "level": player.level,
            "icon_url": str(player.profile_image_url),
            "ranks": [{
                "queue": "Ranked Solo",
                "tier": current_rank_info["tier"],
                "lp": current_rank_info["lp"]
            }]
        },
        "stats_summary": global_stats,
        "champions_stats": final_champs,
        "recent_teammates": final_mates,
        "history": all_games 
    }

    with open(DB_FILE, "w", encoding='utf-8') as f:
        json.dump(site_data, f, indent=4, ensure_ascii=False)
    
    with open("opgg_clone_data.json", "w", encoding='utf-8') as f:
        json.dump(site_data, f, indent=4, ensure_ascii=False)

    print(f"\n✅ TERMINÉ ! {len(all_games)} matchs disponibles dans le frontend.")

if __name__ == "__main__":
    main()