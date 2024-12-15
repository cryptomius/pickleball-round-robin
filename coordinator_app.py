import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from sheets_manager import SheetsManager
import config
import time

st.set_page_config(page_title="Pickleball Round Robin - Coordinator View", layout="wide")

# Initialize sheets manager
sheets_mgr = SheetsManager()

def generate_next_matches(available_players_df, court_count):
    """Generate optimal matches based on player history"""
    all_matches = sheets_mgr.read_sheet(config.SHEET_MATCHES)
    player_names = available_players_df[config.COL_NAME].tolist()
    
    # Create a matrix of how many times players have played together
    play_matrix = pd.DataFrame(0, index=player_names, columns=player_names)
    
    for _, match in all_matches.iterrows():
        team1 = [match[config.COL_TEAM1_PLAYER1], match[config.COL_TEAM1_PLAYER2]]
        team2 = [match[config.COL_TEAM2_PLAYER1], match[config.COL_TEAM2_PLAYER2]]
        for p1 in team1 + team2:
            for p2 in team1 + team2:
                if p1 in player_names and p2 in player_names:
                    play_matrix.loc[p1, p2] += 1
    
    # Generate matches
    matches = []
    available_players = player_names.copy()
    
    while len(available_players) >= 4:
        # Find the player who has played the least
        player1 = min(available_players, key=lambda p: play_matrix.loc[p].sum())
        available_players.remove(player1)
        
        # Find their partner (someone they've played with least)
        potential_partners = available_players.copy()
        partner = min(potential_partners, key=lambda p: play_matrix.loc[player1, p])
        available_players.remove(partner)
        
        # Find opponents (pair who has played least with team1)
        potential_opponents = available_players.copy()
        opponent_scores = {p: play_matrix.loc[player1, p] + play_matrix.loc[partner, p] 
                         for p in potential_opponents}
        opponent1 = min(opponent_scores.items(), key=lambda x: x[1])[0]
        available_players.remove(opponent1)
        
        opponent_scores = {p: play_matrix.loc[player1, p] + play_matrix.loc[partner, p] +
                         play_matrix.loc[opponent1, p] for p in available_players}
        opponent2 = min(opponent_scores.items(), key=lambda x: x[1])[0]
        available_players.remove(opponent2)
        
        matches.append([player1, partner, opponent1, opponent2])
    
    # If we have more matches than courts, we'll queue them up
    return matches

