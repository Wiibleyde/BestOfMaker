import os
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import pickle
import re


def publish_youtube_video(title: str, description: str, video_path: str, thumbnail_path: str):
    # Clean and validate description
    cleaned_description = description.strip()
    
    # Remove problematic control characters but keep UTF-8 characters
    cleaned_description = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', cleaned_description)
    
    # Normalize line breaks
    cleaned_description = cleaned_description.replace('\r\n', '\n').replace('\r', '\n')

    # Replace < and > with their HTML entities to avoid issues
    cleaned_description = cleaned_description.replace('<', '&lt;').replace('>', '&gt;')
    
    # Remove special quotes and replace with standard ones
    cleaned_description = cleaned_description.replace('"', '"').replace('"', '"')
    cleaned_description = cleaned_description.replace(''', "'").replace(''', "'")
    
    # Remove any remaining problematic characters that could cause issues
    cleaned_description = cleaned_description.replace('\x00', '')  # Null bytes
    
    # Validate description length (YouTube limit is 5000 characters)
    if len(cleaned_description) > 5000:
        cleaned_description = cleaned_description[:4997] + "..."

    # Clean title
    title = title.replace('"', '').replace('"', '').replace('"', '').strip()
    
    if not title or not cleaned_description:
        raise ValueError("Title and description cannot be empty.")
    
    print(f"Cleaned description length: {len(cleaned_description)}")
    print(f"Cleaned description: {repr(cleaned_description[:200])}")  # Debug output
    
    scopes = ["https://www.googleapis.com/auth/youtube.upload"]
    client_secrets_file = "client_secret.json"
    token_file = "token.pickle"

    credentials = None
    
    # Charger les credentials existants depuis le fichier token
    if os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            credentials = pickle.load(token)
    
    # Si les credentials n'existent pas ou ne sont plus valides
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            # Actualiser le token
            credentials.refresh(Request())
        else:
            # Première authentification (nécessite interaction une seule fois)
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                client_secrets_file, scopes)
            credentials = flow.run_local_server(port=0)
        
        # Sauvegarder les credentials pour les prochaines utilisations
        with open(token_file, 'wb') as token:
            pickle.dump(credentials, token)

    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=credentials)

    # Préparation des métadonnées
    request_body = {
        "snippet": {
            "title": title,
            "description": cleaned_description,
            "categoryId": "22"  # "People & Blogs"
        },
        "status": {
            "privacyStatus": "unlisted"  # publication en non répertorié
        }
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/*")

    # Upload de la vidéo
    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media
    )

    response = request.execute()
    video_id = response["id"]
    print(f"Vidéo publiée (non répertoriée) : https://youtu.be/{video_id}")

    # Ajout de la miniature
    if thumbnail_path:
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path)
        ).execute()

    return video_id
