import streamlit as st
import hmac
import time
import os
from boxsdk import JWTAuth, Client

def get_box_client():
    """Authenticate and return Box client using Streamlit secrets."""
    auth = JWTAuth(
        client_id=st.secrets["box"]["client_id"],
        client_secret=st.secrets["box"]["client_secret"],
        enterprise_id=st.secrets["box"]["enterprise_id"],
        jwt_key_id=st.secrets["box"]["jwt_key_id"],
        rsa_private_key_data=st.secrets["box"]["private_key"].encode(),
        rsa_private_key_passphrase=st.secrets["box"]["passphrase"].encode(),
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

def save_interview_data(username, transcripts_directory, times_directory):
    """Save transcript locally and upload to Box."""
    transcript_file = os.path.join(transcripts_directory, f"{username}.txt")
    time_file = os.path.join(times_directory, f"{username}.txt")

    # Save locally
    with open(transcript_file, "w") as t:
        for message in st.session_state.messages:
            t.write(f"{message['role']}: {message['content']}\n")

    with open(time_file, "w") as d:
        duration = (time.time() - st.session_state.start_time) / 60
        d.write(f"Start: {time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(st.session_state.start_time))}\n")
        d.write(f"Duration: {duration:.2f} min\n")

    # Upload to Box
    upload_to_box(transcript_file, folder_id="306134958001")
    upload_to_box(time_file, folder_id="306134958001")
