import streamlit as st
from pickleball.sheets_manager import SheetsManager
from pickleball import config
import pandas as pd
import time

st.set_page_config(page_title="Match Management - Pickleball Round Robin", layout="wide")
sheets_mgr = SheetsManager()

st.title("Match Management")

# Add custom CSS and hide sidebar
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



# Get active players for match generation
players_df = sheets_mgr.read_sheet(config.SHEET_PLAYERS)
active_players = players_df[players_df[config.COL_STATUS] == config.STATUS_PLAYER_ACTIVE]

# Court Status Overview
st.header("Court Status")
courts_df = sheets_mgr.read_sheet(config.SHEET_COURTS)
matches_df = sheets_mgr.read_sheet(config.SHEET_MATCHES)

if not courts_df.empty:
    court_cols = st.columns(len(courts_df))
    for i, (court_col, (_, court)) in enumerate(zip(court_cols, courts_df.iterrows())):
        with court_col:
            st.subheader(f"{court[config.COL_COURT_NUMBER]}")
            
            # Get current match for this court
            court_matches = matches_df[
                (matches_df[config.COL_COURT_NUMBER] == court[config.COL_COURT_NUMBER]) &
                (matches_df[config.COL_MATCH_STATUS].isin([config.STATUS_SCHEDULED, config.STATUS_IN_PROGRESS]))
            ]
            
            current_match = None
            if len(court_matches) > 0:
                current_match = court_matches.iloc[0]
            
            if current_match is not None:
                #st.write("**Current Match:**")
                st.write(f"T1: {current_match[config.COL_TEAM1_PLAYER1]}, {current_match[config.COL_TEAM1_PLAYER2]}")
                st.write(f"T2: {current_match[config.COL_TEAM2_PLAYER1]}, {current_match[config.COL_TEAM2_PLAYER2]}")
                
                # Cancel button above score fields
                if st.button("Cancel Match", key=f"cancel_current_{current_match[config.COL_MATCH_ID]}"):
                    success, message = sheets_mgr.cancel_match(current_match[config.COL_MATCH_ID])
                    if success:
                        st.success(message)
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(message)
                
                # Score submission form for current match
                form_key = f"submit_score_{i}_{current_match[config.COL_MATCH_ID]}"
                with st.form(form_key):
                    score_col1, score_col2 = st.columns(2)
                    with score_col1:
                        team1_score = st.number_input("Team 1 Score", min_value=0, max_value=15, value=0, key=f"team1_score_{form_key}")
                    with score_col2:
                        team2_score = st.number_input("Team 2 Score", min_value=0, max_value=15, value=0, key=f"team2_score_{form_key}")
                    
                    # Submit button inside the form
                    submitted = st.form_submit_button("Submit Score")
                    if submitted:
                        if team1_score == team2_score:
                            st.error("Scores cannot be equal")
                        else:
                            # Update scores
                            if sheets_mgr.update_match_score(current_match[config.COL_MATCH_ID], team1_score, team2_score):
                                st.success("Scores submitted successfully!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("Failed to update match scores")
            else:
                st.write("No active match")

# Match Generation
st.header("Generate Matches")

# Get active players
active_players = players_df[players_df[config.COL_STATUS] == config.STATUS_PLAYER_ACTIVE][config.COL_NAME].tolist()
if len(active_players) < 4:
    st.error("Not enough active players to generate matches. Need at least 4 players.")
else:
    # Get number of courts
    court_count = len(courts_df) if not courts_df.empty else 0
    if court_count == 0:
        st.error("No courts available")
    else:
        # Count existing pending matches
        pending_match_count = len(matches_df[matches_df[config.COL_MATCH_STATUS] == config.STATUS_PENDING])
        max_pending_matches = int(court_count * 1.5)
        
        if pending_match_count >= max_pending_matches:
            st.warning(f"Cannot generate new matches. Already have {pending_match_count} pending matches.")
        else:
            if st.button("Generate Matches"):
                # Calculate how many new matches we can generate
                available_slots = max_pending_matches - pending_match_count
                
                # Generate matches
                new_matches = sheets_mgr.generate_next_matches(active_players, min(court_count, available_slots))
                if new_matches:
                    st.success(f"Generated {len(new_matches)} new matches!")
                    st.rerun()
                else:
                    st.error("Failed to generate matches")

# Display pending matches
st.header("Pending Matches")
st.write("**Awaiting court assignment**")

pending_matches = matches_df[matches_df[config.COL_MATCH_STATUS] == config.STATUS_PENDING].head(10)
if not pending_matches.empty:
    for idx, match in pending_matches.iterrows():
        match_col, cancel_col = st.columns([4, 1])
        with match_col:
            st.write(f"T1: {match[config.COL_TEAM1_PLAYER1]} & {match[config.COL_TEAM1_PLAYER2]} vs "
                    f"T2: {match[config.COL_TEAM2_PLAYER1]} & {match[config.COL_TEAM2_PLAYER2]}")
        with cancel_col:
            if st.button("Cancel Match", key=f"cancel_pending_{match[config.COL_MATCH_ID]}_{idx}"):
                success, message = sheets_mgr.cancel_match(match[config.COL_MATCH_ID])
                if success:
                    st.success(message)
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(message)
else:
    st.write("No pending matches")