def main():
    st.title("Lakes Entrance Pickleball Round Robin")
    st.subheader("Coordinator View")

    # Initialize sheets manager
    sheets_mgr = SheetsManager()

    # Court Status Overview
    #st.header("Court Status")
    courts_df = sheets_mgr.read_sheet(config.SHEET_COURTS)
    matches_df = sheets_mgr.read_sheet(config.SHEET_MATCHES)
    players_df = sheets_mgr.read_sheet(config.SHEET_PLAYERS)

    cols = st.columns(config.COURTS_COUNT)
    for i, col in enumerate(cols, 1):
        with col:
            court_filter = courts_df[config.COL_COURT_NUMBER] == f"Court {i}"
            court_status = config.STATUS_COURT_ACTIVE  # Default status
            if not courts_df.empty and any(court_filter):
                court_status = courts_df[court_filter][config.COL_STATUS].iloc[0]
            
            st.subheader(f"Court {i}")
            
            # Display current matches
            current_matches = matches_df[
                (matches_df[config.COL_COURT_NUMBER] == f"Court {i}") &
                (matches_df[config.COL_MATCH_STATUS].isin([config.STATUS_SCHEDULED, config.STATUS_IN_PROGRESS]))
            ]
            if not current_matches.empty:
                for j, (_, match) in enumerate(current_matches.iterrows()):
                    st.write(f"T1: {match[config.COL_TEAM1_PLAYER1]}, {match[config.COL_TEAM1_PLAYER2]}")
                    st.write(f"T2: {match[config.COL_TEAM2_PLAYER1]}, {match[config.COL_TEAM2_PLAYER2]}")
                    
                    # Score entry for in-progress matches
                    if match[config.COL_MATCH_STATUS] in [config.STATUS_SCHEDULED, config.STATUS_IN_PROGRESS]:
                        if st.button("Cancel Match", key=f"cancel_match_{match[config.COL_MATCH_ID]}_{j}"):
                            match_id = match[config.COL_MATCH_ID]
                            sheets_mgr.update_match_status(match_id, config.STATUS_CANCELLED)
                            st.success("Match cancelled successfully!")
                            time.sleep(1)
                            st.rerun()
                        
                        st.write("Enter Match Scores:")
                        with st.form(f"score_entry_form_{match[config.COL_MATCH_ID]}_{j}"):
                            col1, col2 = st.columns(2)
                            with col1:
                                team1_score = st.number_input(
                                    "Team 1 Score",
                                    min_value=0,
                                    max_value=21,
                                    value=0,
                                    key=f"team1_score_{match[config.COL_MATCH_ID]}_{j}"
                                )
                            with col2:
                                team2_score = st.number_input(
                                    "Team 2 Score",
                                    min_value=0,
                                    max_value=21,
                                    value=0,
                                    key=f"team2_score_{match[config.COL_MATCH_ID]}_{j}"
                                )
                            
                            submitted = st.form_submit_button("Submit Scores")
                            if submitted:
                                try:
                                    if team1_score == team2_score:
                                        st.error("Scores cannot be equal. There must be a winner.")
                                    else:
                                        # Update match status to completed
                                        match_id = match[config.COL_MATCH_ID]
                                        status_result = sheets_mgr.update_match_status(match_id, config.STATUS_COMPLETED)
                                        if not status_result:
                                            st.error("Failed to update match status")
                                            return
                                        
                                        # Update scores and calculate points
                                        scores_data = sheets_mgr.update_match_score(match_id, team1_score, team2_score)
                                        if not scores_data:
                                            st.error("Failed to update match scores")
                                            return
                                        
                                        # Update scores sheet
                                        scores_df = sheets_mgr.read_sheet(config.SHEET_SCORES)
                                        scores_df = pd.concat([scores_df, pd.DataFrame(scores_data, columns=[config.COL_MATCH_ID, config.COL_NAME, config.COL_TOTAL_POINTS])], ignore_index=True)
                                        update_result = sheets_mgr.update_sheet(config.SHEET_SCORES, [scores_df.columns.tolist()] + scores_df.values.tolist())
                                        if not update_result:
                                            st.error("Failed to update scores sheet")
                                            return
                                        
                                        st.success("Scores submitted successfully!")
                                        time.sleep(1)  # Give user time to see the success message
                                        st.rerun()
                                        
                                except Exception as e:
                                    st.error(f"An error occurred: {str(e)}")
                
                # Remove the refresh button since we're using automatic rerun
                if st.session_state.get('show_refresh', False):
                    del st.session_state['show_refresh']
    # Generate Matches
    #st.header("Generate Matches")
    
    # Get active players
    active_players = players_df[players_df[config.COL_STATUS] == config.STATUS_ACTIVE][config.COL_NAME].tolist()
    
    if st.button("Generate More Matches"):
        if len(active_players) < 4:
            st.error("Not enough active players to generate matches. Need at least 4 players.")
            return
        
        # Get completed matches for these players
        completed_matches = matches_df[matches_df[config.COL_MATCH_STATUS] == config.STATUS_COMPLETED]
        
        # Generate new matches
        new_matches = generate_next_matches(players_df[players_df[config.COL_STATUS] == config.STATUS_ACTIVE], len(sheets_mgr.get_available_courts()))
        
        if new_matches:
            # Get available courts
            available_courts = sheets_mgr.get_available_courts()
            court_count = len(available_courts)
            
            # Split matches into current and queued
            current_matches = new_matches[:court_count]
            queued_matches = new_matches[court_count:]
            
            # Find the highest existing match ID
            existing_match_ids = matches_df[config.COL_MATCH_ID].str.extract(r'M(\d+)', expand=False).astype(float)
            next_match_id = 1 if existing_match_ids.empty else int(existing_match_ids.max()) + 1

            # Add current matches to matches_df
            for i, match in enumerate(current_matches):
                court_number = available_courts[config.COL_COURT_NUMBER].iloc[i]
                match_data = {
                    config.COL_MATCH_ID: f"M{next_match_id + i}",
                    config.COL_COURT_NUMBER: str(court_number),
                    config.COL_TEAM1_PLAYER1: str(match[0]),
                    config.COL_TEAM1_PLAYER2: str(match[1]),
                    config.COL_TEAM2_PLAYER1: str(match[2]),
                    config.COL_TEAM2_PLAYER2: str(match[3]),
                    config.COL_MATCH_STATUS: config.STATUS_SCHEDULED,
                    config.COL_TEAM1_SCORE: "0",
                    config.COL_TEAM2_SCORE: "0"
                }
                matches_df = pd.concat([matches_df, pd.DataFrame([match_data])], ignore_index=True)
            
            # Add queued matches to matches_df
            for i, match in enumerate(queued_matches):
                match_data = {
                    config.COL_MATCH_ID: f"M{next_match_id + len(current_matches) + i}",
                    config.COL_COURT_NUMBER: "",  # No court assigned yet
                    config.COL_TEAM1_PLAYER1: str(match[0]),
                    config.COL_TEAM1_PLAYER2: str(match[1]),
                    config.COL_TEAM2_PLAYER1: str(match[2]),
                    config.COL_TEAM2_PLAYER2: str(match[3]),
                    config.COL_MATCH_STATUS: "Queued",  # Special status for queued matches
                    config.COL_TEAM1_SCORE: "0",
                    config.COL_TEAM2_SCORE: "0"
                }
                matches_df = pd.concat([matches_df, pd.DataFrame([match_data])], ignore_index=True)
            
            # Convert all columns to string type before updating sheet
            matches_df = matches_df.astype(str)
            
            # Update the sheets
            sheets_mgr.update_sheet(config.SHEET_MATCHES, [matches_df.columns.tolist()] + matches_df.values.tolist())
            
            if queued_matches:
                st.success(f"Generated {len(current_matches)} active matches and {len(queued_matches)} queued matches!")
            else:
                st.success(f"Generated {len(current_matches)} matches!")
            st.rerun()
        else:
            st.warning("No new matches could be generated at this time.")

   
    # Player Management
    st.header("Player Management")
    
    # Add New Player
    st.subheader("Add New Player")
    col1, col2 = st.columns([2, 1])
    
    # Initialize session state for last name input if not exists
    if 'show_last_name_input' not in st.session_state:
        st.session_state.show_last_name_input = False
        st.session_state.duplicate_first_name = ""
    
    with col1:
        new_player_name = st.text_input("Player Name").strip()
        if st.session_state.show_last_name_input:
            last_name = st.text_input("Last Name (required to differentiate from existing player)").strip()
    with col2:
        if st.button("Add Player"):
            if new_player_name:
                players_df = sheets_mgr.read_sheet(config.SHEET_PLAYERS)
                # Check for duplicate names (case insensitive)
                existing_names = players_df[config.COL_NAME].str.lower().str.strip()
                if new_player_name.lower() in existing_names.values:
                    if not st.session_state.show_last_name_input:
                        st.session_state.show_last_name_input = True
                        st.session_state.duplicate_first_name = new_player_name
                        st.warning(f"Player name '{new_player_name}' already exists. Please enter a last name to differentiate.")
                        st.rerun()
                    elif 'last_name' in locals() and last_name:
                        full_name = f"{new_player_name} {last_name}"
                        if full_name.lower() in existing_names.values:
                            st.error(f"Player '{full_name}' already exists!")
                        else:
                            new_player = {
                                config.COL_NAME: full_name,
                                config.COL_STATUS: config.STATUS_ACTIVE,
                                config.COL_TOTAL_POINTS: 0,
                                config.COL_GAMES_PLAYED: 0,
                                config.COL_CHECK_IN_TIME: datetime.now().isoformat(),
                                config.COL_LAST_MATCH_TIME: ""
                            }
                            players_df = pd.concat([players_df, pd.DataFrame([new_player])], ignore_index=True)
                            sheets_mgr.update_sheet(config.SHEET_PLAYERS, [players_df.columns.tolist()] + players_df.values.tolist())
                            st.success(f"Added player: {full_name}")
                            # Reset the last name input state
                            st.session_state.show_last_name_input = False
                            st.session_state.duplicate_first_name = ""
                            st.rerun()
                else:
                    new_player = {
                        config.COL_NAME: new_player_name,
                        config.COL_STATUS: config.STATUS_ACTIVE,
                        config.COL_TOTAL_POINTS: 0,
                        config.COL_GAMES_PLAYED: 0,
                        config.COL_CHECK_IN_TIME: datetime.now().isoformat(),
                        config.COL_LAST_MATCH_TIME: ""
                    }
                    players_df = pd.concat([players_df, pd.DataFrame([new_player])], ignore_index=True)
                    sheets_mgr.update_sheet(config.SHEET_PLAYERS, [players_df.columns.tolist()] + players_df.values.tolist())
                    st.success(f"Added player: {new_player_name}")
                    st.rerun()
            else:
                st.error("Please enter a player name")
    
    # Get all players and sort by name
    players_df = sheets_mgr.read_sheet(config.SHEET_PLAYERS)
    players_df = players_df.sort_values(by=config.COL_NAME)
    
    # Display all players with status toggles
    if not players_df.empty:
        st.subheader("Players")
        for i, (_, player) in enumerate(players_df.iterrows()):
            col1, col2 = st.columns([3, 1])
            with col1:
                # Display player name with gray color if inactive
                if player[config.COL_STATUS] == config.STATUS_INACTIVE:
                    st.markdown(f'<span style="color: gray">{player[config.COL_NAME]}</span>', unsafe_allow_html=True)
                else:
                    st.write(player[config.COL_NAME])
            with col2:
                button_text = "Mark Active" if player[config.COL_STATUS] == config.STATUS_INACTIVE else "Mark Inactive"
                if st.button(button_text, key=f"toggle_status_{i}"):
                    new_status = config.STATUS_ACTIVE if player[config.COL_STATUS] == config.STATUS_INACTIVE else config.STATUS_INACTIVE
                    sheets_mgr.update_player_status(player[config.COL_NAME], new_status)
                    st.success(f"Player {player[config.COL_NAME]} marked as {new_status}")
                    st.rerun()

    # Match Management
    st.header("Match Management")
    
    # Edit completed match scores
    completed_matches = matches_df[matches_df[config.COL_MATCH_STATUS] == config.STATUS_COMPLETED]
    if not completed_matches.empty:
        st.subheader("Edit Completed Match Scores")
        selected_match = st.selectbox(
            "Select Match",
            completed_matches.apply(lambda x: f"{x[config.COL_MATCH_ID]} - {x[config.COL_TEAM1_PLAYER1]}/{x[config.COL_TEAM1_PLAYER2]} vs {x[config.COL_TEAM2_PLAYER1]}/{x[config.COL_TEAM2_PLAYER2]} ({x[config.COL_TEAM1_SCORE]}-{x[config.COL_TEAM2_SCORE]})", axis=1),
            key="edit_match_select"
        )
        
        if selected_match:
            match_id = selected_match.split(" - ")[0]
            match = completed_matches[completed_matches[config.COL_MATCH_ID] == match_id].iloc[0]
            
            col1, col2 = st.columns(2)
            with col1:
                team1_score = st.number_input(
                    f"Team 1 Score ({match[config.COL_TEAM1_PLAYER1]}/{match[config.COL_TEAM1_PLAYER2]})",
                    min_value=0,
                    max_value=21,
                    value=int(match[config.COL_TEAM1_SCORE]) if pd.notna(match[config.COL_TEAM1_SCORE]) else 0
                )
            with col2:
                team2_score = st.number_input(
                    f"Team 2 Score ({match[config.COL_TEAM2_PLAYER1]}/{match[config.COL_TEAM2_PLAYER2]})",
                    min_value=0,
                    max_value=21,
                    value=int(match[config.COL_TEAM2_SCORE]) if pd.notna(match[config.COL_TEAM2_SCORE]) else 0
                )
            
            if st.button("Update Scores"):
                if team1_score == team2_score:
                    st.error("Scores cannot be equal. There must be a winner.")
                else:
                    try:
                        # Update match scores in Matches sheet
                        matches_df.loc[matches_df[config.COL_MATCH_ID] == match_id, config.COL_TEAM1_SCORE] = team1_score
                        matches_df.loc[matches_df[config.COL_MATCH_ID] == match_id, config.COL_TEAM2_SCORE] = team2_score
                        if not sheets_mgr.update_sheet(config.SHEET_MATCHES, [matches_df.columns.tolist()] + matches_df.values.tolist()):
                            st.error("Failed to update match scores")
                            return
                        
                        # Calculate new scores and update Scores and Players sheets
                        scores_data = sheets_mgr.update_match_score(match_id, team1_score, team2_score)
                        if not scores_data:
                            st.error("Failed to update player scores")
                            return
                        
                        # Update scores sheet
                        scores_df = sheets_mgr.read_sheet(config.SHEET_SCORES)
                        scores_df = pd.concat([scores_df, pd.DataFrame(scores_data, columns=[config.COL_MATCH_ID, config.COL_NAME, config.COL_TOTAL_POINTS])], ignore_index=True)
                        update_result = sheets_mgr.update_sheet(config.SHEET_SCORES, [scores_df.columns.tolist()] + scores_df.values.tolist())
                        if not update_result:
                            st.error("Failed to update scores sheet")
                            return
                        
                        st.success("Scores updated successfully!")
                        time.sleep(1)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")
    else:
        st.write("No completed matches to edit")
    
    # Show Leaderboard
    st.header("Leaderboard")
    
    # Get scores data
    scores_df = sheets_mgr.read_sheet(config.SHEET_SCORES)
    scores_df = scores_df.sort_values(by=config.COL_TOTAL_POINTS, ascending=False)
    st.dataframe(scores_df[[config.COL_NAME, config.COL_TOTAL_POINTS]])

if __name__ == "__main__":
    main()
