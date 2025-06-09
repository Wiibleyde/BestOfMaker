from twitchAPI.twitch import Twitch
from twitchAPI.helper import first
from datetime import datetime, timedelta, timezone
import asyncio
import os
import subprocess
from dataclasses import dataclass
from dotenv import load_dotenv  # Ajouté pour charger les variables d'environnement


@dataclass
class Clip:
    """Classe représentant un clip Twitch avec ses métadonnées essentielles."""

    id: str
    url: str
    title: str
    broadcaster_name: str
    thumbnail_url: str = ""
    view_count: int = 0
    created_at: str = ""
    duration: float = 0


# Charger les variables d'environnement depuis un fichier .env
load_dotenv()


async def login() -> Twitch:
    client_id = os.getenv("TWITCH_CLIENT_ID")
    client_secret = os.getenv("TWITCH_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise ValueError("TWITCH_CLIENT_ID et TWITCH_CLIENT_SECRET doivent être définis dans le fichier .env")
    twitch = Twitch(client_id, client_secret)
    await twitch.authenticate_app([])
    return twitch


async def get_clips_with_term(
    twitch: Twitch,
    game_id: str = None,
    term: str = None,
    broadcaster_id: str = None,
    first_count: int = 100,
    max_clips: int = 500,
) -> list[Clip]:
    """
    Récupère les clips de la semaine dernière pour un jeu et/ou un streamer spécifique.
    Filtre les clips dont le titre contient le terme donné, si fourni.

    Args:
        twitch: Instance Twitch authentifiée
        game_id: ID du jeu (optionnel si broadcaster_id est fourni)
        term: Terme à rechercher dans le titre (optionnel)
        broadcaster_id: ID du streamer (optionnel si game_id est fourni)
        first_count: Nombre de clips par page (max 100)
        max_clips: Nombre maximum total de clips à récupérer

    Returns:
        Liste d'objets Clip correspondant aux critères
    """
    # Vérifier qu'au moins un critère de filtrage est fourni
    if game_id is None and broadcaster_id is None:
        raise ValueError(
            "Au moins un des paramètres game_id ou broadcaster_id doit être fourni"
        )

    # Calculer la période de la semaine dernière
    now = datetime.now(timezone.utc)
    last_week = now - timedelta(days=7)

    print(
        f"Recherche de clips depuis {last_week.isoformat()} jusqu'à {now.isoformat()}"
    )
    if game_id:
        print(f"Pour le jeu ID: {game_id}")
    if broadcaster_id:
        print(f"Pour le streamer ID: {broadcaster_id}")
    if term:
        print(f"Contenant le terme: '{term}'")

    # Récupérer les clips
    clips = []
    clip_count = 0
    batch_count = 0
    request_delay = 4.0  # 4 secondes entre chaque lot

    try:
        # Préparer les paramètres pour la requête
        clip_params = {"started_at": last_week, "ended_at": now, "first": first_count}

        # IMPORTANT: L'API exige exactement UN des paramètres suivants
        # Selon la doc, on ne peut pas combiner game_id et broadcaster_id
        if broadcaster_id:
            clip_params["broadcaster_id"] = broadcaster_id
        elif game_id:
            clip_params["game_id"] = game_id
        else:
            raise ValueError(
                "Au moins un des paramètres game_id ou broadcaster_id doit être fourni"
            )

        # Obtenir le générateur de clips
        clip_generator = twitch.get_clips(**clip_params)

        # Récupérer les clips jusqu'à la limite
        async for clip in clip_generator:
            # Vérifier que le clip provient bien du jeu demandé (si game_id est fourni)
            if game_id is not None:
                if not hasattr(clip, "game_id") or str(clip.game_id) != str(game_id):
                    continue  # Ignore les clips qui ne sont pas du jeu demandé

            # Si broadcaster_name absent, le récupérer via l'API
            print(
                getattr(clip, "broadcaster_name")
            )
            if not hasattr(clip, "broadcaster_name") or not clip.broadcaster_name:
                try:
                    user = await first(twitch.get_users(ids=[clip.broadcaster_id]))
                    print(
                        f"AAAAAAAAAAAAAAAAAAAAAA Récupération du nom du broadcaster pour l'ID {clip.broadcaster_id}..."
                    )
                    if user and hasattr(user, "display_name"):
                        clip.broadcaster_name = user.display_name
                    elif user and hasattr(user, "login"):
                        clip.broadcaster_name = user.login
                    else:
                        clip.broadcaster_name = clip.broadcaster_id
                except Exception as e:
                    print(f"Erreur lors de la récupération du nom du broadcaster pour l'ID {clip.broadcaster_id}: {e}")
                    clip.broadcaster_name = clip.broadcaster_id

            clips.append(clip)
            clip_count += 1

            if clip_count % 10 == 0:
                print(f"Récupéré {clip_count} clips...")

            if clip_count >= max_clips:
                print(f"Atteint la limite de {max_clips} clips")
                break

            # Ajouter un délai tous les 'first_count' clips pour éviter le rate limit
            if clip_count % first_count == 0:
                batch_count += 1
                print(
                    f"Délai de {request_delay} secondes après le lot {batch_count}..."
                )
                await asyncio.sleep(request_delay)

    except Exception as e:
        print(f"Erreur lors de la récupération des clips: {e}")

    print(f"Récupéré {len(clips)} clips au total")

    # Si un terme est fourni, on filtre par titre, sinon on retourne tous les clips
    if term:
        term_lower = term.lower()
        filtered_clips = [
            clip
            for clip in clips
            if hasattr(clip, "title") and term_lower in clip.title.lower()
        ]
        print(
            f"Après filtrage: {len(filtered_clips)} clips contenant le terme '{term}'"
        )
    else:
        filtered_clips = clips

    # Convertir en objets Clip
    result_clips = []
    for clip in filtered_clips:
        try:
            clip_obj = Clip(
                id=clip.id,
                url=clip.url,
                title=clip.title,
                broadcaster_name=clip.broadcaster_name,
                thumbnail_url=getattr(clip, "thumbnail_url", ""),
                view_count=getattr(clip, "view_count", 0),
                created_at=getattr(clip, "created_at", ""),
                duration=getattr(clip, "duration", 0),
            )
            result_clips.append(clip_obj)
        except AttributeError as e:
            print(f"Erreur lors de la conversion du clip: {e}")

    print(f"Converti {len(result_clips)} clips en objets Clip")
    return result_clips


async def get_game_id(twitch: Twitch, game_name: str) -> str:
    game = await first(twitch.get_games(names=[game_name]))
    if game:
        return game.id
    raise ValueError(f"Game '{game_name}' not found.")


async def get_broadcasters(
    twitch: Twitch,
    game_id: str,
    terms: list[str] | str,
    first_count: int = 100,
    max_streamers: int = 2,
) -> list:
    """
    Récupère les streamers qui diffusent actuellement (à l'instant T) un jeu spécifique
    et dont le titre du stream contient un ou plusieurs termes donnés.

    Args:
        twitch: Instance Twitch authentifiée
        game_id: ID du jeu
        terms: Terme(s) à rechercher dans le titre du stream (chaîne ou liste de chaînes)
        first_count: Nombre de streams par page (max 100)
        max_streamers: Nombre maximum total de streamers à récupérer

    Returns:
        Liste des streamers correspondants
    """
    # Convertir le terme en liste s'il est fourni comme chaîne
    if isinstance(terms, str):
        terms = [terms]

    terms_lower = [term.lower() for term in terms]
    terms_str = "', '".join(terms)

    print(
        f"Recherche de streamers diffusant actuellement le jeu ID {game_id} avec l'un des termes suivants dans le titre: '{terms_str}'"
    )

    # Liste pour stocker les noms des streamers
    broadcasters = []
    stream_count = 0
    batch_count = 0
    request_delay = 4.0  # 4 secondes entre chaque lot

    try:
        # Obtenir le générateur de streams actuels
        stream_generator = twitch.get_streams(game_id=game_id, first=first_count)

        # Parcourir les streams et filtrer ceux avec un des termes dans le titre
        async for stream in stream_generator:
            stream_count += 1

            # Vérifier si le titre contient l'un des termes recherchés
            if hasattr(stream, "title") and hasattr(stream, "user_name"):
                title_lower = stream.title.lower()

                # Vérifier si l'un des termes est présent dans le titre
                if any(term in title_lower for term in terms_lower):
                    # Filtrer les noms d'utilisateur avec des caractères non-ASCII
                    if all(c.isascii() for c in stream.user_name):
                        # Trouver quel terme a matché pour l'afficher
                        matched_terms = [
                            term for term in terms_lower if term in title_lower
                        ]
                        matched_str = "', '".join(matched_terms)

                        broadcasters.append(stream.user_name)
                        print(
                            f"Trouvé streamer: {stream.user_name} - Titre: {stream.title}"
                        )
                        print(f"  >> Termes trouvés: '{matched_str}'")

            # Afficher la progression
            if stream_count % 10 == 0:
                print(
                    f"Analysé {stream_count} streams, trouvé {len(broadcasters)} streamers..."
                )

            # Arrêter si on atteint le nombre maximum de streamers
            if len(broadcasters) >= max_streamers:
                print(f"Atteint la limite de {max_streamers} streamers")
                break

            # Ajouter un délai tous les first_count streams
            if stream_count % first_count == 0 and stream_count > 0:
                batch_count += 1
                print(
                    f"Délai de {request_delay} secondes après le lot {batch_count}..."
                )
                await asyncio.sleep(request_delay)

    except Exception as e:
        print(f"Erreur lors de la récupération des streamers: {e}")

    print(
        f"Trouvé {len(broadcasters)} streamers diffusant actuellement le jeu ID {game_id} avec l'un des termes recherchés"
    )
    return broadcasters


async def get_broadcaster_id(twitch: Twitch, username: str) -> str:
    """
    Récupère l'ID d'un streamer à partir de son nom d'utilisateur.

    Args:
        twitch: Instance Twitch authentifiée
        username: Nom d'utilisateur du streamer

    Returns:
        ID du streamer
    """
    try:
        # Filtrer les caractères non-ASCII qui peuvent causer des problèmes
        filtered_username = "".join(c for c in username if c.isascii())
        if not filtered_username:
            raise ValueError(f"Nom d'utilisateur non valide après filtrage: {username}")

        # Si le nom a été modifié, informer
        if filtered_username != username:
            print(
                f"Attention: Nom d'utilisateur modifié de '{username}' à '{filtered_username}' pour compatibilité"
            )
            username = filtered_username

        user = await first(twitch.get_users(logins=[username]))
        if user:
            return user.id
        raise ValueError(f"Streamer '{username}' not found.")
    except Exception as e:
        raise ValueError(
            f"Erreur lors de la récupération de l'ID pour '{username}': {e}"
        )


def download_clip(url_clip: str, destination_file: str) -> bool:
    """
    Télécharge un clip Twitch à partir de son URL en utilisant yt-dlp et le sauvegarde dans un fichier spécifique.

    Args:
        url_clip (str): L'URL du clip Twitch à télécharger.
        destination_file (str): Le chemin complet du fichier où sauvegarder le clip (incluant l'extension).

    Returns:
        bool: True si le téléchargement a réussi, False sinon.
    """
    # Vérification de l'URL
    if not (
        url_clip.startswith("https://clips.twitch.tv/")
        or url_clip.startswith("https://www.twitch.tv/")
        or url_clip.startswith("https://twitch.tv/")
    ):
        print(
            f"Avertissement : L'URL '{url_clip}' peut ne pas être un clip Twitch valide."
        )

    # S'assurer que le dossier parent existe
    parent_dir = os.path.dirname(destination_file)
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)

    try:
        # Commande yt-dlp avec options optimisées
        commande = [
            "yt-dlp",
            "--no-playlist",  # Ne pas télécharger les playlists
            "--geo-bypass",  # Contourner les restrictions géographiques
            "--no-warnings",  # Réduire les avertissements
            "-o",
            destination_file,  # Fichier de destination exact
            url_clip,
        ]

        print(f"Téléchargement de {url_clip} vers {destination_file}")

        # Exécution de la commande
        resultat = subprocess.run(commande, capture_output=True, text=True, check=True)

        # Vérifier si le fichier a bien été créé
        if os.path.exists(destination_file):
            print(f"Clip téléchargé avec succès: {destination_file}")
            return True
        else:
            # Chercher si le fichier a été sauvegardé avec une extension différente
            base_path = os.path.splitext(destination_file)[0]
            potential_files = [
                f
                for f in os.listdir(parent_dir or ".")
                if os.path.isfile(os.path.join(parent_dir or ".", f))
                and f.startswith(os.path.basename(base_path))
            ]

            if potential_files:
                print(f"Clip téléchargé avec un nom différent: {potential_files[0]}")
                return True
            else:
                print(
                    "Téléchargement semble terminé mais le fichier n'a pas été trouvé."
                )
                return False

    except subprocess.CalledProcessError as e:
        print(f"Erreur lors du téléchargement: {e}")
        if e.stderr:
            print(f"Détails: {e.stderr}")
        return False

    except FileNotFoundError:
        print("Erreur: yt-dlp n'est pas installé ou n'est pas dans le PATH.")
        print("Installez-le avec: pip install yt-dlp")
        return False

    except Exception as e:
        print(f"Erreur inattendue: {e}")
        return False


async def prepare_clip_infos(clips: list[Clip], download_dir: str) -> list[tuple[str, str]]:
    """
    Prépare une liste de tuples (chemin_du_clip, broadcaster_name) pour l'assemblage vidéo.
    Télécharge les clips si besoin.
    """
    clip_infos = []
    for clip in clips:
        # Génère un nom de fichier unique pour chaque clip
        safe_title = "".join(c if c.isalnum() else "_" for c in clip.title)[:40]
        filename = f"{clip.broadcaster_name}_{safe_title}_{clip.id}.mp4"
        filepath = os.path.join(download_dir, filename)
        # Télécharge le clip si le fichier n'existe pas déjà
        if not os.path.exists(filepath):
            success = download_clip(clip.url, filepath)
            if not success:
                print(f"Échec du téléchargement pour {clip.url}")
                continue
        clip_infos.append((filepath, clip.broadcaster_name))
    return clip_infos
