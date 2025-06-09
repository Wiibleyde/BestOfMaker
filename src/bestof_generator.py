import asyncio
import json
import os
import shutil
from datetime import datetime
from src.twitchClips import (
    login,
    get_clips_with_term,
    get_broadcaster_id,
    download_clip,
    Clip,
)
from src.videoAssembler import concatClips, INTRO_PATH
from moviepy import VideoFileClip


# Fichier pour stocker les streamers identifiés
STREAMERS_FILE = "data/tracked_streamers.json"
# Dossier pour stocker les best-of
BESTOF_DIR = "bestof"


async def generate_weekly_bestof(
    max_clips_per_streamer: int = 30, total_bestof_clips: int = 20
):
    """
    Génère un best-of hebdomadaire à partir des clips des streamers suivis.

    Args:
        max_clips_per_streamer: Nombre maximum de clips à récupérer par streamer
        total_bestof_clips: Nombre total de clips à inclure dans le best-of final
    """
    print(f"Démarrage de la génération du best-of hebdomadaire...")

    # Vérifier que le fichier des streamers existe
    if not os.path.exists(STREAMERS_FILE):
        print(f"Erreur: Fichier de suivi des streamers {STREAMERS_FILE} introuvable.")
        return

    # Créer le dossier bestof s'il n'existe pas
    os.makedirs(BESTOF_DIR, exist_ok=True)

    # Créer un dossier temporaire pour les clips
    temp_dir = f"{BESTOF_DIR}/temp"
    os.makedirs(temp_dir, exist_ok=True)

    # Charger la liste des streamers suivis
    tracked_streamers = load_tracked_streamers()
    if not tracked_streamers:
        print("Aucun streamer suivi trouvé.")
        return

    print(f"Génération du best-of pour {len(tracked_streamers)} streamers suivis.")

    # Se connecter à l'API Twitch
    twitch = await login()

    # Récupérer tous les clips des streamers suivis
    all_clips = []

    for streamer in tracked_streamers:
        try:
            print(f"Récupération des clips pour {streamer}...")

            # Obtenir l'ID du streamer
            broadcaster_id = await get_broadcaster_id(twitch, streamer)

            # Récupérer les clips du streamer
            streamer_clips = await get_clips_with_term(
                twitch,
                broadcaster_id=broadcaster_id,
                term="",
                first_count=max_clips_per_streamer,
            )

            print(f"Récupéré {len(streamer_clips)} clips pour {streamer}")
            all_clips.extend(streamer_clips)

            # Petit délai entre chaque streamer
            await asyncio.sleep(2)

        except Exception as e:
            print(f"Erreur lors de la récupération des clips pour {streamer}: {e}")

    # D'abord trier tous les clips par nombre de vues (du plus vu au moins vu)
    all_clips.sort(key=lambda clip: clip.view_count, reverse=True)

    # Sélectionner les X meilleurs clips basés sur le nombre de vues
    best_clips = all_clips[:total_bestof_clips]

    if not best_clips:
        print("Aucun clip trouvé pour générer le best-of.")
        return

    print(
        f"\nSélection des {len(best_clips)} meilleurs clips sur {len(all_clips)} clips récupérés."
    )
    print("Clips sélectionnés (par nombre de vues):")
    for i, clip in enumerate(
        best_clips[:5]
    ):  # Afficher les 5 premiers pour vérification
        print(f"  {i+1}. {clip.title} - {clip.view_count} vues - {clip.created_at}")
    if len(best_clips) > 5:
        print(f"  ... et {len(best_clips) - 5} autres clips")

    # ENSUITE trier les meilleurs clips par date (du plus ancien au plus récent)
    # pour préserver l'ordre chronologique dans la vidéo finale
    best_clips.sort(key=lambda clip: clip.created_at)

    print("\nOrdre final pour la vidéo (chronologique):")
    for i, clip in enumerate(
        best_clips[:5]
    ):  # Afficher les 5 premiers pour vérification
        print(f"  {i+1}. {clip.created_at} - {clip.title} - {clip.view_count} vues")
    if len(best_clips) > 5:
        print(f"  ... et {len(best_clips) - 5} autres clips")

    # Télécharger les clips
    downloaded_paths = []

    for i, clip in enumerate(best_clips):
        try:
            print(
                f"Téléchargement du clip {i+1}/{len(best_clips)}: {clip.title} ({clip.view_count} vues)..."
            )

            # Générer un nom de fichier basé sur l'ordre et l'ID du clip
            save_path = f"{temp_dir}/{i+1:02d}_{clip.id}.mp4"

            success = download_clip(clip.url, save_path)

            if success:
                downloaded_paths.append((save_path, clip.broadcaster_name))

            # Petit délai entre téléchargements
            await asyncio.sleep(1)

        except Exception as e:
            print(f"Erreur lors du téléchargement du clip {clip.url}: {e}")

    # Générer le nom du fichier best-of avec la date
    date_str = datetime.now().strftime("%Y-%m-%d")
    bestof_file = f"{BESTOF_DIR}/bestof_{date_str}.mp4"

    # Assembler les clips téléchargés
    if downloaded_paths:
        print(f"\nAssemblage de {len(downloaded_paths)} clips en une vidéo best-of...")

        # Trier les chemins par nom de fichier pour respecter l'ordre
        downloaded_paths.sort()

        final_path = concatClips(downloaded_paths, bestof_file)

        if final_path:
            print(f"Best-of hebdomadaire créé avec succès: {final_path}")

            # Enregistrer les métadonnées du best-of
            save_bestof_metadata(best_clips, final_path, date_str)
        else:
            print("Échec de la création du best-of.")
    else:
        print("Aucun clip téléchargé, impossible de créer le best-of.")

    # Nettoyage du dossier temporaire
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
        print(f"Dossier temporaire {temp_dir} supprimé.")


