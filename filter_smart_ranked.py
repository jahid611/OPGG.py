import json
import time
import os
import webbrowser
import opgg.opgg
from opgg.opgg import OPGG
from opgg.params import Region

def main():
    print("\n--- 🧠 ANALYSE D'IMPACT AATROX (Génération Rapport HTML) ---")
    
    ORIGINAL_URL = opgg.opgg._GAMES_API_URL
    bot = OPGG()
    
    # --- CONFIG ---
    target_name = "BoumeSama#EUW"
    target_region = Region.EUW
    target_champ_id = 266 # Aatrox
    target_ranked_count = 50
    # --------------

    print(f"1. Recherche de {target_name}...")
    try:
        search = bot.search(target_name, target_region)
        if not search: return print("❌ Joueur introuvable.")
        my_id = search[0].summoner.summoner_id
    except Exception as e: return print(f"❌ Erreur: {e}")

    # --- 2. RÉCUPÉRATION ---
    ranked_buffer = []
    cursor = ""
    batch = 0
    
    print(f"2. Téléchargement des {target_ranked_count} parties...")

    while len(ranked_buffer) < target_ranked_count and batch < 10:
        batch += 1
        if cursor: opgg.opgg._GAMES_API_URL = ORIGINAL_URL + f"&ended_at={cursor}"
        
        try:
            raw_games = bot.get_recent_games(search_result=search[0], results=20)
            if not raw_games: break

            last = raw_games[-1] if isinstance(raw_games, list) else raw_games
            if isinstance(last, list): last = last[-1]
            if hasattr(last, 'created_at'): cursor = last.created_at.strftime('%Y-%m-%dT%H:%M:%S')

            for g in raw_games:
                if isinstance(g, list): g = g[0]
                if "RANKED" in g.game_type:
                    ranked_buffer.append(g)
            
            print(f"   -> {len(ranked_buffer)}/{target_ranked_count} ranked trouvées...", end="\r")
            time.sleep(1.0) 
        except: break
    
    opgg.opgg._GAMES_API_URL = ORIGINAL_URL
    games_to_analyze = ranked_buffer[:target_ranked_count]
    
    # --- 3. ANALYSE ---
    print(f"\n3. Calcul de l'impact...")
    aatrox_data = []
    
    for game in games_to_analyze:
        my_team = next((p.team_key for p in game.participants if p.summoner.summoner_id == my_id), None)
        if not my_team: continue

        aatrox = next((p for p in game.participants if p.team_key == my_team and p.champion_id == target_champ_id), None)
        
        if aatrox:
            st = aatrox.stats
            team_kills = sum(p.stats.kill for p in game.participants if p.team_key == my_team)
            team_dmg = sum(p.stats.total_damage_dealt_to_champions for p in game.participants if p.team_key == my_team)
            
            kda_val = (st.kill + st.assist) / max(1, st.death)
            dmg_share = (st.total_damage_dealt_to_champions / max(1, team_dmg)) * 100
            p_kill = (st.kill + st.assist) / max(1, team_kills) * 100
            
            # VERDICT
            verdict = "Normal"
            v_class = "normal" # Pour le CSS
            impact_score = (kda_val * 5) + dmg_share + (p_kill / 2)
            
            if st.result == "WIN":
                if impact_score > 80: verdict, v_class = "👑 1v9 HARD CARRY", "carry"
                elif impact_score > 55: verdict, v_class = "💪 Solid Carry", "solid"
                elif impact_score > 35: verdict, v_class = "🚌 Passenger", "passenger"
                else: verdict, v_class = "🍀 Lucky Win", "lucky"
            else: 
                if impact_score > 65: verdict, v_class = "💀 SVP (Team Gap)", "svp"
                elif st.death > 8 and kda_val < 1.5: verdict, v_class = "🤡 FEEDER", "feeder"
                elif dmg_share < 15: verdict, v_class = "💤 Invisible", "invisible"
                else: verdict, v_class = "❌ Diff Top", "diff"

            player_name = "MOI" if aatrox.summoner.summoner_id == my_id else aatrox.summoner.game_name
            
            aatrox_data.append({
                "result": st.result,
                "player": player_name,
                "k": st.kill, "d": st.death, "a": st.assist,
                "kda": round(kda_val, 2),
                "dmg_share": round(dmg_share, 1),
                "dmg_total": st.total_damage_dealt_to_champions,
                "p_kill": round(p_kill, 0),
                "op_score": st.op_score,
                "verdict": verdict,
                "v_class": v_class,
                "items": aatrox.items,
                "date": game.created_at.strftime("%d/%m %H:%M")
            })

    # --- 4. GÉNÉRATION HTML ---
    print("4. Création du rapport HTML...")
    generate_html_report(aatrox_data, len(games_to_analyze))

