import os
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from googleapiclient.http import MediaFileUpload


def publish_youtube_video(title, description, video_path, thumbnail_path):
    scopes = ["https://www.googleapis.com/auth/youtube.upload"]
    client_secrets_file = "client_secret.json"

    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        client_secrets_file, scopes)
    credentials = flow.run_local_server(port=0)

    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=credentials)

    # Préparation des métadonnées
    request_body = {
        "snippet": {
            "title": title,
            "description": description,
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
