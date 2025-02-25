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
    private_key = os.getenv('BOX_PRIVATE_KEY')  # Ensure newlines are properly handled
    passphrase = os.getenv('BOX_PASSPHRASE')

    # Debugging: Check the environment variables
    print(f"Client ID: {client_id}")
    print(f"Client Secret: {client_secret}")
    print(f"Developer Token: {developer_token}")
    print(f"Passphrase: {passphrase is not None}")  # Checking if passphrase is loaded

    # Ensure private_key is correctly loaded (and debug the private_key if needed)
    if private_key:
        private_key = private_key.replace(r'\n', '\n')
    else:
        print("Private key is not loaded properly")

    print(f"Private Key: {'Loaded' if private_key else 'Not Loaded'}")

    # Setup JWT auth with the loaded credentials
    try:
        auth = JWTAuth(
            client_id=client_id,
            client_secret=client_secret,
            developer_token=developer_token,
            private_key_data=private_key,
            passphrase=passphrase
        )
        return Client(auth)
    except Exception as e:
        print(f"Error during JWTAuth setup: {str(e)}")
        return None

# Password screen for dashboard (note: only very basic authentication!)
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

    # After saving the files, upload to Box
    upload_to_box(transcript_file, folder_id="306134958001")
    upload_to_box(time_file, folder_id="306134958001")

def upload_to_box(file_path, folder_id="306134958001"):
    """Upload or update file in Box folder."""
    client = get_box_client()
    
    if not client:
        print("Client is None. Could not establish Box connection.")
        return
    
    folder = client.folder(folder_id)
    file_name = os.path.basename(file_path)

    # Debugging: Confirm the file exists locally
    if not os.path.exists(file_path):
        print(f"File does not exist locally: {file_path}")
        return

    print(f"Attempting to upload file: {file_name} to folder ID: {folder_id}")
    
    # Check if file exists in Box
    existing_files = {item.name: item.id for item in folder.get_items()}

    if file_name in existing_files:
        file = client.file(existing_files[file_name])
        try:
            file.update_contents(file_path)
            print(f"Updated: {file_name}")
        except Exception as e:
            print(f"Error updating file: {e}")
    else:
        try:
            folder.upload(file_path)
            print(f"Uploaded: {file_name}")
        except Exception as e:
            print(f"Error uploading file: {e}")
