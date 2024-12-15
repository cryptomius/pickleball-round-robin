import streamlit as st
from pickleball.sheets_manager import SheetsManager
from pickleball import config
import pandas as pd

st.set_page_config(page_title="Tournament Summary - Pickleball Round Robin", layout="wide")
sheets_mgr = SheetsManager()

st.title("Tournament Summary")

# Get tournament data
players_df = sheets_mgr.read_sheet(config.SHEET_PLAYERS)
matches_df = sheets_mgr.read_sheet(config.SHEET_MATCHES)

if not players_df.empty:
    # Get active players and completed matches
    active_players = players_df[players_df[config.COL_STATUS] == config.STATUS_ACTIVE].copy()
    completed_matches = matches_df[matches_df[config.COL_MATCH_STATUS] == config.STATUS_COMPLETED]
    
    # Display summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Players", len(players_df))
    with col2:
        st.metric("Active Players", len(active_players))
    with col3:
        st.metric("Total Games Completed", len(completed_matches))

    # Add sorting options
    sort_by = st.radio(
        "Sort by",
        ["Total Points", "Average Points Per Game"],
        horizontal=True
    )
    sort_column = config.COL_TOTAL_POINTS if sort_by == "Total Points" else config.COL_AVG_POINTS

    # Convert numeric columns to float
    players_df[config.COL_TOTAL_POINTS] = pd.to_numeric(players_df[config.COL_TOTAL_POINTS], errors='coerce').fillna(0.0)
    players_df[config.COL_AVG_POINTS] = pd.to_numeric(players_df[config.COL_AVG_POINTS], errors='coerce').fillna(0.0)
    players_df[config.COL_GAMES_PLAYED] = pd.to_numeric(players_df[config.COL_GAMES_PLAYED], errors='coerce').fillna(0).astype(int)

    # Overall Standings
    st.header("Overall Standings")
    active_players = players_df[players_df[config.COL_STATUS] == config.STATUS_ACTIVE].copy()
    if not active_players.empty:
        # Sort players by selected column
        active_players = active_players.sort_values(by=sort_column, ascending=False)
        
        # Display standings
        for i, (_, player) in enumerate(active_players.iterrows()):
            gender_icon = "♀️" if player.get(config.COL_GENDER, "") == "W" else ""
            st.write(
                f"{i+1}. {player[config.COL_NAME]} {gender_icon} - "
                f"Points: {float(player[config.COL_TOTAL_POINTS]):.1f} - "
                f"Games: {int(player[config.COL_GAMES_PLAYED])} - "
                f"Avg: {float(player[config.COL_AVG_POINTS]):.1f}"
            )
    else:
        st.write("No active players")

    # Women's Standings
    st.header("Women's Standings")
    active_women = active_players[active_players[config.COL_GENDER] == "W"]
    if not active_women.empty:
        # Sort women players by selected column
        active_women = active_women.sort_values(by=sort_column, ascending=False)
        
        # Display standings
        for i, (_, player) in enumerate(active_women.iterrows()):
            st.write(
                f"{i+1}. {player[config.COL_NAME]} ♀️ - "
                f"Points: {float(player[config.COL_TOTAL_POINTS]):.1f} - "
                f"Games: {int(player[config.COL_GAMES_PLAYED])} - "
                f"Avg: {float(player[config.COL_AVG_POINTS]):.1f}"
            )
    else:
        st.write("No women players registered yet.")
else:
    st.write("No players registered yet")
