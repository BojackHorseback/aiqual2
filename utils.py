import streamlit as st
import hmac
import os
import time
import io
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.http import MediaFileUpload
import config

# Initialize session state variables before importing utils
if "username" not in st.session_state:
    st.session_state.username = None  # Default value or placeholder

def save_interview_data_to_drive(transcript_path, time_path):
    """Save interview data (transcript and time) to Google Drive."""
    
    if st.session_state.username is None:
        st.error("Username is not set!")
        return

    username = st.session_state.username

    # Your Google Drive API code here (upload files using username)
    # You can access the username from st.session_state now

    # Example (replace with actual logic):
    st.write(f"Saving interview data for {username}...")

    # Continue with your Google Drive logic

def save_interview_data(username, transcripts_directory, times_directory, file_name_addition_transcript="", file_name_addition_time=""):
    """Write interview data (transcript and time) to disk."""

    # Store chat transcript
    with open(
        os.path.join(
            transcripts_directory, f"{username}{file_name_addition_transcript}.txt"
        ),
        "w",
    ) as t:
        for message in st.session_state.messages:
            t.write(f"{message['role']}: {message['content']}\n")

    # Store file with start time and duration of interview
    with open(
        os.path.join(times_directory, f"{username}{file_name_addition_time}.txt"),
        "w",
    ) as d:
        duration = (time.time() - st.session_state.start_time) / 60
        d.write(
            f"Start time (UTC): {time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(st.session_state.start_time))}\nInterview duration (minutes): {duration:.2f}"
        )


# If modifying Google Drive, ensure the necessary permissions are granted (e.g., write access).
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def authenticate_google_drive():
    """Authenticate with Google Drive API and return service."""
    SCOPES = ["https://www.googleapis.com/auth/drive.file"]

    # Path to token.json stored in /etc/secrets/
    token_path = "/etc/secrets/token.json"
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    else:
        # If token doesn't exist, run the OAuth flow
        creds = None
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    '/mnt/data/credentials.json', SCOPES  # Assuming credentials.json is still stored in /mnt/data/
                )
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run (you can also keep this in /etc/secrets if you prefer)
            with open(token_path, 'w') as token:
                token.write(creds.to_json())

    service = build("drive", "v3", credentials=creds)
    return service

def upload_file_to_drive(service, file_path, file_name, mimetype='text/plain'):
    """Upload a file to Google Drive."""
    file_metadata = {'name': file_name}
    media = MediaIoBaseUpload(io.FileIO(file_path, 'rb'), mimetype=mimetype)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file['id']


# The actual logic for saving the interview data to drive should be part of a Streamlit event like a button click or session state change
def main():
    # Make sure the username is set before proceeding
    if st.session_state.username:
        # Call the save interview data function (wrapped in a button or some event)
        if st.button("Save Interview Data"):
            save_interview_data_to_drive(
                username=st.session_state.username,
                transcripts_directory=config.BACKUPS_DIRECTORY,
                times_directory=config.BACKUPS_DIRECTORY,
                file_name_addition_transcript=f"_transcript_started_{st.session_state.start_time_file_names}",
                file_name_addition_time=f"_time_started_{st.session_state.start_time_file_names}",
            )
            st.success("Interview data saved successfully.")
    else:
        st.error("Please log in first.")

# Run the main function to trigger events
if __name__ == "__main__":
    main()

# Password screen for dashboard (note: only very basic authentication!)
# Based on https://docs.streamlit.io/knowledge-base/deploy/authentication-without-sso
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

    # Test account has multiple interview attempts
    if username != "testaccount":

        # Check if file exists
        try:
            with open(os.path.join(directory, f"{username}.txt"), "r") as _:
                return True

        except FileNotFoundError:
            return False

    else:

        return False
