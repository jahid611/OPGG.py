import pprint
from opgg.opgg import OPGG
from opgg.params import Region

def main():
    print("--- DIAGNOSTIC DE LA STRUCTURE GAME ---")
    opgg = OPGG()
    
    # Vos infos
    name = "jaydmj23#JSYD"
    region = Region.EUW

    # 1. Recherche
    print(f"Recherche de {name}...")
    try:
        results = opgg.search(name, region)
        if not results:
            print("Joueur non trouvé.")
            return
        player = results[0].summoner
    except Exception as e:
        print(f"Erreur recherche: {e}")
        return

    # 2. Récupération d'une seule game
    print("Récupération de la dernière partie...")
    try:
        games = opgg.get_recent_games(search_result=results[0], results=1)
    except Exception as e:
        print(f"Erreur historique: {e}")
        return

    if not games:
        print("Aucune partie trouvée.")
        return

    game = games[0]
    
    # Si c'est une liste (cas rare), on prend l'élément
    if isinstance(game, list):
        game = game[0]

    print("\n" + "="*40)
    print("TYPE DE L'OBJET GAME :", type(game))
    print("="*40)

    # 3. On essaie d'afficher tous les attributs disponibles
    print("\n[LISTE DES ATTRIBUTS DISPONIBLES] :")
    try:
        # On essaie de lister les clés si c'est un dictionnaire ou un objet Pydantic
        if hasattr(game, '__dict__'):
            pprint.pprint(game.__dict__)
        elif hasattr(game, 'dict'): # Pydantic V1
            pprint.pprint(game.dict())
        elif hasattr(game, 'model_dump'): # Pydantic V2
            pprint.pprint(game.model_dump())
        else:
            print("Impossible de lire les attributs proprement, affichage brut :")
            print(game)
    except Exception as e:
        print(f"Erreur lors de l'affichage des attributs : {e}")
        print("Affichage brut de secours :")
        print(game)

    print("\n" + "="*40)
    print("Merci de copier-coller ce résultat dans le chat !")

if __name__ == "__main__":
    main()