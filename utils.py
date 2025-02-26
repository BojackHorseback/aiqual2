import streamlit as st
import hmac
import time
import os
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials

def check_password():
    """Returns 'True' if the user has entered a correct password."""
    def login_form():
        """Form with widgets to collect user information"""
        with st.form("Credentials"):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.form_submit_button("Log in", on_click=password_entered)

    def password_entered():
        """Checks whether username and password entered by the user are correct."""
        if st.session_state.username in st.secrets.passwords and hmac.compare_digest(
            st.session_state.password,
            st.secrets.passwords[st.session_state.username],
        ):
            st.session_state.password_correct = True
        else:
            st.session_state.password_correct = False

        del st.session_state.password  # don't store password in session state

    # Return True, username if password was already entered correctly before
    if st.session_state.get("password_correct", False):
        return True, st.session_state.username

    # Otherwise show login screen
    login_form()
    if "password_correct" in st.session_state:
        st.error("User or password incorrect")
    return False, st.session_state.username


def check_if_interview_completed(directory, username):
    """Check if interview transcript/time file exists which signals that interview was completed."""
    if username != "testaccount":
        try:
            with open(os.path.join(directory, f"{username}.txt"), "r") as _:
                return True
        except FileNotFoundError:
            return False
    return False


def save_interview_data(
    username,
    transcripts_directory,
    times_directory,
    file_name_addition_transcript="",
    file_name_addition_time=""
):
    """Write interview data to disk and upload to Google Drive."""
    transcript_file = os.path.join(transcripts_directory, f"{username}{file_name_addition_transcript}.txt")
    time_file = os.path.join(times_directory, f"{username}{file_name_addition_time}.txt")

    with open(transcript_file, "w") as t:
        for message in st.session_state.messages:
            t.write(f"{message['role']}: {message['content']}\n")

    with open(time_file, "w") as d:
        duration = (time.time() - st.session_state.start_time) / 60
        d.write(f"Start: {time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(st.session_state.start_time))}\n")
        d.write(f"Duration: {duration:.2f} min\n")

    # Upload the files to Google Drive
    upload_to_google_drive(transcript_file)
    upload_to_google_drive(time_file)


def authenticate_google_drive():
    """Authenticate and return Google Drive service."""
    CREDENTIALS_FILE = "/etc/secrets/google_drive_credentials.json"
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=["https://www.googleapis.com/auth/drive.file"])
    service = build("drive", "v3", credentials=creds)
    return service


def upload_to_google_drive(file_path, folder_id="YOUR_GOOGLE_DRIVE_FOLDER_ID"):
    """Upload file to Google Drive, handling overwrites."""
    service = authenticate_google_drive()
    file_name = os.path.basename(file_path)

    file_metadata = {
        "name": file_name,
        "parents": [folder_id]
    }
    media = MediaFileUpload(file_path, resumable=True)

    try:
        existing_files = service.files().list(q=f"name='{file_name}' and '{folder_id}' in parents", fields="files(id)").execute()
        if existing_files.get("files"):
            file_id = existing_files["files"][0]["id"]
            service.files().update(fileId=file_id, media_body=media).execute()
            print(f"Updated: {file_name}")
        else:
            service.files().create(body=file_metadata, media_body=media, fields="id").execute()
            print(f"Uploaded: {file_name}")
    except Exception as e:
        print(f"ERROR: Failed to upload {file_name} - {str(e)}")
