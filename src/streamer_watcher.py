import asyncio
import json
import os
import time
from datetime import datetime
from src.twitchClips import login, get_broadcasters

# Fichier pour stocker les streamers identifiés
STREAMERS_FILE = "data/tracked_streamers.json"

async def monitor_streamers(game_id: str, search_terms: list[str], interval_minutes: int = 15, max_streamers_per_check: int = 10):
    """
    Surveille en continu les streamers qui diffusent un jeu spécifique avec certains termes dans le titre.
    Exécute la vérification à intervalles réguliers et enregistre les streamers identifiés.
    
    Args:
        game_id: ID du jeu à surveiller
        search_terms: Liste des termes à rechercher dans les titres
        interval_minutes: Intervalle entre les vérifications en minutes
        max_streamers_per_check: Nombre maximum de streamers à récupérer par vérification
    """
    # S'assurer que le dossier data existe
    os.makedirs("data", exist_ok=True)
    
    # Charger les streamers déjà suivis
    tracked_streamers = load_tracked_streamers()
    
    print(f"Service de surveillance des streamers démarré pour le jeu {game_id}")
    print(f"Recherche des termes: {', '.join(search_terms)}")
    print(f"Intervalle de vérification: {interval_minutes} minutes")
    
    twitch = None
    
    try:
        while True:
            try:
                # Connexion/reconnexion à l'API Twitch si nécessaire
                if twitch is None:
                    print("Connexion à l'API Twitch...")
                    twitch = await login()
                
                # Récupérer les streamers actuels
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Recherche de streamers en direct...")
                current_streamers = await get_broadcasters(
                    twitch, 
                    game_id, 
                    search_terms, 
                    first_count=100, 
                    max_streamers=max_streamers_per_check
                )
                
                # Mettre à jour la liste des streamers suivis
                new_streamers = 0
                for streamer in current_streamers:
                    if streamer not in tracked_streamers:
                        tracked_streamers.append(streamer)
                        new_streamers += 1
                
                # Enregistrer la liste mise à jour
                if new_streamers > 0:
                    save_tracked_streamers(tracked_streamers)
                    print(f"Ajouté {new_streamers} nouveaux streamers à la liste de suivi (total: {len(tracked_streamers)})")
                else:
                    print(f"Aucun nouveau streamer trouvé. Liste de suivi actuelle: {len(tracked_streamers)} streamers")
                
            except Exception as e:
                print(f"Erreur lors de la vérification des streamers: {e}")
                twitch = None  # Forcer une reconnexion lors de la prochaine itération
            
            # Attendre l'intervalle spécifié avant la prochaine vérification
            print(f"Prochaine vérification dans {interval_minutes} minutes...")
            await asyncio.sleep(interval_minutes * 60)
            
    except KeyboardInterrupt:
        print("\nSurveillance des streamers arrêtée par l'utilisateur.")

def load_tracked_streamers() -> list:
    """Charge la liste des streamers suivis depuis le fichier JSON."""
    if os.path.exists(STREAMERS_FILE):
        try:
            with open(STREAMERS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Erreur lors du chargement des streamers suivis: {e}")
    return []

def save_tracked_streamers(streamers: list):
    """Enregistre la liste des streamers suivis dans un fichier JSON."""
    try:
        with open(STREAMERS_FILE, 'w') as f:
            json.dump(streamers, f)
    except Exception as e:
        print(f"Erreur lors de l'enregistrement des streamers suivis: {e}")

if __name__ == "__main__":
    # Configuration pour GTA V et MindCity
    GAME_ID = "32982"  # ID de GTA V
    SEARCH_TERMS = ["[MindCityRP]", "[MindCity]", "[MindCity RP]", "[MindCity-RP]"]
    
    # Lancer la surveillance
    asyncio.run(monitor_streamers(GAME_ID, SEARCH_TERMS))
