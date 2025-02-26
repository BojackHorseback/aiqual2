import streamlit as st
import time
from utils import (
    check_password,
    check_if_interview_completed,
    save_interview_data,
)
import os
import config
import json
import google.auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials

# Path to your Google Drive API credentials
CREDENTIALS_FILE = "/etc/secrets/credentials.json"  # Update for Render secret file

# Define the Google Drive folder ID where you want to upload files
FOLDER_ID = "1tR_afXFbueJStnuDtOF-iW92LgLpZP77"  # Replace with actual Google Drive folder ID

# Authenticate using a Service Account
def authenticate_google_drive():
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=["https://www.googleapis.com/auth/drive.file"])
    service = build("drive", "v3", credentials=creds)
    return service

# Function to upload transcript file to Google Drive
def upload_to_google_drive(file_path, file_name):
    service = authenticate_google_drive()
    file_metadata = {"name": file_name, "parents": [FOLDER_ID]}
    media = MediaFileUpload(file_path, mimetype="text/plain")
    file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    st.success(f"Transcript uploaded to Google Drive: {file_name} (ID: {file.get('id')})")

# Set up Streamlit app
st.set_page_config(page_title="Interview", page_icon=config.AVATAR_INTERVIEWER)

if config.LOGINS:
    pwd_correct, username = check_password()
    if not pwd_correct:
        st.stop()
    st.session_state.username = username
else:
    st.session_state.username = "testaccount"

for directory in [config.TRANSCRIPTS_DIRECTORY, config.TIMES_DIRECTORY, config.BACKUPS_DIRECTORY]:
    os.makedirs(directory, exist_ok=True)

if "interview_active" not in st.session_state:
    st.session_state.interview_active = True
if "messages" not in st.session_state:
    st.session_state.messages = []
if "start_time" not in st.session_state:
    st.session_state.start_time = time.time()
    st.session_state.start_time_file_names = time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime(st.session_state.start_time))

interview_previously_completed = check_if_interview_completed(config.TIMES_DIRECTORY, st.session_state.username)

if interview_previously_completed and not st.session_state.messages:
    st.session_state.interview_active = False
    st.markdown("Interview already completed.")

col1, col2 = st.columns([0.85, 0.15])
with col2:
    if st.session_state.interview_active and st.button("Quit", help="End the interview."):
        st.session_state.interview_active = False
        st.session_state.messages.append({"role": "assistant", "content": "You have cancelled the interview."})
        save_interview_data(st.session_state.username, config.TRANSCRIPTS_DIRECTORY, config.TIMES_DIRECTORY)

for message in st.session_state.messages[1:]:
    avatar = config.AVATAR_INTERVIEWER if message["role"] == "assistant" else config.AVATAR_RESPONDENT
    if not any(code in message["content"] for code in config.CLOSING_MESSAGES.keys()):
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

if st.session_state.interview_active:
    if message_respondent := st.chat_input("Your message here"):
        st.session_state.messages.append({"role": "user", "content": message_respondent})
        with st.chat_message("user", avatar=config.AVATAR_RESPONDENT):
            st.markdown(message_respondent)

if not st.session_state.interview_active:
    save_interview_data(st.session_state.username, config.TRANSCRIPTS_DIRECTORY, config.TIMES_DIRECTORY)
    transcript_file = os.path.join(config.TRANSCRIPTS_DIRECTORY, f"{st.session_state.username}_transcript.txt")
    if os.path.exists(transcript_file):
        upload_to_google_drive(transcript_file, f"{st.session_state.username}_transcript.txt")
    else:
        st.error("Error: Transcript file not found for upload.")
