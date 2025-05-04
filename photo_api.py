import os
import pandas as pd
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.transport.requests import AuthorizedSession

# Define the scopes required for accessing Google Photos
scopes = ['https://www.googleapis.com/auth/photoslibrary.readonly']

# File to store the user's access and refresh tokens
TOKEN_FILE = 'token.json'
# File containing OAuth 2.0 client credentials
CLIENT_SECRETS_FILE = 'client_secret.json'

def get_credentials():
    creds = None
    # Check if token file exists with user credentials
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, scopes)
    
    # If no valid credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, scopes)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    
    return creds

def main():
    # Get user credentials
    creds = get_credentials()
    print("Authentication successful!")
    
    # Create an authorized session
    authed_session = AuthorizedSession(creds)
    
    # Variables for pagination
    nextPageToken = None
    idx = 0
    media_items = []
    
    # Retrieve all media items matching the filter
    while True:
        idx += 1
        print(f"Fetching page {idx}...")
        
        response = authed_session.post(
            'https://photoslibrary.googleapis.com/v1/mediaItems:search',
            headers={'content-type': 'application/json'},
            json={
                "pageSize": 100,
                "pageToken": nextPageToken,
                "filters": {
                    "dateFilter": {
                        "ranges": [{
                            "startDate": {
                                "year": 2023,
                                "month": 1,
                                "day": 1,
                            },
                            "endDate": {
                                "year": 2023,
                                "month": 1,
                                "day": 26,
                            }
                        }]
                    }
                }
            })
        
        response_json = response.json()
        
        # Check if the response contains media items
        if "mediaItems" in response_json:
            media_items += response_json["mediaItems"]
        else:
            print(f"No media items found or error in response: {response_json}")
            break
        
        # Check for next page token
        if "nextPageToken" not in response_json:
            break
            
        nextPageToken = response_json["nextPageToken"]
    
    # Process results if we have any media items
    if media_items:
        print(f"Found {len(media_items)} media items")
        
        # Create DataFrame from results
        photos_df = pd.DataFrame(media_items)
        photos_df = pd.concat([photos_df, pd.json_normalize(photos_df.mediaMetadata).rename(
            columns={"creationTime": "creationTime_metadata"})], axis=1)
        photos_df["creationTime_metadata_dt"] = photos_df.creationTime_metadata.astype("datetime64")
        
        # Display sample of results
        print(photos_df.head())
        print(f"\nSample item (index 25 if available):")
        if len(photos_df) > 25:
            print(photos_df.iloc[25])
    else:
        print("No media items found for the specified date range")

if __name__ == "__main__":
    main()