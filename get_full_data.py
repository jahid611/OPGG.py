import json
import os
from opgg.opgg import OPGG
from opgg.params import Region

def main():
    print("--- 🚀 Démarrage de l'extraction COMPLETE style OP.GG ---")
    opgg = OPGG()
    
    # --- CONFIG ---
    target_name = "Jaydmj23#JSYD"
    target_region = Region.EUW
    # --------------

    print(f"1. Recherche du profil : {target_name}...")
    try:
        search_results = opgg.search(target_name, target_region)
        if not search_results:
            print("❌ Joueur introuvable.")
            return
        player = search_results[0].summoner
        my_id = player.summoner_id
    except Exception as e:
        print(f"❌ Erreur API: {e}")
        return

    # Infos de base du profil (Solorank, Flex, etc.)
    # Note: La librairie ne donne pas toujours facilement les LP actuels hors game,
    # on va utiliser les infos de la dernière game pour l'estimation.
    
    full_data = {
        "profile": {
            "name": player.game_name,
            "tag": player.tagline,
            "level": player.level,
            "icon_url": str(player.profile_image_url),
            "ladder_rank": "N/A", # Pas dispo via cette lib
            "solo_tier": "Unranked",
            "solo_lp": "0"
        },
        "stats_summary": {
            "kills": 0, "deaths": 0, "assists": 0, "wins": 0, "games": 0
        },
        "history": []
    }

    print("2. Analyse des 10 derniers matchs (Mode Détaillé)...")
    games = opgg.get_recent_games(search_result=search_results[0], results=10)

    for i, game in enumerate(games):
        if isinstance(game, list): game = game[0]
        
        # --- INFOS GÉNÉRALES DU MATCH ---
        match_data = {
            "game_id": game.id,
            "game_type": game.game_type, # SOLORANKED, ARAM...
            "time_ago": "Récemment", # Calcul de date complexe, on simplifie
            "duration": f"{game.game_length_second // 60}m {game.game_length_second % 60}s",
            "result": "UNKNOWN", # Sera défini selon le joueur
            "my_stats": {},
            "teams": {"BLUE": [], "RED": []}
        }

        # --- ANALYSE DES 10 JOUEURS ---
        if hasattr(game, 'participants'):
            for p in game.participants:
                stats = p.stats
                summoner = p.summoner
                
                # Calcul CS (Sbires + Monstres neutres)
                cs = stats.minion_kill + (stats.neutral_minion_kill or 0)
                cs_min = round(cs / (game.game_length_second / 60), 1)

                # Info Joueur
                p_data = {
                    "name": summoner.game_name or summoner.internal_name,
                    "tag": summoner.tagline,
                    "champ_id": p.champion_id,
                    "team": p.team_key, # BLUE ou RED
                    "role": p.position,
                    "spells": p.spells, # [id1, id2]
                    "runes": p.rune.primary_rune_id if p.rune else None,
                    "kda": f"{stats.kill}/{stats.death}/{stats.assist}",
                    "k": stats.kill, "d": stats.death, "a": stats.assist,
                    "damage": stats.total_damage_dealt_to_champions,
                    "wards": stats.ward_place,
                    "vision": stats.vision_score,
                    "cs": cs,
                    "cs_min": cs_min,
                    "items": p.items, # Liste des IDs d'items
                    "op_score": stats.op_score,
                    "op_rank": stats.op_score_rank, # 1st, 2nd, etc.
                    "tier": "Unranked"
                }

                # Récupération du rang de ce joueur
                if hasattr(p, 'tier_info') and p.tier_info and p.tier_info.tier:
                    p_data["tier"] = f"{p.tier_info.tier} {p.tier_info.division}"

                # On ajoute à l'équipe correspondante
                match_data["teams"][p.team_key].append(p_data)

                # SI C'EST MOI (L'utilisateur)
                if summoner.summoner_id == my_id:
                    match_data["result"] = stats.result # WIN / LOSE
                    
                    # Mise à jour du résumé global
                    full_data["stats_summary"]["games"] += 1
                    full_data["stats_summary"]["kills"] += stats.kill
                    full_data["stats_summary"]["deaths"] += stats.death
                    full_data["stats_summary"]["assists"] += stats.assist
                    if stats.result == "WIN": full_data["stats_summary"]["wins"] += 1

                    # Mise à jour du rang profil (basé sur la dernière game)
                    if i == 0:
                        full_data["profile"]["solo_tier"] = p_data["tier"]
                        if hasattr(p.tier_info, 'lp'):
                            full_data["profile"]["solo_lp"] = p.tier_info.lp

                    # On copie les stats pour l'affichage résumé
                    match_data["my_stats"] = p_data

        full_data["history"].append(match_data)
        print(f"   -> Match {i+1} traité ({match_data['result']})")

    # 3. Sauvegarde
    with open("full_data.json", "w", encoding='utf-8') as f:
        json.dump(full_data, f, indent=4, ensure_ascii=False)
    
    print("\n✅ Extraction terminée ! Données dans 'full_data.json'")

if __name__ == "__main__":
    main()