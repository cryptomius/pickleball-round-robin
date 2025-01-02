import streamlit as st
from pickleball.sheets_manager import SheetsManager
from pickleball import config

# Force light theme
st.set_page_config(page_title="Pickleball Tournament Coordinator", layout="wide", initial_sidebar_state="collapsed")

# Add custom CSS
st.markdown("""
    <style>
    .block-container {
        padding: 1.5rem 1.4rem !important;
    }
    .appview-container section:first-child {
        width: 250px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Pickleball Round Robin - Coordinator")
st.write("Welcome to the Pickleball Round Robin Tournament Management System!")
st.write("Please use the sidebar to navigate between different sections:")
st.markdown('1. <a href="Player_Management" target="_self">**Player Management**</a> - Add new players and manage player status', unsafe_allow_html=True)
st.markdown('2. <a href="Match_Management" target="_self">**Match Management**</a> - Generate matches, submit scores, and view court status', unsafe_allow_html=True)
st.markdown('3. <a href="Tournament_Summary" target="_self">**Tournament Summary**</a> - View tournament statistics and current standings', unsafe_allow_html=True)
st.markdown('4. <a href="Player_App" target="_self">**Player App**</a> - View the tournament from a player\'s perspective', unsafe_allow_html=True)
st.markdown('5. <a href="Display_Board" target="_self">**Display Board**</a> - Large format display of current matches and next up queue', unsafe_allow_html=True)
