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
if 'is_woman' not in st.session_state:
    st.session_state.is_woman = False
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
                    players_df.loc[players_df[config.COL_NAME] == player_name, config.COL_STATUS] = config.STATUS_INACTIVE
                    sheets_mgr.update_sheet(config.SHEET_PLAYERS, [players_df.columns.tolist()] + players_df.values.tolist())
                    
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
                    players_df.loc[players_df[config.COL_NAME] == player_name, config.COL_STATUS] = config.STATUS_INACTIVE
                    sheets_mgr.update_sheet(config.SHEET_PLAYERS, [players_df.columns.tolist()] + players_df.values.tolist())
                    
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
            players_df.loc[players_df[config.COL_NAME] == player_name, config.COL_STATUS] = config.STATUS_INACTIVE
            sheets_mgr.update_sheet(config.SHEET_PLAYERS, [players_df.columns.tolist()] + players_df.values.tolist())
            
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
    st.session_state.is_woman = False
    st.session_state.form_submitted = False
    st.rerun()

with st.form("add_player"):
    new_player = st.text_input("New Player Name", key="new_player_input")
    is_woman = st.checkbox("Woman Player", key="is_woman")
    submitted = st.form_submit_button("Add Player")
    if submitted and new_player:
        success, message = sheets_mgr.add_player(new_player, is_woman)
        if success:
            st.success(message)
            st.session_state.form_submitted = True
            st.rerun()
        else:
            st.error(message)

# Display players section with status toggles
st.header("Players")
if not players_df.empty:
    for i, (_, player) in enumerate(players_df.iterrows()):
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            status = "✅" if player[config.COL_STATUS] == config.STATUS_ACTIVE else "❌"
            gender = "♀️" if player.get(config.COL_GENDER, "") == "W" else ""
            st.write(f"{status} {player[config.COL_NAME]} {gender}")
        with col2:
            if st.button("Toggle Status", key=f"toggle_{i}"):
                new_status = config.STATUS_INACTIVE if player[config.COL_STATUS] == config.STATUS_ACTIVE else config.STATUS_ACTIVE
                
                # If marking player as inactive, handle their matches
                if new_status == config.STATUS_INACTIVE:
                    current_matches, scheduled_matches = sheets_mgr.handle_player_inactivation(player[config.COL_NAME])
                    if current_matches is not None or scheduled_matches is not None:
                        st.session_state.show_match_removal = True
                        st.session_state.player_to_deactivate = player[config.COL_NAME]
                        st.session_state.current_matches = current_matches
                        st.session_state.scheduled_matches = scheduled_matches
                        st.rerun()
                    else:
                        # No matches to handle, just update status
                        players_df.loc[players_df[config.COL_NAME] == player[config.COL_NAME], config.COL_STATUS] = new_status
                        sheets_mgr.update_sheet(config.SHEET_PLAYERS, [players_df.columns.tolist()] + players_df.values.tolist())
                        st.rerun()
                else:
                    # Just activating the player
                    players_df.loc[players_df[config.COL_NAME] == player[config.COL_NAME], config.COL_STATUS] = new_status
                    sheets_mgr.update_sheet(config.SHEET_PLAYERS, [players_df.columns.tolist()] + players_df.values.tolist())
                    st.rerun()
