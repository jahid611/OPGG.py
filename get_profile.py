import json
import os
from opgg.opgg import OPGG
from opgg.params import Region

def main():
    print("--- Démarrage de la récupération du profil ---")
    opgg = OPGG()
    
    # --- TES INFOS ---
    target_name = "jaydmj23#JSYD"
    target_region = Region.EUW
    # -----------------

    print(f"1. Recherche du joueur {target_name}...")
    try:
        search_results = opgg.search(target_name, target_region)
    except Exception as e:
        print(f"❌ Erreur critique recherche : {e}")
        return

    if not search_results:
        print("❌ Joueur introuvable.")
        return

    player = search_results[0].summoner
    my_summoner_id = player.summoner_id
    
    print(f"   -> Trouvé : {player.internal_name} (Niveau {player.level})")
    
    print("2. Téléchargement des derniers matchs...")
    try:
        games = opgg.get_recent_games(search_result=search_results[0], results=10)
    except Exception as e:
        print(f"❌ Erreur historique : {e}")
        return
    
    # Préparation des données pour le site
    profile_data = {
        "name": player.game_name,
        "tag": player.tagline,
        "level": player.level,
        "image_url": str(player.profile_image_url), # Important: convertir en texte
        "games": []
    }

    print(f"   -> {len(games)} matchs récupérés. Extraction des stats...")

    count = 0
    for i, game in enumerate(games):
        if isinstance(game, list): game = game[0]

        # --- RECHERCHE DU JOUEUR DANS LA LISTE DES 10 PARTICIPANTS ---
        my_participant = None
        if hasattr(game, 'participants'):
            for p in game.participants:
                if p.summoner.summoner_id == my_summoner_id:
                    my_participant = p
                    break
        
        if my_participant is None:
            continue # On passe si on ne te trouve pas

        try:
            # On récupère TES stats spécifiques
            stats = my_participant.stats
            
            # Gestion du rang (Emerald, Platinum, etc.)
            tier_txt = "Unranked"
            if hasattr(my_participant, 'tier_info') and my_participant.tier_info:
                 t = my_participant.tier_info
                 if t.tier:
                    tier_txt = f"{t.tier} {t.division} ({t.lp} LP)"

            match_info = {
                "champion_id": my_participant.champion_id,
                "win": stats.result == "WIN",
                "kills": stats.kill,
                "deaths": stats.death,
                "assists": stats.assist,
                "op_score": stats.op_score,
                "tier": tier_txt,
                "role": my_participant.position
            }
            
            profile_data["games"].append(match_info)
            count += 1
            
        except Exception as e:
            print(f"   [!] Erreur lecture match {i+1}: {e}")
            continue

    # 3. Sauvegarde
    print("3. Création du fichier profile.json...")
    try:
        with open("profile.json", "w", encoding='utf-8') as f:
            json.dump(profile_data, f, indent=4, ensure_ascii=False)
        print(f"\n✅ SUCCÈS ! {count} parties sauvegardées dans profile.json")
    except Exception as e:
        print(f"❌ Erreur sauvegarde : {e}")

if __name__ == "__main__":
    main()