import streamlit as st
import hmac
import time
import os
from boxsdk import Client, JWTAuth

def get_box_client():
    # Load credentials from environment variables
    client_id = os.getenv('BOX_CLIENT_ID')
    client_secret = os.getenv('BOX_CLIENT_SECRET')
    developer_token = os.getenv('BOX_DEVELOPER_TOKEN')
    private_key = os.getenv('BOX_PRIVATE_KEY')
    passphrase = os.getenv('BOX_PASSPHRASE')

    # Setup JWT auth with the loaded credentials
    auth = JWTAuth(
        client_id=client_id,
        client_secret=client_secret,
        developer_token=developer_token,
        private_key_data=private_key,
        passphrase=passphrase
    )
    
    return Client(auth)



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


def upload_to_box(file_path, folder_id="0"):
    """Upload or update file in Box folder."""
    client = get_box_client()
    folder = client.folder(folder_id)
    file_name = os.path.basename(file_path)

    # Check if file exists in Box
    existing_files = {item.name: item.id for item in folder.get_items()}

    if file_name in existing_files:
        file = client.file(existing_files[file_name])
        file.update_contents(file_path)
        print(f"Updated: {file_name}")
    else:
        folder.upload(file_path)
        print(f"Uploaded: {file_name}")

def save_interview_data(
    username,
    transcripts_directory,
    times_directory,
    file_name_addition_transcript="",
    file_name_addition_time=""
):
    """Write interview data to disk and upload to Box."""

    # Define file paths
    transcript_file = os.path.join(transcripts_directory, f"{username}{file_name_addition_transcript}.txt")
    time_file = os.path.join(times_directory, f"{username}{file_name_addition_time}.txt")

    # Save interview transcript
    with open(transcript_file, "w") as t:
        for message in st.session_state.messages:
            t.write(f"{message['role']}: {message['content']}\n")

    # Save time metadata
    with open(time_file, "w") as d:
        duration = (time.time() - st.session_state.start_time) / 60
        d.write(f"Start: {time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(st.session_state.start_time))}\n")
        d.write(f"Duration: {duration:.2f} min\n")

    # Upload to Box
    upload_to_box(transcript_file, folder_id="306134958001")
    upload_to_box(time_file, folder_id="306134958001")
