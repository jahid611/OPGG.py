import json
import os
import logging
from opgg.opgg import OPGG
from opgg.params import Tier, StatsRegion, Queue # On utilise Tier et StatsRegion ici

# Configure le logger pour éviter les warnings dans la console
logging.getLogger("OPGG.py").setLevel(logging.ERROR)

# Définition des rôles à analyser
ROLES_TO_ANALYZE = ["TOP", "JUNGLE", "MID", "ADC", "SUPPORT"]

# Nom du fichier de sortie
OUTPUT_FILE = "matchups_meta_data.json"

def get_deep_matchup_data():
    """
    Récupère toutes les statistiques de champion possibles par rôle (Winrate, Pickrate, KDA, Matchups détaillés)
    pour les tiers Emerald+.
    """
    print("--- 🚀 DÉMARRAGE DE L'EXTRACTION DE LA MÉTA GLOBALE ---")
    opgg = OPGG()
    
    # 1. Récupération des données de base de Riot (Mapping ID -> Nom)
    print("[1/4] Téléchargement des noms de champions...")
    try:
        champions_list = opgg.get_all_champions()
        id_to_name = {champ.id: champ.name for champ in champions_list}
    except Exception as e:
        print(f"❌ Erreur lors du téléchargement des champions : {e}")
        return {}

    # 2. Récupération des stats par rôle (Emerald+)
    print("[2/4] Récupération des stats détaillées (Emerald+ Global)...")
    try:
        # Tente de récupérer la BDD complète des stats de champion
        all_stats_raw = opgg.get_champion_stats(
            tier=Tier.EMERALD_PLUS,
            region=StatsRegion.GLOBAL,
            queue_type=Queue.SOLO 
        )
    except Exception as e:
        print(f"❌ Erreur lors du téléchargement des stats : {e}")
        return {}

    # 3. Consolidation des données par Champion et par Rôle
    print("[3/4] Consolidation des données par Champion/Rôle...")
    
    final_meta_data = {} # Clé: Nom du Champion (str)

    for champ_stat in all_stats_raw:
        champ_id = champ_stat['id']
        champ_name = id_to_name.get(champ_id, "Unknown Champ")
        
        # On initialise la structure pour ce champion
        final_meta_data[champ_name] = {
            "id": champ_id,
            "global_stats": champ_stat['average_stats'],
            "roles_data": {} # Contient TOP, JUNGLE, etc.
        }
        
        for pos_data in champ_stat['positions']:
            role = pos_data['name'] # TOP, JUNGLE, etc.
            
            if role in ROLES_TO_ANALYZE:
                # Extraction des données de performance spécifiques à ce rôle
                role_stats = pos_data['stats']
                
                # Extraction des pires matchups (Counters) pour ce rôle
                matchups = []
                if 'counters' in pos_data:
                    for counter in pos_data['counters']:
                        enemy_name = id_to_name.get(counter['champion_id'], "Unknown Enemy")
                        total_games = counter['play']
                        wins = counter['win']
                        wr_vs_enemy = (wins / total_games) * 100
                        
                        matchups.append({
                            "vs": enemy_name,
                            "win_rate": round(wr_vs_enemy, 2),
                            "games": total_games
                        })
                
                # On trie les matchups pour avoir le pire en premier
                matchups.sort(key=lambda x: x['win_rate'])

                final_meta_data[champ_name]["roles_data"][role] = {
                    "win_rate": round(role_stats['win_rate'] * 100, 2),
                    "pick_rate": round(role_stats['pick_rate'] * 100, 2),
                    "role_rate": round(role_stats['role_rate'] * 100, 2),
                    "kda": round(role_stats['kda'], 2),
                    "matchups": matchups
                }

    # 4. Sauvegarde
    print(f"[4/4] Sauvegarde de la méta dans {OUTPUT_FILE}...")
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(final_meta_data, f, indent=4, ensure_ascii=False)
        print(f"\n✅ SUCCÈS ! Le fichier '{OUTPUT_FILE}' est prêt pour le frontend.")
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde : {e}")
        return {}

    return final_meta_data

if __name__ == "__main__":
    get_deep_matchup_data()