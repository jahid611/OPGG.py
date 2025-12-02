import json
import logging
from opgg.opgg import OPGG
from opgg.params import Region, Tier, Queue, StatsRegion

# 1. On configure le silence pour ne plus voir les WARNINGS rouges
logging.getLogger("OPGG.py").setLevel(logging.ERROR)

def main():
    print("--- Génération des données pour le site de Matchups ---")
    opgg = OPGG()

    # Etape A : Récupérer la liste des champions (ID -> Nom)
    # On a besoin de savoir que ID 86 = Garen
    print("[1/3] Téléchargement des noms de champions...")
    champions_list = opgg.get_all_champions()
    
    # On crée un dictionnaire simple : {86: "Garen", 1: "Annie", ...}
    id_to_name = {champ.id: champ.name for champ in champions_list}
    print(f" -> {len(id_to_name)} champions identifiés.")

    # Etape B : Récupérer les stats globales (Emerald+)
    print("[2/3] Récupération des statistiques Top Lane...")
    stats = opgg.get_champion_stats(
        tier=Tier.EMERALD_PLUS,
        region=StatsRegion.GLOBAL,
        queue_type=Queue.SOLO
    )

    final_data = []

    # Etape C : Traitement des données
    for champ_stat in stats:
        # On cherche le nom du champion grâce à son ID
        champ_name = id_to_name.get(champ_stat['id'], "Inconnu")
        
        # On cherche si ce champion est joué au TOP
        top_data = None
        for pos in champ_stat['positions']:
            if pos['name'] == 'TOP':
                top_data = pos
                break
        
        # Si le champion n'est pas joué au top, on passe au suivant
        if not top_data:
            continue

        # On prépare l'objet pour notre site
        my_champion = {
            "name": champ_name,
            "win_rate": round(top_data['stats']['win_rate'] * 100, 2), # Ex: 51.2%
            "matchups": []
        }

        # On analyse ses counters (matchups)
        # Note: L'API renvoie parfois peu de counters, ou seulement les plus fréquents
        if 'counters' in top_data:
            for counter in top_data['counters']:
                enemy_name = id_to_name.get(counter['champion_id'], "Enemy")
                
                # Calcul du winrate contre cet ennemi
                total_games = counter['play']
                wins = counter['win']
                wr_vs_enemy = (wins / total_games) * 100
                
                my_champion["matchups"].append({
                    "vs": enemy_name,
                    "win_rate": round(wr_vs_enemy, 2),
                    "games": total_games
                })

        final_data.append(my_champion)

    # Etape D : Sauvegarde en JSON
    print(f"[3/3] Sauvegarde de {len(final_data)} champions Top...")
    with open("data_site.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, indent=4, ensure_ascii=False)

    print("\n✅ Succès ! Le fichier 'data_site.json' est prêt.")

if __name__ == "__main__":
    main()