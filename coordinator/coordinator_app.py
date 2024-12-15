import streamlit as st
from pickleball.sheets_manager import SheetsManager
from pickleball import config

st.set_page_config(
    page_title="Pickleball Round Robin - Coordinator",
    page_icon="🏸",
    layout="wide",
)

st.title("Pickleball Round Robin - Coordinator")
st.write("Welcome to the Pickleball Round Robin Tournament Management System!")
st.write("Please use the sidebar to navigate between different sections:")
st.write("1. **Player Management**: Add new players and manage player status")
st.write("2. **Match Management**: Generate matches, submit scores, and view court status")
st.write("3. **Tournament Summary**: View tournament statistics and current standings")

