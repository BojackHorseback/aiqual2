# UTILS.PY

import streamlit as st
import hmac
import io
import os
from google.oauth2.service_account import Credentials 
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import config

SCOPES = ['https://www.googleapis.com/auth/drive.file']
FOLDER_ID = "1-y9bGuI0nmK22CPXg804U5nZU3gA--lV"  # Google Drive folder ID

def authenticate_google_drive():
    #Authenticate using a service account and return the Google Drive service.
    key_path = "/etc/secrets/service-account.json"
    if not os.path.exists(key_path):
        raise FileNotFoundError("Google Drive credentials file not found! Check Render secrets / environmental variables")
    creds = Credentials.from_service_account_file(key_path, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)

def upload_file_to_drive(service, file_path, file_name, mimetype='text/plain'):
    #Upload to Google Drive folder.
    file_metadata = {
        'name': file_name,
        'parents': [FOLDER_ID]
    }

    with io.FileIO(file_path, 'rb') as file_data:
        media = MediaIoBaseUpload(file_data, mimetype=mimetype)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file['id']

def save_interview_data_to_drive(transcript_path):
    #Save interview transcript & timing data to Google Drive.
    service = authenticate_google_drive()  # Authenticate Drive API

    try:
        transcript_id = upload_file_to_drive(service, transcript_path, os.path.basename(transcript_path))
        st.success(f"Files uploaded! Transcript ID: {transcript_id}")
    except Exception as e:
        st.error(f"Failed to upload files: {e}")


def save_interview_data(username, transcripts_directory, file_name_addition_transcript=""):
    #Write interview data to disk.
    transcript_file = os.path.join(transcripts_directory, f"{username}{file_name_addition_transcript}.txt")

    # Store chat transcript
    with open(transcript_file, "w") as t:
        for message in st.session_state.messages:
            t.write(f"{message['role']}: {message['content']}\n")
