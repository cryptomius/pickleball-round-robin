import streamlit as st
from pickleball.sheets_manager import SheetsManager
from pickleball import config
import pandas as pd

st.set_page_config(page_title="Tournament Summary - Pickleball Round Robin", layout="wide")
sheets_mgr = SheetsManager()

st.title("Tournament Summary")

# Get tournament data
players_df = sheets_mgr.read_sheet(config.SHEET_PLAYERS)
if not players_df.empty:
    active_players = players_df[players_df[config.COL_STATUS] == config.STATUS_ACTIVE].copy()
    
    # Get tournament summary
    matches_df = sheets_mgr.read_sheet(config.SHEET_MATCHES)
    completed_matches = matches_df[matches_df[config.COL_MATCH_STATUS] == config.STATUS_COMPLETED]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Players", len(players_df))
    with col2:
        st.metric("Active Players", len(active_players))
    with col3:
        st.metric("Total Games Completed", len(completed_matches))
    
    # Show leaderboard
    st.header("Current Standings")

    # Add sort options
    sort_by = st.radio("Sort by:", ["Total Points", "Average Points per Game"], horizontal=True)

    # Get players who have played games
    players_with_games = active_players[
        active_players[config.COL_GAMES_PLAYED].notna() & 
        (active_players[config.COL_GAMES_PLAYED] != '') & 
        (active_players[config.COL_GAMES_PLAYED] != '0')
    ].copy()
    
    if not players_with_games.empty:
        # Convert numeric columns safely
        players_with_games[config.COL_TOTAL_POINTS] = pd.to_numeric(players_with_games[config.COL_TOTAL_POINTS], errors='coerce').fillna(0)
        players_with_games[config.COL_GAMES_PLAYED] = pd.to_numeric(players_with_games[config.COL_GAMES_PLAYED], errors='coerce').fillna(0)
        players_with_games[config.COL_AVG_POINTS] = pd.to_numeric(players_with_games[config.COL_AVG_POINTS], errors='coerce').fillna(0)
        
        # Calculate average points if needed
        if config.COL_AVG_POINTS not in players_with_games.columns:
            players_with_games[config.COL_AVG_POINTS] = players_with_games[config.COL_TOTAL_POINTS] / players_with_games[config.COL_GAMES_PLAYED].replace(0, 1)
        
        # Sort based on selection
        if sort_by == "Average Points per Game":
            leaderboard = players_with_games.sort_values(by=config.COL_AVG_POINTS, ascending=False)
        else:  # Total Points
            leaderboard = players_with_games.sort_values(by=config.COL_TOTAL_POINTS, ascending=False)
        
        # Display top players
        for i, (_, player) in enumerate(leaderboard.iterrows(), 1):
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            with col1:
                st.write(f"{i}. {player[config.COL_NAME]}")
            with col2:
                st.write(f"Total Points: {player[config.COL_TOTAL_POINTS]:.1f}")
            with col3:
                st.write(f"Games: {int(player[config.COL_GAMES_PLAYED])}")
            with col4:
                st.write(f"Avg: {player[config.COL_AVG_POINTS]:.2f}")
    else:
        st.write("No games played yet")
