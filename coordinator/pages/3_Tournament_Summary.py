import streamlit as st
from pickleball.sheets_manager import SheetsManager
from pickleball import config
import pandas as pd

st.set_page_config(page_title="Tournament Summary - Pickleball Round Robin", layout="wide")
sheets_mgr = SheetsManager()

st.title("Tournament Summary")

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

    # Add key for match types
    st.markdown("""
    **Match Types:** M = Men's Doubles, W = Women's Doubles, X = Mixed Doubles
    """)

    # Convert numeric columns to float
    players_df[config.COL_TOTAL_POINTS] = pd.to_numeric(players_df[config.COL_TOTAL_POINTS], errors='coerce').fillna(0.0)
    players_df[config.COL_GAMES_PLAYED] = pd.to_numeric(players_df[config.COL_GAMES_PLAYED], errors='coerce').fillna(0).astype(int)

    # Function to get match types for a player
    def get_player_match_types(player_name):
        player_matches = completed_matches[
            (completed_matches[config.COL_TEAM1_PLAYER1] == player_name) |
            (completed_matches[config.COL_TEAM1_PLAYER2] == player_name) |
            (completed_matches[config.COL_TEAM2_PLAYER1] == player_name) |
            (completed_matches[config.COL_TEAM2_PLAYER2] == player_name)
        ]
        match_counts = {"M": 0, "W": 0, "X": 0}
        for _, match in player_matches.iterrows():
            match_type = match[config.COL_MATCH_TYPE]
            if match_type == "Mens":
                match_counts["M"] += 1
            elif match_type == "Womens":
                match_counts["W"] += 1
            elif match_type == "Mixed":
                match_counts["X"] += 1
        
        # Build string with repeated letters
        result = ""
        for match_type in ["X", "M", "W"]:  # Order: Mixed, Men's, Women's
            result += match_type * match_counts[match_type]
        return result

    # Create three columns for standings
    standings_col1, standings_col2, standings_col3 = st.columns(3)

    # Overall Standings
    with standings_col1:
        st.header("Overall Standings")
        active_players = players_df[players_df[config.COL_STATUS] == config.STATUS_ACTIVE].copy()
        if not active_players.empty:
            # Sort players by total points
            active_players = active_players.sort_values(by=config.COL_TOTAL_POINTS, ascending=False)
            
            # Display standings
            for i, (_, player) in enumerate(active_players.iterrows()):
                gender_icon = "♀️" if player[config.COL_GENDER] == config.GENDER_FEMALE else "♂️"
                match_types = get_player_match_types(player[config.COL_NAME])
                st.write(
                    f"{i+1}. {player[config.COL_NAME]} {gender_icon} - "
                    f"{float(player[config.COL_TOTAL_POINTS]):.1f} "
                    f"({int(player[config.COL_GAMES_PLAYED])}: {match_types})"
                )
        else:
            st.write("No active players")

    # Men's Standings
    with standings_col2:
        st.header("Men's Standings")
        active_men = active_players[active_players[config.COL_GENDER] == config.GENDER_MALE]
        if not active_men.empty:
            # Sort men players by total points
            active_men = active_men.sort_values(by=config.COL_TOTAL_POINTS, ascending=False)
            
            # Display standings
            for i, (_, player) in enumerate(active_men.iterrows()):
                match_types = get_player_match_types(player[config.COL_NAME])
                trophy = "🏆 " if i == 0 else "🥈 " if i == 1 else ""
                st.write(
                    f"{i+1}. {trophy}{player[config.COL_NAME]} - "
                    f"{float(player[config.COL_TOTAL_POINTS]):.1f} "
                    f"({int(player[config.COL_GAMES_PLAYED])}: {match_types})"
                )
        else:
            st.write("No men players registered yet.")

    # Women's Standings
    with standings_col3:
        st.header("Women's Standings")
        active_women = active_players[active_players[config.COL_GENDER] == config.GENDER_FEMALE]
        if not active_women.empty:
            # Sort women players by total points
            active_women = active_women.sort_values(by=config.COL_TOTAL_POINTS, ascending=False)
            
            # Display standings
            for i, (_, player) in enumerate(active_women.iterrows()):
                match_types = get_player_match_types(player[config.COL_NAME])
                trophy = "🏆 " if i == 0 else "🥈 " if i == 1 else ""
                st.write(
                    f"{i+1}. {trophy}{player[config.COL_NAME]} - "
                    f"{float(player[config.COL_TOTAL_POINTS]):.1f} "
                    f"({int(player[config.COL_GAMES_PLAYED])}: {match_types})"
                )
        else:
            st.write("No women players registered yet.")
else:
    st.write("No players registered yet")
