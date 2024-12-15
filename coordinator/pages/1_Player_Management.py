import streamlit as st
from pickleball.sheets_manager import SheetsManager
from pickleball import config
import pandas as pd

st.set_page_config(page_title="Player Management - Pickleball Round Robin", layout="wide")
sheets_mgr = SheetsManager()

st.title("Player Management")

# Add New Player
st.header("Add New Player")
with st.form("add_player"):
    new_player = st.text_input("New Player Name", key="new_player_input")
    submitted = st.form_submit_button("Add Player")
    if submitted and new_player:
        success, message = sheets_mgr.add_player(new_player)
        if success:
            st.success(message)
            # Clear the input by updating session state
            st.session_state.new_player_input = ""
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
        col1, col2 = st.columns([3, 1])
        with col1:
            status = "✅" if player[config.COL_STATUS] == config.STATUS_ACTIVE else "❌"
            st.write(f"{status} {player[config.COL_NAME]}")
        with col2:
            if st.button("Toggle Status", key=f"toggle_{i}"):
                new_status = config.STATUS_INACTIVE if player[config.COL_STATUS] == config.STATUS_ACTIVE else config.STATUS_ACTIVE
                players_df.loc[players_df[config.COL_NAME] == player[config.COL_NAME], config.COL_STATUS] = new_status
                sheets_mgr.update_sheet(config.SHEET_PLAYERS, [players_df.columns.tolist()] + players_df.values.tolist())
                st.rerun()
