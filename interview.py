#interview.py - OpenAI - Saving to Google Drive
import streamlit as st
import time
import pytz
from datetime import datetime
from utils import save_interview_data_to_drive
import config

# Define Central Time
central_tz = pytz.timezone("America/Chicago")
current_datetime = datetime.now(central_tz).strftime("%Y-%m-%d (%H:%M:%S)")

# Select API based on model in config
if "gpt" in config.MODEL.lower():
    from openai import OpenAI
    api = "openai"
    st.session_state.username = f"OpenAI - {current_datetime}"
    client = OpenAI(api_key=st.secrets["API_KEY"])
    api_kwargs = {"stream": True}
    st.set_page_config(page_title="Interview - OpenAI", page_icon=config.AVATAR_INTERVIEWER)

elif "claude" in config.MODEL.lower():
    import anthropic
    api = "anthropic"
    st.session_state.username = f"Anthropic - {current_datetime}"
    client = anthropic.Anthropic(api_key=st.secrets["API_KEY"])
    api_kwargs = {"system": config.SYSTEM_PROMPT}
    st.set_page_config(page_title="Interview - Anthropic", page_icon=config.AVATAR_INTERVIEWER)

# Initialise session state
st.session_state.setdefault("interview_active", True)
st.session_state.setdefault("messages", [])

# Quit button
if st.session_state.interview_active and st.button("Quit", help="End the interview."):
    st.session_state.interview_active = False
    st.session_state.messages.append({"role": "assistant", "content": "You have cancelled the interview."})
    save_interview_data_to_drive(f"{st.session_state.username}-INCOMPLETE.txt", f"{st.session_state.username}-TIME.txt")

# API kwargs
api_kwargs.update({
    "messages": st.session_state.messages,
    "model": config.MODEL,
    "max_tokens": config.MAX_OUTPUT_TOKENS,
})
if config.TEMPERATURE is not None:
    api_kwargs["temperature"] = config.TEMPERATURE

# Initialize system message if empty
if not st.session_state.messages:
    st.session_state.messages.append({"role": "system", "content": config.SYSTEM_PROMPT})
    with st.chat_message("assistant", avatar=config.AVATAR_INTERVIEWER):
        stream = client.chat.completions.create(**api_kwargs)
        message_interviewer = st.write_stream(stream)
    st.session_state.messages.append({"role": "assistant", "content": message_interviewer})

# Chat loop
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

            # Save final transcript to Google Drive
            for code in config.CLOSING_MESSAGES.keys():
                if code in message_interviewer:
                    st.session_state.messages.append({"role": "assistant", "content": message_interviewer})
                    st.session_state.interview_active = False
                    st.markdown(config.CLOSING_MESSAGES[code])
                    save_interview_data_to_drive(f"{st.session_state.username}.txt", f"{st.session_state.username}-TIME.txt")
