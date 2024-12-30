import streamlit as st
from pickleball.csv_manager import CSVManager
from pickleball import config
import pandas as pd
from datetime import datetime
import numpy as np
from PIL import Image
import time
import extra_streamlit_components as stx
import traceback
import qrcode
import io

def display_qr_code():
    """Display QR code at the bottom of the page"""

    # Add explanation of scoring and matching system
    st.markdown("""
    ### How the Tournament Works
    
    #### 🎯 Scoring System
    - Win a match: 2 base points + up to 1 bonus point based on score difference
    - Lose a match: 1 base point + bonus points based on how close the game was
    - Example: In a 9-11 game
      - Winners get 2.2 points (2 base + 0.2 bonus)
      - Losers get 1.82 points (1 base + 0.82 performance bonus)
    
    #### 🤝 Player Matching
    Our smart matching system ensures:
    - Equal play time: Players with fewer games get priority
    - New partnerships: You'll play with different partners each round
    - Fresh competition: You'll face different opponents each time
    - No one sits out too long: Everyone plays a similar number of games
    
    #### 💫 Why This System?
    - Everyone earns points in every game - keeping it fun and engaging!
    - Close games are rewarded - keeping matches competitive
    - Good players shine even in losses - reflecting true skill levels
    - Mixed partnerships help you meet and play with everyone
    - Perfect for a social tournament where fun and fairness come first!
    """)
    
    st.markdown("---")  # Add a separator
    st.subheader("Let someone scan this code to view the player app")
    
    # Generate QR code for the current page URL
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data("https://pickleball-tournament.streamlit.app/")  # Get the current URL
    qr.make(fit=True)
    
    # Create the QR code image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert PIL image to bytes
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    
    # Display the QR code
    st.image(img_byte_arr)

