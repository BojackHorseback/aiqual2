#interview.py - OpenAI - Saving to Google Drive
## at the end of a line denotes the line needs to be updated if the API changes

import streamlit as st
import time
from utils import (
    save_interview_data,
    save_interview_data_to_drive,
)
import os
import config
import pytz
from datetime import datetime


# Define Central Time and get current_datetime
central_tz = pytz.timezone("America/Chicago")
current_datetime = datetime.now(central_tz).strftime("%Y-%m-%d (%H:%M:%S)")


#Bunch o stuff
if "gpt" in config.MODEL.lower(): #Check config for API type
    api = "openai" #Set API type
    from openai import OpenAI #Import API specific library
    client = OpenAI(api_key=st.secrets["API_KEY"])
    api_kwargs = {"stream": True}
    st.set_page_config(page_title="Interview - OpenAI", page_icon=config.AVATAR_INTERVIEWER) #Set page title and icon
elif "claude" in config.MODEL.lower(): #Same as above
    api = "anthropic"
    import anthropic
    client = anthropic.Anthropic(api_key=st.secrets["API_KEY"])
    api_kwargs = {"system": config.SYSTEM_PROMPT}
    st.set_page_config(page_title="Interview - Anthropic", page_icon=config.AVATAR_INTERVIEWER)


# Create directories if they do not already exist
for directory in [config.TRANSCRIPTS_DIRECTORY, config.BACKUPS_DIRECTORY]:
    os.makedirs(directory, exist_ok=True)

# Initialise session state
st.session_state.setdefault("interview_active", True)
st.session_state.setdefault("messages", [])

# Add 'Quit' button to dashboard
col1, col2 = st.columns([0.85, 0.15])
with col2:
    if st.session_state.interview_active and st.button("Quit", help="End the interview."):
        st.session_state.interview_active = False
        st.session_state.messages.append({"role": "assistant", "content": "You have cancelled the interview."})
        save_interview_data_to_drive(
                        os.path.join(config.TRANSCRIPTS_DIRECTORY, f"{st.session_state.username}-INCOMPLETE.txt")
                    )

# API kwargs
api_kwargs.update({
    "messages": st.session_state.messages,
    "model": config.MODEL,
    "max_tokens": config.MAX_OUTPUT_TOKENS,
})
if config.TEMPERATURE is not None:
    api_kwargs["temperature"] = config.TEMPERATURE


# Main chat if interview is active
if st.session_state.interview_active:
    if message_respondent := st.chat_input("Your message here"):
        st.session_state.messages.append({"role": "user", "content": message_respondent})

        with st.chat_message("user", avatar=config.AVATAR_RESPONDENT):
            st.markdown(message_respondent)

        with st.chat_message("assistant", avatar=config.AVATAR_INTERVIEWER):
            message_placeholder = st.empty()
            message_interviewer = ""

            stream = client.chat.completions.create(**api_kwargs)
            for message in stream:
                text_delta = message.choices[0].delta.content
                if text_delta:
                    message_interviewer += text_delta
                if len(message_interviewer) > 5:
                    message_placeholder.markdown(message_interviewer + "▌")
                if any(code in message_interviewer for code in config.CLOSING_MESSAGES.keys()):
                    message_placeholder.empty()
                    break

            if not any(code in message_interviewer for code in config.CLOSING_MESSAGES.keys()):
                message_placeholder.markdown(message_interviewer)
                st.session_state.messages.append({"role": "assistant", "content": message_interviewer})

                try:
                    save_interview_data(
                        username=st.session_state.username,
                        transcripts_directory=config.BACKUPS_DIRECTORY,
                    )
                except:
                    pass

            for code in config.CLOSING_MESSAGES.keys():
                if code in message_interviewer:
                    st.session_state.messages.append({"role": "assistant", "content": message_interviewer})
                    st.session_state.interview_active = False
                    st.markdown(config.CLOSING_MESSAGES[code])

                    final_transcript_stored = False
                    retries = 0
                    max_retries = 10
                    while not final_transcript_stored and retries < max_retries:
                        save_interview_data(
                            username=st.session_state.username,
                            transcripts_directory=config.TRANSCRIPTS_DIRECTORY,
                        )
                        time.sleep(0.1)
                        retries += 1

                    save_interview_data_to_drive(
                        os.path.join(config.TRANSCRIPTS_DIRECTORY, f"{st.session_state.username}.txt")
                    )
