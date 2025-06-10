from PIL import Image, ImageDraw, ImageFont
import os
import requests
from io import BytesIO

from typing import Optional


def generate_youtube_thumbnail(
    image_path: str, date_str: str, output_path: Optional[str] = None
) -> str:
    """
    Génère une miniature YouTube avec le texte 'BEST OF DU {date_str}' superposé.

    Args:
        image_path (str): Chemin vers l'image source ou URL
        date_str (str): Date à afficher dans le texte
        output_path (str, optional): Chemin de sortie. Si None, utilise le nom de l'image source avec '_thumbnail'

    Returns:
        str: Chemin du fichier de sortie
    """
    # Dimensions standard YouTube thumbnail
    YOUTUBE_WIDTH = 1280
    YOUTUBE_HEIGHT = 720

    # Charger l'image (URL ou fichier local)
    if image_path.startswith(('http://', 'https://')):
        # Télécharger l'image depuis l'URL
        response = requests.get(image_path)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
    else:
        # Charger depuis un fichier local
        img = Image.open(image_path)

    with img:
        # Redimensionner l'image aux dimensions YouTube
        img_resized = img.resize(
            (YOUTUBE_WIDTH, YOUTUBE_HEIGHT), Image.Resampling.LANCZOS
        )

        # Convertir en RGB si nécessaire
        if img_resized.mode != "RGB":
            img_resized = img_resized.convert("RGB")

        # Créer un objet de dessin
        draw = ImageDraw.Draw(img_resized)

        # Texte à afficher
        text = f"BEST OF DE LA SEMAINE DU {date_str}"

        # Essayer de charger une police personnalisée, sinon utiliser la police par défaut
        try:
            font_size = 80
            font = ImageFont.truetype(
                "assets/font/Montserrat-VariableFont_wght.ttf", font_size
            )
        except (OSError, IOError):
            font = ImageFont.load_default()
            font_size = 40  # Taille par défaut plus petite pour la police système

        # Ajuster la taille de la police si le texte est trop long
        while font_size > 20:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]

            # Si le texte rentre avec une marge de 40px de chaque côté
            if text_width <= YOUTUBE_WIDTH - 80:
                break

            # Réduire la taille de la police
            font_size -= 5
            try:
                font = ImageFont.truetype(
                    "assets/font/Montserrat-VariableFont_wght.ttf", font_size
                )
            except (OSError, IOError):
                font = ImageFont.load_default()

        # Calculer la position du texte (centré horizontalement, en bas)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = (YOUTUBE_WIDTH - text_width) // 2
        y = YOUTUBE_HEIGHT - text_height - 50  # 50px du bas

        # Ajouter un contour noir pour la lisibilité
        outline_width = 3  # Remettre à 3
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, font=font, fill="black")

        # Dessiner le texte principal en blanc plusieurs fois pour effet gras
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                draw.text((x + dx, y + dy), text, font=font, fill="white")

        # Définir le chemin de sortie
        if output_path is None:
            if image_path.startswith(('http://', 'https://')):
                # Pour les URLs, utiliser un nom générique basé sur la date
                output_path = f"thumbnail_{date_str.replace('/', '_')}.jpg"
            else:
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                output_dir = os.path.dirname(image_path)
                output_path = os.path.join(output_dir, f"{base_name}_thumbnail.jpg")

        # Créer le répertoire de sortie s'il n'existe pas
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # Déterminer le format de sauvegarde basé sur l'extension
        file_extension = os.path.splitext(output_path)[1].lower()
        if file_extension == '.png':
            img_resized.save(output_path, "PNG")
        else:
            # Par défaut, sauvegarder en JPEG
            img_resized.save(output_path, "JPEG", quality=95)

        return output_path
