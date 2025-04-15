import streamlit as st 
import time 


def animated_typing_title(text, delay=0.04, font_size="42px", color="#004080"):
    """
    Display the provided text with a typing animation.
    """
    placeholder = st.empty()
    full_text = ""
    for char in text:
        full_text += char
        placeholder.markdown(
            f"<h1 style='color:{color}; font-size: {font_size}; margin: 0'>{full_text}</h1>",
            unsafe_allow_html=True,
        )
        time.sleep(delay)