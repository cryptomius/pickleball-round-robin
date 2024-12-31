import streamlit as st
from pickleball.sheets_manager import SheetsManager
from pickleball import config
import pandas as pd
import time

# Force light theme
st.set_page_config(page_title="Match Management - Pickleball Round Robin", layout="wide", initial_sidebar_state="collapsed")
sheets_mgr = SheetsManager()

# Cache sheet data to avoid multiple reads
@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_sheet_data():
    players_df = sheets_mgr.read_sheet(config.SHEET_PLAYERS)
    matches_df = sheets_mgr.read_sheet(config.SHEET_MATCHES)
    return players_df, matches_df

def clear_cache():
    """Clear all Streamlit cached data"""
    st.cache_data.clear()

# Get cached sheet data
players_df, matches_df = get_sheet_data()

st.title("Match Management")

# Add custom CSS
st.markdown("""
    <style>
    .block-container {
        padding: 1.5rem 1.4rem !important;
    }
    .appview-container section:first-child {
        width: 250px !important;
    }
    /* Hide clear value button in number inputs */
    button[data-testid="clear-number-input"] {
        display: none !important;
    }
    /* Pending matches table styling */
    .matches-table {
        width: 100%;
        margin-bottom: 1rem;
    }
    .matches-header {
        background-color: #e6e6e6;
        padding: 0.5rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
        display: flex;
    }
    .matches-row {
        padding: 0.5rem;
        display: flex;
        align-items: center;
        background-color: #e7ffe8;
    }
    .matches-row.conflict {
        background-color: #ffe8e8;
    }
    .order-num {
        flex: 0.5;
    }
    .match-type {
        flex: 1;
    }
    .team1 {
        flex: 2;
    }
    .team2 {
        flex: 2;
    }
    .actions {
        flex: 1;
        text-align: center;
    }
    div:has(.matches-row) + div {
        margin-top: -40px;
    }
    a[href="https://streamlit.io/cloud"],
    #root header:first-child {
        display: none;
    }
    </style>
""", unsafe_allow_html=True)

# Get active players for match generation
active_players = players_df[players_df[config.COL_STATUS] == config.STATUS_PLAYER_ACTIVE]

# Get all blocking players from pending matches
blocking_players = set()
pending_matches = matches_df[matches_df[config.COL_MATCH_STATUS] == config.STATUS_PENDING].head(10)
scheduled_matches = matches_df[
    matches_df[config.COL_MATCH_STATUS].isin([config.STATUS_SCHEDULED, config.STATUS_IN_PROGRESS])
]

if not pending_matches.empty and not scheduled_matches.empty:
    for _, match in pending_matches.iterrows():
        # Check if any players in this match are in scheduled matches
        match_players = [
            match[config.COL_TEAM1_PLAYER1], match[config.COL_TEAM1_PLAYER2],
            match[config.COL_TEAM2_PLAYER1], match[config.COL_TEAM2_PLAYER2]
        ]
        has_conflict = False
        for player in match_players:
            if player in scheduled_matches[config.COL_TEAM1_PLAYER1].values or \
               player in scheduled_matches[config.COL_TEAM1_PLAYER2].values or \
               player in scheduled_matches[config.COL_TEAM2_PLAYER1].values or \
               player in scheduled_matches[config.COL_TEAM2_PLAYER2].values:
                blocking_players.add(player)
                has_conflict = True
        
        # If we find a match without conflicts, stop collecting blocking players
        if not has_conflict:
            break

# Court Status Overview
st.header("Court Status")
active_courts = matches_df[
    matches_df[config.COL_MATCH_STATUS].isin([config.STATUS_SCHEDULED, config.STATUS_IN_PROGRESS])
][config.COL_COURT_NUMBER].unique()

# Initialize court count
court_count = len(active_courts) if len(active_courts) > 0 else config.COURTS_COUNT

