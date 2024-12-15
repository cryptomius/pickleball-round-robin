import streamlit as st
from pickleball.sheets_manager import SheetsManager
from pickleball import config
import pandas as pd

st.set_page_config(page_title="Player Management - Pickleball Round Robin", layout="wide")
sheets_mgr = SheetsManager()

st.title("Player Management")

# Add New Player
st.header("Add New Player")

# Initialize session state for form
if 'new_player_input' not in st.session_state:
    st.session_state.new_player_input = ""
if 'is_woman' not in st.session_state:
    st.session_state.is_woman = False

# Handle form reset
if 'form_submitted' not in st.session_state:
    st.session_state.form_submitted = False

if st.session_state.form_submitted:
    st.session_state.new_player_input = ""
    st.session_state.is_woman = False
    st.session_state.form_submitted = False
    st.rerun()

with st.form("add_player"):
    new_player = st.text_input("New Player Name", key="new_player_input")
    is_woman = st.checkbox("Woman Player", key="is_woman")
    submitted = st.form_submit_button("Add Player")
    if submitted and new_player:
        success, message = sheets_mgr.add_player(new_player, is_woman)
        if success:
            st.success(message)
            st.session_state.form_submitted = True
            st.rerun()
        else:
            st.error(message)

# Get and sort players alphabetically
players_df = sheets_mgr.read_sheet(config.SHEET_PLAYERS)
players_df = players_df.sort_values(by=config.COL_NAME)

# Display players section with status toggles
st.header("Players")
if not players_df.empty:
    for i, (_, player) in enumerate(players_df.iterrows()):
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            status = "✅" if player[config.COL_STATUS] == config.STATUS_ACTIVE else "❌"
            gender = "♀️" if player.get(config.COL_GENDER, "") == "W" else ""
            st.write(f"{status} {player[config.COL_NAME]} {gender}")
        with col2:
            if st.button("Toggle Status", key=f"toggle_{i}"):
                new_status = config.STATUS_INACTIVE if player[config.COL_STATUS] == config.STATUS_ACTIVE else config.STATUS_ACTIVE
                players_df.loc[players_df[config.COL_NAME] == player[config.COL_NAME], config.COL_STATUS] = new_status
                sheets_mgr.update_sheet(config.SHEET_PLAYERS, [players_df.columns.tolist()] + players_df.values.tolist())
                st.rerun()
