import os
import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.transport.requests import AuthorizedSession
import time

# Define the scopes required for accessing Google Photos
SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly']

# File to store the user's access and refresh tokens
TOKEN_FILE = 'token.json'

# File containing OAuth 2.0 client credentials
CLIENT_SECRETS_FILE = 'client_secret.json'

# Output directory
DOWNLOAD_DIR = 'vision_photos'

def get_credentials():
    """Get and refresh the credentials for Google Photos API."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    
    return creds

def list_albums(authed_session):
    """List all albums in the user's Google Photos library."""
    albums = []
    nextPageToken = None
    
    while True:
        url = 'https://photoslibrary.googleapis.com/v1/albums'
        params = {'pageSize': 50}
        
        if nextPageToken:
            params['pageToken'] = nextPageToken
        
        response = authed_session.get(url, params=params)
        
        if response.status_code != 200:
            print(f"Error fetching albums: {response.status_code}")
            break
        
        response_json = response.json()
        
        if 'albums' in response_json:
            albums.extend(response_json['albums'])
            print(f"Found {len(response_json['albums'])} albums...")
            
            if 'nextPageToken' in response_json:
                nextPageToken = response_json['nextPageToken']
            else:
                break
        else:
            break
    
    return albums

def find_vision_album(albums):
    """Find the 'vision' album."""
    for album in albums:
        if album.get('title', '').lower() == 'vision':
            return album
    return None

def get_media_items_in_album(authed_session, album_id):
    """Get all media items from a specific album."""
    media_items = []
    nextPageToken = None
    
    while True:
        url = 'https://photoslibrary.googleapis.com/v1/mediaItems:search'
        body = {
            'albumId': album_id,
            'pageSize': 100
        }
        
        if nextPageToken:
            body['pageToken'] = nextPageToken
        
        response = authed_session.post(
            url,
            headers={'content-type': 'application/json'},
            json=body
        )
        
        if response.status_code != 200:
            print(f"Error fetching media items: {response.status_code}")
            break
        
        response_json = response.json()
        
        if 'mediaItems' in response_json:
            media_items.extend(response_json['mediaItems'])
            print(f"Found {len(response_json['mediaItems'])} media items...")
            
            if 'nextPageToken' in response_json:
                nextPageToken = response_json['nextPageToken']
            else:
                break
        else:
            break
    
    return media_items

def download_media_item(url, filename, download_dir):
    """Download a media item from Google Photos."""
    try:
        filepath = os.path.join(download_dir, filename)
        
        # Skip if file already exists
        if os.path.exists(filepath):
            print(f"File {filename} already exists, skipping...")
            return True
        
        # Download the file
        response = requests.get(url)
        response.raise_for_status()
        
        # Write the file
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        print(f"Downloaded: {filename}")
        return True
    except Exception as e:
        print(f"Error downloading {filename}: {e}")
        return False

def main():
    # Create download directory
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    
    print("Authenticating...")
    creds = get_credentials()
    authed_session = AuthorizedSession(creds)
    
    print("Finding albums...")
    albums = list_albums(authed_session)
    
    # Find the vision album
    vision_album = find_vision_album(albums)
    
    if not vision_album:
        print("Couldn't find an album named 'vision'")
        return
    
    print(f"Found 'vision' album with {vision_album.get('mediaItemsCount', '0')} items")
    
    # Get media items from the vision album
    print("Fetching media items...")
    media_items = get_media_items_in_album(authed_session, vision_album['id'])
    
    if not media_items:
        print("No media items found in the 'vision' album")
        return
    
    print(f"Downloading {len(media_items)} items from 'vision' album...")
    
    # Download all media items
    successful = 0
    for i, item in enumerate(media_items):
        # Rate limiting
        if i > 0 and i % 10 == 0:
            time.sleep(1)
        
        # Get base URL
        base_url = item.get('baseUrl')
        if not base_url:
            continue
        
        # Determine file type and extension
        mime_type = item.get('mimeType', '')
        if 'image' in mime_type:
            extension = mime_type.split('/')[-1]
            if extension == 'jpeg':
                extension = 'jpg'
            # High quality download
            download_url = f"{base_url}=d"

        # Get filename
        if 'filename' in item:
            original_filename = item['filename']
            if '.' in original_filename:
                base_name = '.'.join(original_filename.split('.')[:-1])
                filename = f"{base_name}.{extension}"
            else:
                filename = f"{original_filename}.{extension}"
        else:
            filename = f"photo_{i+1}.{extension}"
        
        print(f"Downloading {i+1}/{len(media_items)}: {filename}")
        if download_media_item(download_url, filename, DOWNLOAD_DIR):
            successful += 1
    
    print(f"\nDownload completed. {successful}/{len(media_items)} files downloaded successfully.")
    print(f"Files saved to: {os.path.abspath(DOWNLOAD_DIR)}")

if __name__ == "__main__":
    main()