if len(active_courts) > 0:
    court_cols = st.columns(len(active_courts))
    for i, court_number in enumerate(sorted(active_courts)):
        with court_cols[i]:
            st.subheader(f"Court {court_number}")
            
            # Get current match for this court
            court_matches = matches_df[
                (matches_df[config.COL_COURT_NUMBER] == court_number) &
                (matches_df[config.COL_MATCH_STATUS].isin([config.STATUS_SCHEDULED, config.STATUS_IN_PROGRESS]))
            ]
            
            current_match = None
            if len(court_matches) > 0:
                current_match = court_matches.iloc[0]
            
            if current_match is not None:
                st.write(f"**{current_match[config.COL_MATCH_TYPE]}**")
                
                # Format player names with bold if they're blocking a pending match
                def format_court_player(name):
                    return f"**{name}**" if name in blocking_players else name
                
                team1_p1 = format_court_player(current_match[config.COL_TEAM1_PLAYER1])
                team1_p2 = format_court_player(current_match[config.COL_TEAM1_PLAYER2])
                team2_p1 = format_court_player(current_match[config.COL_TEAM2_PLAYER1])
                team2_p2 = format_court_player(current_match[config.COL_TEAM2_PLAYER2])
                
                st.write(f"T1: {team1_p1}, {team1_p2}")
                st.write(f"T2: {team2_p1}, {team2_p2}")
                
                # Cancel button above score fields
                if st.button("Cancel Match", key=f"cancel_current_{current_match[config.COL_MATCH_ID]}"):
                    success, message = sheets_mgr.cancel_match(current_match[config.COL_MATCH_ID])
                    if success:
                        clear_cache()  # Clear cache after write
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
                        team1_score = st.number_input("Team 1 Score", min_value=0, max_value=15, value=None, placeholder="", key=f"team1_score_{form_key}")
                    with score_col2:
                        team2_score = st.number_input("Team 2 Score", min_value=0, max_value=15, value=None, placeholder="", key=f"team2_score_{form_key}")
                    
                    # Submit button inside the form
                    submitted = st.form_submit_button("Submit Score")
                    if submitted:
                        if team1_score is None or team2_score is None:
                            st.error("Please enter scores for both teams")
                        elif team1_score == team2_score:
                            st.error("Scores cannot be equal")
                        elif max(team1_score, team2_score) < 11:
                            st.error("At least one team must reach 11 points")
                        elif abs(team1_score - team2_score) < 2:
                            st.error("Winning team must win by at least 2 points")
                        else:
                            # Update scores
                            if sheets_mgr.update_match_score(current_match[config.COL_MATCH_ID], team1_score, team2_score):
                                clear_cache()  # Clear cache after write
                                sheets_mgr.check_and_assign_courts()
                                st.success("Score updated successfully!")
                                st.experimental_rerun()
                            else:
                                st.error("Failed to update match scores")
            else:
                st.write("No active match")
else:
    # Default to COURTS_COUNT courts if no active matches
    st.info("No active matches on courts")

# Display pending matches
st.header("Pending Matches")
st.write("**Awaiting court assignment**")

