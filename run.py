# run.py
import json
from opgg.opgg import OPGG
from opgg.params import Region, Tier, Queue, StatsRegion

def main():
    print("--- Démarrage de OPGG.py ---")
    
    # 1. On initialise l'outil
    opgg = OPGG()
    
    # ---------------------------------------------------------
    # TEST 1 : Chercher un joueur
    # ---------------------------------------------------------
    print("\n[1] Recherche du joueur 'Hide on bush' en Corée...")
    try:
        results = opgg.search("Hide on bush", Region.KR)
        
        if results:
            player = results[0].summoner
            print(f" -> Trouvé ! Joueur : {player.internal_name}")
            print(f" -> Niveau : {player.level}")
            print(f" -> ID : {player.summoner_id}")
        else:
            print(" -> Aucun joueur trouvé.")
    except Exception as e:
        print(f"Erreur lors de la recherche : {e}")

    # ---------------------------------------------------------
    # TEST 2 : Récupérer les Stats (Winrates/Matchups)
    # C'est cette partie qui est utile pour votre site web
    # ---------------------------------------------------------
    print("\n[2] Récupération des stats globales (Emerald+)...")
    try:
        # Cette fonction télécharge les stats de TOUS les champions d'un coup
        stats = opgg.get_champion_stats(
            tier=Tier.EMERALD_PLUS,
            region=StatsRegion.GLOBAL,
            queue_type=Queue.SOLO
        )
        
        print(" -> Stats récupérées !")
        
        # On affiche juste un petit bout pour voir si ça marche
        # (L'objet retourné est souvent une liste ou un dictionnaire complexe)
        print(f" -> Type de données reçu : {type(stats)}")
        
        # Si c'est une liste, on affiche le premier champion
        if isinstance(stats, list) and len(stats) > 0:
            print(f" -> Exemple de données : {stats[0]}")
        elif isinstance(stats, dict):
             # Affiche les clés principales pour comprendre la structure
            print(f" -> Clés disponibles : {list(stats.keys())}")

    except Exception as e:
        print(f"Erreur lors des stats : {e}")

if __name__ == "__main__":
    main()