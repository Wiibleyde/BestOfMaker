from moviepy import VideoFileClip, TextClip, CompositeVideoClip, concatenate_videoclips
import os

INTRO_PATH = "assets/videos/INTRO.mp4"
OUTRO_PATH = "assets/videos/OUTRO.mp4"
TRANSI_PATH = "assets/videos/TRANSI.mp4"

def _get_existing_clips(paths):
    """Retourne la liste des chemins de clips existants, affiche un avertissement sinon."""
    existing = []
    for path in paths:
        if os.path.exists(path):
            existing.append(path)
        else:
            print(f"Avertissement: Le clip {path} n'existe pas et sera ignoré.")
    return existing

def concatClips(clip_infos: list[tuple[str, str]], output_path: str) -> str:
    """
    Concatène une liste de clips vidéo en une seule vidéo avec MoviePy.
    Chaque élément de clip_infos est un tuple (clip_path, broadcaster_name).
    """
    if not clip_infos:
        print("Aucun clip à concaténer.")
        return ""

    # Préparer la liste finale des chemins de clips (intro, clips, outro)
    all_infos = []
    if os.path.exists(INTRO_PATH):
        all_infos.append((INTRO_PATH, None))
    all_infos.extend(clip_infos)
    if os.path.exists(OUTRO_PATH):
        all_infos.append((OUTRO_PATH, None))
    
    TRANSI_VIDEO = ""
    if os.path.exists(TRANSI_PATH):
        # Ajouter la transition si elle existe
        TRANSI_VIDEO = VideoFileClip(TRANSI_PATH).resized(width=1920, height=1080).with_fps(60)

    # Filtrer les chemins existants et avertir pour les manquants
    valid_infos = []
    for path, name in all_infos:
        if os.path.exists(path):
            # Pour intro/outro, pas de nom de streamer
            if path in (INTRO_PATH, OUTRO_PATH):
                valid_infos.append((path, None))
            else:
                if not name:
                    print(f"Avertissement: broadcaster_name manquant pour {path}, valeur par défaut utilisée.")
                    name = "LeStreamerLuiLà"
                print(f"Ajout du clip: {path} pour le streamer: {name}")
                valid_infos.append((path, name))
        else:
            print(f"Avertissement: Le clip {path} n'existe pas et sera ignoré.")
    if not valid_infos:
        print("Aucun clip valide à concaténer.")
        return ""

    # Créer le dossier de sortie s'il n'existe pas
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Charger les clips vidéo
    video_clips = []
    for path, _ in valid_infos:
        try:
            clip = VideoFileClip(path)
            clip = clip.resized(width=1920, height=1080)
            clip = clip.with_fps(60)
            video_clips.append(clip)
        except Exception as e:
            print(f"Erreur lors de l'ouverture du clip {path}: {e}")

    if not video_clips:
        print("Aucun clip valide à concaténer.")
        return ""

    # Ajouter le texte @streamer sur chaque clip (sauf intro/outro)
    processed_clips = []
    for idx, clip in enumerate(video_clips):
        path, broadcaster_name = valid_infos[idx]
        if path == INTRO_PATH or path == OUTRO_PATH:
            # Ne rien ajouter pour l'intro ou l'outro
            processed_clips.append(clip)
            continue

        if not broadcaster_name:
            broadcaster_name = "LeStreamerLuiLà"
        streamer_tag = f"@{broadcaster_name}"

        # Créer le clip de texte
        txt_clip = TextClip(
            text=streamer_tag,
            font_size=36,
            color='white',
            font='assets/font/Montserrat-VariableFont_wght.ttf',
            bg_color='#00000080',  # Semi-transparent black background
            stroke_color='black',
            stroke_width=2,
            size=(600, 60),
            method='caption'
        ).with_duration(clip.duration).with_position(("right", "bottom"))

        # Superposer le texte sur le clip vidéo
        composite = CompositeVideoClip([clip, txt_clip])
        processed_clips.append(composite)

    try:
        # Utilise compose pour garantir la cohérence de la taille et du framerate
        final_clip = concatenate_videoclips(processed_clips, method="chain", transition=TRANSI_VIDEO if TRANSI_VIDEO else None)
        final_clip.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile="temp-audio.m4a",
            remove_temp=True,
            threads=4,
            preset="veryfast",
            fps=60
        )
        print(f"Vidéo concaténée avec succès: {output_path}")
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"Taille du fichier: {size_mb:.2f} Mo")
        return output_path
    except Exception as e:
        print(f"Erreur lors de la concaténation avec MoviePy: {e}")
        return ""
    finally:
        for clip in video_clips:
            clip.close()