pending_matches = matches_df[matches_df[config.COL_MATCH_STATUS] == config.STATUS_PENDING].head(10)
if not pending_matches.empty:
    # Get all currently scheduled matches to check for conflicts
    scheduled_matches = matches_df[
        matches_df[config.COL_MATCH_STATUS].isin([config.STATUS_SCHEDULED, config.STATUS_IN_PROGRESS])
    ]
    
    # Create header
    st.markdown(
        '<div class="matches-header">'
        '<div class="order-num">#</div>'
        '<div class="match-type">Match Type</div>'
        '<div class="team1">Team 1</div>'
        '<div class="team2">Team 2</div>'
        '<div class="actions">Actions</div>'
        '</div>',
        unsafe_allow_html=True
    )
    
    # Display matches
    for order_num, (idx, match) in enumerate(pending_matches.iterrows(), 1):
        # Check if any players in this match are in scheduled matches
        match_players = [
            match[config.COL_TEAM1_PLAYER1], match[config.COL_TEAM1_PLAYER2],
            match[config.COL_TEAM2_PLAYER1], match[config.COL_TEAM2_PLAYER2]
        ]
        player_conflicts = set()
        has_conflict = False
        if not scheduled_matches.empty:
            for player in match_players:
                if player in scheduled_matches[config.COL_TEAM1_PLAYER1].values or \
                   player in scheduled_matches[config.COL_TEAM1_PLAYER2].values or \
                   player in scheduled_matches[config.COL_TEAM2_PLAYER1].values or \
                   player in scheduled_matches[config.COL_TEAM2_PLAYER2].values:
                    player_conflicts.add(player)
                    has_conflict = True
        
        # Format player names with bold for conflicts
        def format_player_name(name):
            return f"<strong>{name}</strong>" if name in player_conflicts else name
        
        team1_p1 = format_player_name(match[config.COL_TEAM1_PLAYER1])
        team1_p2 = format_player_name(match[config.COL_TEAM1_PLAYER2])
        team2_p1 = format_player_name(match[config.COL_TEAM2_PLAYER1])
        team2_p2 = format_player_name(match[config.COL_TEAM2_PLAYER2])
        
        team1 = f"{team1_p1} & {team1_p2}"
        team2 = f"{team2_p1} & {team2_p2}"
        
        conflict_class = " conflict" if has_conflict else ""
        st.markdown(
            f'<div class="matches-row{conflict_class}">'
            f'<div class="order-num">{order_num}</div>'
            f'<div class="match-type">{match[config.COL_MATCH_TYPE]}</div>'
            f'<div class="team1">{team1}</div>'
            f'<div class="team2">{team2}</div>'
            f'<div class="actions"></div>'
            f'</div>',
            unsafe_allow_html=True
        )
        # Place the button in the actions column
        order_col, col1, col2, col3, button_col = st.columns([0.5, 1, 2, 2, 1])
        with button_col:
            if st.button("Cancel Match", key=f"cancel_pending_{match[config.COL_MATCH_ID]}_{idx}"):
                success, message = sheets_mgr.cancel_match(match[config.COL_MATCH_ID])
                if success:
                    clear_cache()  # Clear cache after write
                    st.success(message)
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(message)
else:
    st.write("No pending matches")

# Match Generation
st.header("Generate Matches")

# Get active players (use cached data)
active_players = players_df[players_df[config.COL_STATUS] == config.STATUS_PLAYER_ACTIVE][config.COL_NAME].tolist()
if len(active_players) < 4:
    st.error("Not enough active players to generate matches. Need at least 4 players.")
else:
    # Get number of courts (use cached data)
    active_courts = matches_df[
        matches_df[config.COL_MATCH_STATUS].isin([config.STATUS_SCHEDULED, config.STATUS_IN_PROGRESS])
    ][config.COL_COURT_NUMBER].unique()
    
    court_count = len(active_courts) if len(active_courts) > 0 else config.COURTS_COUNT
    
    if court_count == 0:
        st.error("No courts available")
    else:
        # Count existing pending matches (use cached data)
        pending_match_count = len(matches_df[matches_df[config.COL_MATCH_STATUS] == config.STATUS_PENDING])
        max_pending_matches = int(court_count * 1.5)
        
        if pending_match_count >= max_pending_matches:
            st.warning(f"Cannot generate new matches. Already have {pending_match_count} pending matches.")
        else:
            if st.button("Generate Matches"):
                # Calculate how many new matches we can generate
                available_slots = max_pending_matches - pending_match_count
                
                # Generate matches
                with st.spinner("Generating matches..."):
                    success = sheets_mgr.generate_next_matches(active_players, min(court_count, available_slots))
                    if success:
                        clear_cache()  # Clear cache after write
                        st.success("Successfully generated new matches!")
                        time.sleep(1)  # Give time for sheet updates to propagate
                        st.rerun()
                    else:
                        st.error("Failed to generate matches. Try again or check if all players have already played together.")
                
                # Get list of available courts (1-COURTS_COUNT if no active matches)
                available_courts = []
                for i in range(1, config.COURTS_COUNT + 1):  # Courts 1-COURTS_COUNT
                    if str(i) not in active_courts:
                        available_courts.append(i)
                
                # Assign courts to new matches if courts are available
                if available_courts:
                    sheets_mgr.assign_pending_matches_to_courts(available_courts)