def main():
    # Set page auto refresh interval (milliseconds)
    st.set_page_config(
        page_title="Pickleball Round Robin - Player View",
        layout="wide",
        initial_sidebar_state="collapsed",
        page_icon="🏸",
        menu_items=None
    )
    
    st.title("Lakes Entrance Pickleball Round Robin")
    #st.subheader("Player View")

    # Add custom CSS
    st.markdown("""
        <style>
        .block-container {
            padding: 1.5rem 1.4rem !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Initialize sheets manager
    sheets_mgr = CSVManager()

    # Get all players and sort by name
    players_df = sheets_mgr.read_sheet(config.SHEET_PLAYERS)
    player_names = players_df[config.COL_NAME].sort_values().tolist()

    # Get current selection from cookie and initialize session state
    cookie_manager = stx.CookieManager()
    current_cookie = cookie_manager.get(cookie="selected_player")
    
    # Initialize session state for player name if it doesn't exist or is empty
    if "player_name" not in st.session_state or not st.session_state.get("player_name"):
        if current_cookie and current_cookie in player_names:
            st.session_state.player_name = current_cookie
        else:
            st.session_state.player_name = ""
    
    # Calculate the index for the selectbox
    default_index = 0
    if st.session_state.get("player_name") and st.session_state.player_name in player_names:
        default_index = player_names.index(st.session_state.player_name) + 1
    
    # Player selection
    selected_player = st.selectbox(
        "Select Your Name",
        [""] + player_names,
        index=default_index
    )

    # Update session state and cookie when player changes
    if selected_player != st.session_state.get("player_name"):
        st.session_state.player_name = selected_player
        if selected_player:  # Only set cookie if a player is selected
            cookie_manager.set("selected_player", selected_player)

    if not selected_player:
        st.info("Please select your name to view your matches and status")
    else:
        # Display player's current status
        player_data = players_df[players_df[config.COL_NAME] == selected_player]
        if not player_data.empty:
            status = player_data[config.COL_STATUS].iloc[0]
            total_points = player_data[config.COL_TOTAL_POINTS].iloc[0]
            games_played = player_data[config.COL_GAMES_PLAYED].iloc[0]
            
            st.write(f"Status: {status}")
            
            # Handle games played display
            games_played_display = "-"
            if not pd.isna(games_played):
                try:
                    games_played_display = str(int(games_played))
                except:
                    pass
            st.write(f"Games Played: {games_played_display}")
            
            # Calculate and display average points
            avg_points_display = "-"
            if not pd.isna(total_points) and not pd.isna(games_played) and games_played > 0:
                avg_points = total_points / games_played
                avg_points_display = f"{avg_points:.4f}"
            
            st.write(f"Average Points per Game: {avg_points_display}")
            
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
                if pd.isna(court_number) or court_number == "":
                    court_display = "Court TBC"
                else:
                    court_display = f"Court {str(court_number).replace('Court ', '')}"
                st.subheader(court_display)
                
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
                st.write(f"Match Type: {match[config.COL_MATCH_TYPE]} Doubles")
                
                # Show match status
                if match[config.COL_MATCH_STATUS] == config.STATUS_SCHEDULED:
                    st.info("This match is scheduled. Please proceed to your assigned court.")
                elif match[config.COL_MATCH_STATUS] == config.STATUS_IN_PROGRESS:
                    st.info("This match is in progress. Good luck!")
                
                # Add a note about score entry
                st.info("⚠️ Note: Match scores must be entered by the tournament coordinator.")
            
            # Display upcoming matches
            upcoming_matches = matches_df[
                ((matches_df[config.COL_TEAM1_PLAYER1] == selected_player) |
                 (matches_df[config.COL_TEAM1_PLAYER2] == selected_player) |
                 (matches_df[config.COL_TEAM2_PLAYER1] == selected_player) |
                 (matches_df[config.COL_TEAM2_PLAYER2] == selected_player)) &
                (matches_df[config.COL_MATCH_STATUS] == config.STATUS_PENDING)
            ]
            
            st.write("### Up-coming Matches")
            if not upcoming_matches.empty:
                # Get all pending matches to determine queue position
                all_pending_matches = matches_df[matches_df[config.COL_MATCH_STATUS] == config.STATUS_PENDING]
                all_pending_matches = all_pending_matches.reset_index()  # Reset index to get position
                
                for _, match in upcoming_matches.iterrows():
                    # Find position in pending queue
                    match_position = all_pending_matches[all_pending_matches[config.COL_MATCH_ID] == match[config.COL_MATCH_ID]].index[0] + 1
                    
                    court_number = match[config.COL_COURT_NUMBER]
                    if pd.isna(court_number) or court_number == "":
                        court_display = "Court TBC"
                    else:
                        court_display = f"Court {str(court_number).replace('Court ', '')}"
                    
                    st.markdown(
                        f"**Queue Position: {match_position}** ({court_display}) - {match[config.COL_MATCH_TYPE]} Doubles  \n"
                        f"{match[config.COL_TEAM1_PLAYER1]} & {match[config.COL_TEAM1_PLAYER2]} vs "
                        f"{match[config.COL_TEAM2_PLAYER1]} & {match[config.COL_TEAM2_PLAYER2]}"
                    )
            else:
                st.info("Check back when a court is free for your next scheduled match")

            # Display completed matches
            completed_matches = matches_df[
                ((matches_df[config.COL_TEAM1_PLAYER1] == selected_player) |
                 (matches_df[config.COL_TEAM1_PLAYER2] == selected_player) |
                 (matches_df[config.COL_TEAM2_PLAYER1] == selected_player) |
                 (matches_df[config.COL_TEAM2_PLAYER2] == selected_player)) &
                (matches_df[config.COL_MATCH_STATUS] == config.STATUS_COMPLETED)
            ].sort_values(by=config.COL_END_TIME)  # Sort by end time to get chronological order
            
            st.write("### Completed Matches")
            if not completed_matches.empty:
                for match_num, (_, match) in enumerate(completed_matches.iterrows(), 1):
                    court_number = match[config.COL_COURT_NUMBER]
                    if pd.isna(court_number) or court_number == "":
                        court_display = "Court TBC"
                    else:
                        court_display = f"Court {int(court_number)}"
                    
                    # Determine if the player won
                    team1_score = int(match[config.COL_TEAM1_SCORE])
                    team2_score = int(match[config.COL_TEAM2_SCORE])
                    player_in_team1 = selected_player in [match[config.COL_TEAM1_PLAYER1], match[config.COL_TEAM1_PLAYER2]]
                    player_won = (player_in_team1 and team1_score > team2_score) or (not player_in_team1 and team2_score > team1_score)
                    result_emoji = "🏆" if player_won else "💪"
                    
                    st.markdown(
                        f"**Match {match_num}** ({court_display}) - {match[config.COL_MATCH_TYPE]} Doubles {result_emoji}  \n"
                        f"{match[config.COL_TEAM1_PLAYER1]} & {match[config.COL_TEAM1_PLAYER2]} vs "
                        f"{match[config.COL_TEAM2_PLAYER1]} & {match[config.COL_TEAM2_PLAYER2]}  \n"
                        f"Score: {team1_score} - {team2_score}"
                    )
            else:
                st.info("You haven't completed any matches yet")

    # Always display the QR code at the bottom
    display_qr_code()

if __name__ == "__main__":
    main()
