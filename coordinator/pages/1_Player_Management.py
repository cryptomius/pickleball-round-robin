import streamlit as st
from pickleball.sheets_manager import SheetsManager
from pickleball import config
import pandas as pd

st.set_page_config(page_title="Player Management - Pickleball Round Robin", layout="wide")
sheets_mgr = SheetsManager()

# Get and sort players alphabetically
players_df = sheets_mgr.read_sheet(config.SHEET_PLAYERS)
players_df = players_df.sort_values(by=config.COL_NAME)

# Initialize session states
if 'show_match_removal' not in st.session_state:
    st.session_state.show_match_removal = False
if 'player_to_deactivate' not in st.session_state:
    st.session_state.player_to_deactivate = None
if 'current_matches' not in st.session_state:
    st.session_state.current_matches = None
if 'scheduled_matches' not in st.session_state:
    st.session_state.scheduled_matches = None
if 'new_player_input' not in st.session_state:
    st.session_state.new_player_input = ""
if 'player_gender' not in st.session_state:
    st.session_state.player_gender = config.GENDER_MALE
if 'form_submitted' not in st.session_state:
    st.session_state.form_submitted = False

st.title("Player Management")

# Add custom CSS
st.markdown("""
    <style>
    .block-container {
        padding: 1.5rem 1.4rem !important;
    }
    .appview-container section:first-child {
        width: 250px !important;
    }
    .gender-icon {
        font-size: 1.2em;
        margin-left: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# Create a container for the match removal confirmation
match_removal_container = st.empty()

# Force scroll to top if showing confirmation
if st.session_state.show_match_removal:
    st.markdown(
        """
        <script>
            window.scrollTo(0, 0);
            document.body.scrollTop = 0;
            document.documentElement.scrollTop = 0;
        </script>
        """,
        unsafe_allow_html=True
    )
    with match_removal_container.container():
        st.header("⚠️ Match Removal Confirmation")
        player_name = st.session_state.player_to_deactivate
        st.write(f"Handling matches for {player_name} before deactivation:")
        
        if st.session_state.current_matches is not None and not st.session_state.current_matches.empty:
            st.warning("The following matches are currently in progress:")
            for _, match in st.session_state.current_matches.iterrows():
                st.write(f"Court {match[config.COL_COURT_NUMBER]}: "
                        f"{match[config.COL_TEAM1_PLAYER1]}/{match[config.COL_TEAM1_PLAYER2]} vs "
                        f"{match[config.COL_TEAM2_PLAYER1]}/{match[config.COL_TEAM2_PLAYER2]}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Yes, Remove These Matches"):
                    # Remove current matches and collect freed courts
                    freed_courts = sheets_mgr.remove_matches(
                        st.session_state.current_matches[config.COL_MATCH_ID].tolist(),
                        assign_pending=False,
                        return_freed_courts=True
                    ) or []
                    st.success("Current matches removed")
                    
                    # Handle scheduled matches
                    if st.session_state.scheduled_matches is not None and not st.session_state.scheduled_matches.empty:
                        num_scheduled = len(st.session_state.scheduled_matches)
                        # Remove scheduled matches and collect any additional freed courts
                        additional_courts = sheets_mgr.remove_matches(
                            st.session_state.scheduled_matches[config.COL_MATCH_ID].tolist(),
                            assign_pending=False,
                            return_freed_courts=True
                        ) or []
                        freed_courts.extend(additional_courts)
                        st.info(f"Also removed {num_scheduled} scheduled matches")
                    
                    # Now assign all freed courts to pending matches
                    if freed_courts:
                        sheets_mgr.assign_pending_matches_to_courts(freed_courts)
                    
                    # Update player status
                    if sheets_mgr.update_player_status(player_name, config.STATUS_INACTIVE):
                        # Handle any active/scheduled matches
                        success, message = sheets_mgr.handle_player_inactivation(player_name)
                        if success:
                            st.success(f"Player marked as inactive. {message}")
                            st.experimental_rerun()
                        else:
                            st.error(f"Error handling player matches: {message}")
                    
                    # Reset session state
                    st.session_state.show_match_removal = False
                    st.session_state.player_to_deactivate = None
                    st.session_state.current_matches = None
                    st.session_state.scheduled_matches = None
                    st.rerun()
            with col2:
                if st.button("No, Keep These Matches"):
                    # Handle only scheduled matches
                    if st.session_state.scheduled_matches is not None and not st.session_state.scheduled_matches.empty:
                        num_scheduled = len(st.session_state.scheduled_matches)
                        # Remove scheduled matches and collect freed courts
                        freed_courts = sheets_mgr.remove_matches(
                            st.session_state.scheduled_matches[config.COL_MATCH_ID].tolist(),
                            assign_pending=False,
                            return_freed_courts=True
                        ) or []
                        st.info(f"Removed {num_scheduled} scheduled matches")
                        
                        # Assign freed courts to pending matches
                        if freed_courts:
                            sheets_mgr.assign_pending_matches_to_courts(freed_courts)
                    
                    # Update player status
                    if sheets_mgr.update_player_status(player_name, config.STATUS_INACTIVE):
                        # Handle any active/scheduled matches
                        success, message = sheets_mgr.handle_player_inactivation(player_name)
                        if success:
                            st.success(f"Player marked as inactive. {message}")
                            st.experimental_rerun()
                        else:
                            st.error(f"Error handling player matches: {message}")
                    
                    # Reset session state
                    st.session_state.show_match_removal = False
                    st.session_state.player_to_deactivate = None
                    st.session_state.current_matches = None
                    st.session_state.scheduled_matches = None
                    st.rerun()
        else:
            # No current matches, just handle scheduled matches
            if st.session_state.scheduled_matches is not None and not st.session_state.scheduled_matches.empty:
                num_scheduled = len(st.session_state.scheduled_matches)
                # Remove scheduled matches and collect freed courts
                freed_courts = sheets_mgr.remove_matches(
                    st.session_state.scheduled_matches[config.COL_MATCH_ID].tolist(),
                    assign_pending=False,
                    return_freed_courts=True
                ) or []
                st.info(f"Removed {num_scheduled} scheduled matches")
                
                # Assign freed courts to pending matches
                if freed_courts:
                    sheets_mgr.assign_pending_matches_to_courts(freed_courts)
            
            # Update player status
            if sheets_mgr.update_player_status(player_name, config.STATUS_INACTIVE):
                # Handle any active/scheduled matches
                success, message = sheets_mgr.handle_player_inactivation(player_name)
                if success:
                    st.success(f"Player marked as inactive. {message}")
                    st.experimental_rerun()
                else:
                    st.error(f"Error handling player matches: {message}")
            
            # Reset session state
            st.session_state.show_match_removal = False
            st.session_state.player_to_deactivate = None
            st.session_state.current_matches = None
            st.session_state.scheduled_matches = None
            st.rerun()

# Add New Player
st.header("Add New Player")

if st.session_state.form_submitted:
    st.session_state.new_player_input = ""
    st.session_state.player_gender = config.GENDER_MALE

with st.form("add_player_form"):
    new_player = st.text_input("Player Name", key="new_player_input", value=st.session_state.new_player_input)
    gender = st.radio("Gender", [config.GENDER_MALE, config.GENDER_FEMALE], 
                     format_func=lambda x: "Male" if x == config.GENDER_MALE else "Female",
                     horizontal=True,
                     key="player_gender")
    
    submitted = st.form_submit_button("Add Player")
    if submitted and new_player.strip():
        if sheets_mgr.add_player(new_player.strip(), gender == config.GENDER_FEMALE):
            st.success(f"Added {new_player}")
            st.session_state.form_submitted = True
            st.rerun()
        else:
            st.error("Failed to add player")

# Display Players
st.header("Current Players")

# Create two columns for active and inactive players
col1, col2 = st.columns(2)

with col1:
    st.subheader("Active Players")
    active_players = players_df[players_df[config.COL_STATUS] == config.STATUS_ACTIVE]
    for _, player in active_players.iterrows():
        col_name, col_button = st.columns([3, 1])
        with col_name:
            gender_icon = "♀️" if player[config.COL_GENDER] == config.GENDER_FEMALE else "♂️"
            st.write(f"{player[config.COL_NAME]} {gender_icon}")
        with col_button:
            if st.button("Deactivate", key=f"deactivate_{player[config.COL_NAME]}"):
                st.session_state.player_to_deactivate = player[config.COL_NAME]
                # Get current and scheduled matches for this player
                matches_df = sheets_mgr.read_sheet(config.SHEET_MATCHES)
                current_matches = matches_df[
                    (matches_df[config.COL_MATCH_STATUS].isin([config.STATUS_SCHEDULED, config.STATUS_IN_PROGRESS])) &
                    ((matches_df[config.COL_TEAM1_PLAYER1] == player[config.COL_NAME]) |
                     (matches_df[config.COL_TEAM1_PLAYER2] == player[config.COL_NAME]) |
                     (matches_df[config.COL_TEAM2_PLAYER1] == player[config.COL_NAME]) |
                     (matches_df[config.COL_TEAM2_PLAYER2] == player[config.COL_NAME]))
                ]
                scheduled_matches = matches_df[
                    (matches_df[config.COL_MATCH_STATUS] == config.STATUS_PENDING) &
                    ((matches_df[config.COL_TEAM1_PLAYER1] == player[config.COL_NAME]) |
                     (matches_df[config.COL_TEAM1_PLAYER2] == player[config.COL_NAME]) |
                     (matches_df[config.COL_TEAM2_PLAYER1] == player[config.COL_NAME]) |
                     (matches_df[config.COL_TEAM2_PLAYER2] == player[config.COL_NAME]))
                ]
                st.session_state.current_matches = current_matches
                st.session_state.scheduled_matches = scheduled_matches
                st.session_state.show_match_removal = True
                st.rerun()

with col2:
    st.subheader("Inactive Players")
    inactive_players = players_df[players_df[config.COL_STATUS] == config.STATUS_INACTIVE]
    for _, player in inactive_players.iterrows():
        col_name, col_button = st.columns([3, 1])
        with col_name:
            gender_icon = "♀️" if player[config.COL_GENDER] == config.GENDER_FEMALE else "♂️"
            st.write(f"{player[config.COL_NAME]} {gender_icon}")
        with col_button:
            if st.button("Activate", key=f"activate_{player[config.COL_NAME]}"):
                sheets_mgr.update_player_status(player[config.COL_NAME], config.STATUS_ACTIVE)
                st.rerun()
