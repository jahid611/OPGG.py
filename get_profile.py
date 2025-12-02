import json
from opgg.opgg import OPGG
from opgg.params import Region

def main():
    opgg = OPGG()
    
    # --- VOS INFOS ---
    target_name = "jaydmj23#JSYD"
    target_region = Region.EUW
    # -----------------

    print(f"Recherche du joueur {target_name} ({target_region})...")
    try:
        search_results = opgg.search(target_name, target_region)
    except Exception as e:
        print(f"Erreur de recherche : {e}")
        return

    if not search_results:
        print("Joueur introuvable. Vérifiez l'orthographe exacte (Pseudo#TAG).")
        return

    player = search_results[0].summoner
    print(f" -> Trouvé : {player.internal_name} (Niveau {player.level})")
    
    # 2. On récupère l'historique
    print(f"Récupération de l'historique...")
    try:
        # On tente de récupérer 10 games
        games = opgg.get_recent_games(search_result=search_results[0], results=10)
    except Exception as e:
        print(f"Impossible de récupérer l'historique : {e}")
        return
    
    # CORRECTION JSON : On convertit l'URL en string avec str()
    profile_data = {
        "name": player.internal_name,
        "level": player.level,
        "image_url": str(player.profile_image_url), 
        "games": []
    }

    print(f" -> {len(games)} parties récupérées. Analyse en cours...")

    for i, game in enumerate(games):
        # Sécurité pour les listes imbriquées
        if isinstance(game, list):
            if len(game) > 0:
                game = game[0]
            else:
                continue

        # DEBUG : Si myData est vide, on affiche ce qu'il y a dans l'objet game pour comprendre
        if not hasattr(game, 'myData') or game.myData is None:
            print(f" [Info] Partie n°{i+1} ignorée (myData vide).")
            # Décommentez la ligne ci-dessous si vous voulez voir le contenu brut pour déboguer
            # print(f"   -> Contenu brut : {game}") 
            continue

        if not hasattr(game.myData, 'stats') or game.myData.stats is None:
            print(f" [Info] Partie n°{i+1} sans stats.")
            continue

        try:
            stats = game.myData.stats
            
            tier_info = "Normal"
            if hasattr(game, 'average_tier_info') and game.average_tier_info:
                tier_info = game.average_tier_info.tier

            match_info = {
                "champion_id": game.myData.champion_id,
                "win": stats.result == "WIN",
                "kills": stats.kill,
                "deaths": stats.death,
                "assists": stats.assist,
                "op_score": game.myData.op_score,
                "tier": tier_info
            }
            profile_data["games"].append(match_info)
            print(f" [OK] Partie n°{i+1} ajoutée (Champ ID: {game.myData.champion_id})")
            
        except Exception as e:
            print(f" [Erreur] Problème lecture partie n°{i+1}: {e}")
            continue

    # Sauvegarde
    with open("profile.json", "w", encoding='utf-8') as f:
        json.dump(profile_data, f, indent=4, ensure_ascii=False)
    
    print(f"\n✅ Succès ! {len(profile_data['games'])} parties sauvegardées dans profile.json.")

if __name__ == "__main__":
    main()