def generate_html_report(data, total_analyzed):
    if not data: return
    
    wins = sum(1 for g in data if g['result'] == 'WIN')
    total = len(data)
    wr = round((wins/total)*100, 1)

    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <title>Rapport Aatrox - {wr}% WR</title>
        <style>
            :root {{ --bg: #121212; --card: #1e1e1e; --win: #5383e8; --lose: #e84057; --text: #e0e0e0; --gold: #ffb900; }}
            body {{ font-family: 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 40px; }}
            .container {{ max-width: 900px; margin: 0 auto; }}
            
            /* HEADER */
            .header {{ background: var(--card); padding: 30px; border-radius: 12px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; border: 1px solid #333; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
            .title h1 {{ margin: 0; font-size: 2rem; }}
            .subtitle {{ color: #888; margin-top: 5px; }}
            .wr-box {{ text-align: right; }}
            .wr-big {{ font-size: 3rem; font-weight: bold; color: { '#5383e8' if wr >= 50 else '#e84057' }; }}
            .wr-sub {{ color: #888; }}

            /* TABLE */
            .game-list {{ display: flex; flex-direction: column; gap: 10px; }}
            .game-row {{ display: flex; align-items: center; background: var(--card); padding: 15px 20px; border-radius: 8px; border-left: 6px solid #444; transition: transform 0.1s; }}
            .game-row:hover {{ transform: scale(1.01); background: #252525; }}
            
            .game-win {{ border-color: var(--win); background: linear-gradient(90deg, rgba(40,52,78,1) 0%, rgba(30,30,30,1) 40%); }}
            .game-lose {{ border-color: var(--lose); background: linear-gradient(90deg, rgba(89,52,59,1) 0%, rgba(30,30,30,1) 40%); }}

            .col-res {{ width: 80px; font-weight: bold; font-size: 1.1rem; }}
            .text-win {{ color: var(--win); }} .text-lose {{ color: var(--lose); }}
            
            .col-champ {{ width: 60px; }}
            .champ-img {{ width: 48px; height: 48px; border-radius: 50%; border: 2px solid #333; }}
            
            .col-player {{ width: 140px; font-weight: bold; }}
            .tag-me {{ background: #3a3a45; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem; color: #fff; }}

            .col-kda {{ width: 120px; text-align: center; }}
            .kda-main {{ font-size: 1.1rem; font-weight: bold; letter-spacing: 1px; }}
            .kda-sub {{ font-size: 0.8rem; color: #888; }}
            .death {{ color: var(--lose); }}

            .col-stats {{ width: 140px; font-size: 0.9rem; color: #aaa; border-left: 1px solid #333; padding-left: 15px; }}
            .highlight {{ color: #fff; font-weight: bold; }}

            .col-verdict {{ flex: 1; text-align: right; }}
            .badge {{ padding: 6px 12px; border-radius: 20px; font-weight: bold; font-size: 0.85rem; text-transform: uppercase; display: inline-block; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }}
            
            /* VERDICT COLORS */
            .v-carry {{ background: linear-gradient(135deg, #ffd700, #e19205); color: #000; border: 1px solid #fff; }}
            .v-solid {{ background: #2e7d32; color: #fff; }}
            .v-passenger {{ background: #424242; color: #aaa; border: 1px solid #555; }}
            .v-lucky {{ background: #00695c; color: #fff; }}
            .v-svp {{ background: #6a1b9a; color: #fff; border: 1px solid #9c27b0; }}
            .v-feeder {{ background: #c62828; color: #fff; }}
            .v-diff {{ background: #d32f2f; color: #fff; }}
            .v-invisible {{ background: #212121; color: #444; border: 1px dashed #444; }}

            .dmg-bar-bg {{ width: 100%; height: 4px; background: #333; margin-top: 5px; border-radius: 2px; }}
            .dmg-bar-fill {{ height: 100%; background: var(--lose); border-radius: 2px; }}

            .items {{ margin-top: 5px; display: flex; gap: 2px; }}
            .item-img {{ width: 20px; height: 20px; border-radius: 3px; border: 1px solid #333; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="title">
                    <h1>Analyse Aatrox</h1>
                    <div class="subtitle">Sur les {total_analyzed} dernières Ranked (Solo/Flex)</div>
                </div>
                <div class="wr-box">
                    <div class="wr-big">{wr}%</div>
                    <div class="wr-sub">{wins}W - {total - wins}L</div>
                </div>
            </div>

            <div class="game-list">
    """

    for g in data:
        is_win = g['result'] == 'WIN'
        res_txt = "VICTOIRE" if is_win else "DÉFAITE"
        row_class = "game-win" if is_win else "game-lose"
        text_class = "text-win" if is_win else "text-lose"
        
        items_html = "".join([f'<img src="https://ddragon.leagueoflegends.com/cdn/14.23.1/img/item/{i}.png" class="item-img">' for i in g['items'] if i > 0])
        
        html += f"""
        <div class="game-row {row_class}">
            <div class="col-res">
                <div class="{text_class}">{res_txt}</div>
                <div style="font-size:0.75rem; color:#666; font-weight:normal;">{g['date']}</div>
            </div>
            <div class="col-champ">
                <img src="https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/266.png" class="champ-img">
            </div>
            <div class="col-player">
                {g['player']} { '<span class="tag-me">MOI</span>' if g['player'] == 'MOI' else '' }
                <div class="items">{items_html}</div>
            </div>
            <div class="col-kda">
                <div class="kda-main">{g['k']} / <span class="death">{g['d']}</span> / {g['a']}</div>
                <div class="kda-sub">{g['kda']} KDA</div>
            </div>
            <div class="col-stats">
                <div>Dégâts: <span class="highlight">{g['dmg_share']}%</span></div>
                <div class="dmg-bar-bg"><div class="dmg-bar-fill" style="width: {min(g['dmg_share'], 100)}%"></div></div>
                <div style="margin-top:4px;">P/Kill: {g['p_kill']}%</div>
            </div>
            <div class="col-verdict">
                <span class="badge v-{g['v_class']}">{g['verdict']}</span>
                <div style="font-size:0.8rem; color:#666; margin-top:5px;">OP Score {g['op_score']}</div>
            </div>
        </div>
        """

    html += """
            </div>
        </div>
    </body>
    </html>
    """

    filename = "rapport_aatrox.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"\n✅ Rapport généré : {filename}")
    # Ouvre automatiquement le fichier dans le navigateur
    webbrowser.open('file://' + os.path.realpath(filename))

if __name__ == "__main__":
    main()