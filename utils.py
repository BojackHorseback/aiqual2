import streamlit as st
import hmac
import time
import os
import json
from boxsdk import JWTAuth, Client

def get_box_client():
    """Initialize Box client using JWT Auth from a secret file."""
    try:
        # Get the file path for Box config
        box_config_path = "/etc/secrets/box_config.json"

        if not os.path.exists(box_config_path):
            print(f"ERROR: Config file not found at {box_config_path}")
            return None  # Return None if the file doesn't exist

        print(f"Loading Box config from: {box_config_path}")

        # Read and parse JSON config file
        with open(box_config_path, "r") as f:
            config_data = json.load(f)

        print("JSON loaded successfully.")

        # Authenticate using JWT
        auth = JWTAuth.from_settings_dictionary(config_data)
        client = Client(auth)

        # Verify authentication by fetching user details
        user = client.user().get()
        print(f"Authenticated as: {user.login}")

        return client

    except json.JSONDecodeError as e:
        print(f"ERROR: JSON parsing failed - {str(e)}")
        return None
    except Exception as e:
        print(f"ERROR: Failed to initialize Box client - {str(e)}")
        return None  

def upload_to_box(file_path, folder_id="306134958001"):
    """Upload file to Box, handling overwrites."""
    client = get_box_client()
    
    if not client:
        print("ERROR: Box client is None. Authentication failed.")
        return
    
    folder = client.folder(folder_id)
    file_name = os.path.basename(file_path)

    if not os.path.exists(file_path):
        print(f"ERROR: File does not exist locally: {file_path}")
        return

    print(f"Uploading file: {file_name} to folder ID: {folder_id}")

    try:
        # Check if the file already exists in Box
        existing_files = {item.name: item.id for item in folder.get_items()}
        
        if file_name in existing_files:
            file_id = existing_files[file_name]
            file = client.file(file_id)
            file.update_contents(file_path)
            print(f"Updated: {file_name}")
        else:
            folder.upload(file_path)
            print(f"Uploaded: {file_name}")

    except Exception as e:
        print(f"ERROR: Failed to upload {file_name} - {str(e)}")