def load_tracked_streamers() -> list:
    """Charge la liste des streamers suivis depuis le fichier JSON."""
    if os.path.exists(STREAMERS_FILE):
        try:
            with open(STREAMERS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Erreur lors du chargement des streamers suivis: {e}")
    return []


def save_bestof_metadata(clips: list[Clip], file_path: str, date_str: str):
    """Enregistre les métadonnées du best-of dans un fichier JSON avec timecodes."""

    def format_timecode(seconds):
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def serialize_clip(clip, timecode):
        # Convertit created_at en string si nécessaire
        created_at = clip.created_at
        if hasattr(created_at, "isoformat"):
            created_at = created_at.isoformat()
        return {
            "id": clip.id,
            "title": clip.title,
            "broadcaster": clip.broadcaster_name,
            "views": clip.view_count,
            "created_at": created_at,
            "url": clip.url,
            "timecode": format_timecode(timecode),  # timecode au format mm:ss
        }

    # Récupérer la durée de l'intro si elle existe
    intro_duration = 0.0
    if os.path.exists(INTRO_PATH):
        try:
            with VideoFileClip(INTRO_PATH) as intro_clip:
                intro_duration = intro_clip.duration
        except Exception as e:
            print(f"Erreur lors de la lecture de la durée de l'intro: {e}")

    # Calculer les timecodes pour chaque clip (en tenant compte de l'intro)
    timecodes = []
    current_time = intro_duration
    for clip in clips:
        timecodes.append(current_time)
        current_time += getattr(clip, "duration", 0)

    # Générer le titre YouTube avec le clip le plus vu
    most_viewed_clip = max(clips, key=lambda clip: clip.view_count)
    # Convertir la date au format DD/MM/YYYY
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    formatted_date = date_obj.strftime("%d/%m/%Y")
    youtube_title = f"{most_viewed_clip.title} - BEST OF DU {formatted_date}"

    # Générer la description YouTube avec la liste des clips
    clips_list = "\n".join(
        [
            f"{format_timecode(timecode)} : {clip.broadcaster_name} - {clip.title}"
            for clip, timecode in zip(clips, timecodes)
        ]
    )

    youtube_description = f"""Voici le best of du {formatted_date} j'espère qu'il vous plaira ! 
Ce best of est généré automatiquement en fonction des clips fait par les streamer du serveur, donc si un moment vous plait et vous pensez qu'il serait bien dans ce best of, il vous suffit de créer le clip et qu'il soit parmis les plus vu de la semaine ! 

Les clips de la semaine :
{clips_list}

Si quelque chose vous semble bizzare, n'hésitez pas à contacter @Wiibleyde sur les réseaux sociaux (Discord de préférence) ! 

Merci pour votre présence et à la semaine prochaine !"""

    metadata = {
        "date": date_str,
        "youtube_title": youtube_title,
        "youtube_description": youtube_description,
        "file_path": file_path,
        "clips_count": len(clips),
        "total_views": sum(clip.view_count for clip in clips),
        "clips": [
            serialize_clip(clip, timecode) for clip, timecode in zip(clips, timecodes)
        ],
    }

    metadata_file = f"{BESTOF_DIR}/bestof_{date_str}_metadata.json"

    try:
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print(f"Métadonnées du best-of enregistrées dans {metadata_file}")
    except Exception as e:
        print(f"Erreur lors de l'enregistrement des métadonnées: {e}")


if __name__ == "__main__":
    # Lancer la génération du best-of
    asyncio.run(generate_weekly_bestof())
