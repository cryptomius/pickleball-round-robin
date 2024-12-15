import streamlit as st
from pickleball.sheets_manager import SheetsManager
from pickleball import config
import pandas as pd
from datetime import datetime
import numpy as np
from PIL import Image
import time
import extra_streamlit_components as stx
import traceback

def main():
    # Set page auto refresh interval (milliseconds)
    st.set_page_config(
        page_title="Pickleball Round Robin - Player View",
        layout="wide",
        page_icon="🏸",
        menu_items=None
    )
    
    st.title("Lakes Entrance Pickleball Round Robin")
    #st.subheader("Player View")

    # Initialize sheets manager
    sheets_mgr = SheetsManager()

    # Get all players and sort by name
    players_df = sheets_mgr.read_sheet(config.SHEET_PLAYERS)
    player_names = players_df[config.COL_NAME].sort_values().tolist()

    # Get current selection from cookie
    cookie_manager = stx.CookieManager()
    current_selection = cookie_manager.get(cookie="selected_player")
    
    # Player selection
    index = (player_names.index(current_selection) + 1) if current_selection in player_names else 0
    
    selected_player = st.selectbox(
        "Select Your Name",
        [""] + player_names,
        index=index,
        key="player_select"
    )

    if not selected_player:
        st.info("Please select your name to view your matches and status")
        return

    # Display player's current status
    player_data = players_df[players_df[config.COL_NAME] == selected_player]
    if not player_data.empty:
        status = player_data[config.COL_STATUS].iloc[0]
        total_points = player_data[config.COL_TOTAL_POINTS].iloc[0]
        games_played = player_data[config.COL_GAMES_PLAYED].iloc[0]
        
        st.write(f"Status: {status}")
        st.write(f"Total Points: {total_points}")
        st.write(f"Games Played: {games_played}")
        
        # Display player's current match and score entry
        matches_df = sheets_mgr.read_sheet(config.SHEET_MATCHES)
        current_match = matches_df[
            ((matches_df[config.COL_TEAM1_PLAYER1] == selected_player) |
             (matches_df[config.COL_TEAM1_PLAYER2] == selected_player) |
             (matches_df[config.COL_TEAM2_PLAYER1] == selected_player) |
             (matches_df[config.COL_TEAM2_PLAYER2] == selected_player)) &
            (matches_df[config.COL_MATCH_STATUS].isin([config.STATUS_SCHEDULED, config.STATUS_IN_PROGRESS]))
        ]
        
        if not current_match.empty:
            match = current_match.iloc[0]
            st.header("Your Current Match")
            court_number = match[config.COL_COURT_NUMBER]
            if isinstance(court_number, str):
                court_number = court_number.replace("Court ", "")
            st.subheader(f"Court {court_number}")
            
            # Determine which team the player is on
            if selected_player in [match[config.COL_TEAM1_PLAYER1], match[config.COL_TEAM1_PLAYER2]]:
                player_team = 1
                team_label = "Your Team"
                opponent_label = "Opponent Team"
                team_players = [match[config.COL_TEAM1_PLAYER1], match[config.COL_TEAM1_PLAYER2]]
                opponent_players = [match[config.COL_TEAM2_PLAYER1], match[config.COL_TEAM2_PLAYER2]]
            else:
                player_team = 2
                team_label = "Your Team"
                opponent_label = "Opponent Team"
                team_players = [match[config.COL_TEAM2_PLAYER1], match[config.COL_TEAM2_PLAYER2]]
                opponent_players = [match[config.COL_TEAM1_PLAYER1], match[config.COL_TEAM1_PLAYER2]]
            
            st.write(f"{team_label}: {', '.join(filter(None, team_players))}")
            st.write(f"{opponent_label}: {', '.join(filter(None, opponent_players))}")
            
            if match[config.COL_MATCH_STATUS] == config.STATUS_SCHEDULED:
                st.write("Enter Match Scores:")
                with st.form(f"score_entry_form_{match[config.COL_MATCH_ID]}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        your_score = st.number_input(
                            "Your Team's Score",
                            min_value=0,
                            max_value=15,
                            value=0,
                            key=f"your_score_{match[config.COL_MATCH_ID]}"
                        )
                    with col2:
                        opponent_score = st.number_input(
                            "Opponent's Score",
                            min_value=0,
                            max_value=15,
                            value=0,
                            key=f"opponent_score_{match[config.COL_MATCH_ID]}"
                        )
                    
                    submitted = st.form_submit_button("Submit Scores")
                    if submitted:
                        try:
                            if your_score == opponent_score:
                                st.error("Scores cannot be equal. There must be a winner.")
                            else:
                                # Convert scores to team1/team2 format
                                team1_score = your_score if player_team == 1 else opponent_score
                                team2_score = opponent_score if player_team == 1 else your_score
                                
                                # Update scores using the sheets manager
                                if sheets_mgr.update_match_score(match[config.COL_MATCH_ID], team1_score, team2_score):
                                    st.success("Scores submitted successfully!")
                                    time.sleep(1)  # Give user time to see the success message
                                    st.rerun()
                                else:
                                    st.error("Failed to update match scores")
                        except Exception as e:
                            st.error(f"An error occurred: {str(e)}")
                            traceback.print_exc()  # This will help debug by showing the full error
        
        # Display match history
        st.header("Your Matches")
        player_matches = matches_df[
            (matches_df[config.COL_TEAM1_PLAYER1] == selected_player) |
            (matches_df[config.COL_TEAM1_PLAYER2] == selected_player) |
            (matches_df[config.COL_TEAM2_PLAYER1] == selected_player) |
            (matches_df[config.COL_TEAM2_PLAYER2] == selected_player)
        ]
        
        if not player_matches.empty:
            st.write("### Completed Matches")
            for _, match in player_matches.iterrows():
                team1_score = match[config.COL_TEAM1_SCORE] if pd.notna(match[config.COL_TEAM1_SCORE]) else "-"
                team2_score = match[config.COL_TEAM2_SCORE] if pd.notna(match[config.COL_TEAM2_SCORE]) else "-"
                
                # Format the match display
                st.markdown(
                    f"**{match[config.COL_MATCH_ID]}** ({match[config.COL_COURT_NUMBER]})  \n"
                    f"{match[config.COL_TEAM1_PLAYER1]} & {match[config.COL_TEAM1_PLAYER2]} vs "
                    f"{match[config.COL_TEAM2_PLAYER1]} & {match[config.COL_TEAM2_PLAYER2]}  \n"
                    f"Score: {team1_score} - {team2_score}"
                )
        else:
            st.write("No completed matches yet")

if __name__ == "__main__":
    main()