import streamlit as st
from pickleball.sheets_manager import SheetsManager
from pickleball import config
import time

# Force light theme and configure page
st.set_page_config(
    page_title="Display Board - Pickleball Round Robin",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Add custom CSS for large display
st.markdown("""
    <style>
    /* Hide unnecessary elements */
    #MainMenu, footer, header {display: none !important;}
    .block-container {
        padding: 0rem !important;
        max-width: 100% !important;
    }
    .appview-container {
        margin: 0 12px;
    }
    /* Hide stale data */
    div[data-stale="true"] {
        display: none !important;
    }
    /* Court status styling */
    .court-header {
        background-color: #1f77b4;
        color: white;
        padding: 10px;
        font-size: 32px;
        font-weight: bold;
        margin-bottom: 20px;
        border-radius: 5px;
        text-align: center;
    }
    .court-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 10px;
        margin-bottom: 10px;
    }
    .court-number {
        font-size: 95px;
        color: #1f77b4;
        margin-bottom: 10px;
        text-align: center;
        font-weight: 600;
    }
    .court-content {
        background-color: #f0f2f6;
        padding: 15px;
        font-size: 48px;
        border-radius: 5px;
        height: 465px;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .pending-header {
        background-color: #2ca02c;
        color: white;
        padding: 10px;
        font-size: 32px;
        font-weight: bold;
        border-radius: 5px;
        text-align: center;
    }
    .pending-content {
        background-color: #e7ffe8;  /* Green background for non-conflicting matches */
        padding: 15px;
        font-size: 40px;
        border-radius: 5px;
        margin-bottom: 10px;
        position: relative;  /* For absolute positioning of queue number */
    }
    .pending-content.conflict {
        background-color: #ffe8e8;  /* Red background for conflicting matches */
    }
    .queue-number {
        position: absolute;
        top: 10px;
        right: 15px;
        font-size: 36px;
        font-weight: bold;
        color: #666;
    }
    /* Remove streamlit branding */
    .stDeployButton {display: none;}
    </style>
""", unsafe_allow_html=True)

# Initialize sheets manager
sheets_mgr = SheetsManager()

# Cache data with a 15-second TTL ...
@st.cache_data(ttl=14)  # Slightly less than refresh interval to ensure fresh data
def get_sheet_data():
    matches_df = sheets_mgr.read_sheet(config.SHEET_MATCHES)
    return matches_df

def get_ordinal(n):
    """Return ordinal string (1st, 2nd, 3rd, etc.) for a number."""
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

def display_courts(matches_df):
    # Get active courts
    active_matches = matches_df[
        matches_df[config.COL_MATCH_STATUS].isin([config.STATUS_SCHEDULED, config.STATUS_IN_PROGRESS])
    ].sort_values(by=[config.COL_COURT_NUMBER])

    if not active_matches.empty:
        st.markdown('<div class="court-header">CURRENT MATCHES</div>', unsafe_allow_html=True)
        
        # Create two rows for the 3x2 grid
        matches_list = list(active_matches.head(6).iterrows())
        
        # First row of courts (0-2)
        cols1 = st.columns(3)
        for i in range(3):
            with cols1[i]:
                if i < len(matches_list):
                    _, match = matches_list[i]
                    court_content = f"""
                    <div class="court-content">
                    <div class="court-number">Court {match[config.COL_COURT_NUMBER]}</div>
                    {match[config.COL_TEAM1_PLAYER1]} &amp; {match[config.COL_TEAM1_PLAYER2]}<br>
                    {match[config.COL_TEAM2_PLAYER1]} &amp; {match[config.COL_TEAM2_PLAYER2]}<br>
                    <strong>{match[config.COL_MATCH_TYPE]}</strong>
                    </div>
                    """
                    st.markdown(court_content, unsafe_allow_html=True)
                else:
                    st.markdown(
                        '<div class="court-content" style="text-align: center;"><br>No Active Match</div>',
                        unsafe_allow_html=True
                    )
        
        # Second row of courts (3-5)
        cols2 = st.columns(3)
        for i in range(3):
            with cols2[i]:
                idx = i + 3
                if idx < len(matches_list):
                    _, match = matches_list[idx]
                    court_content = f"""
                    <div class="court-content">
                    <div class="court-number">Court {match[config.COL_COURT_NUMBER]}</div>
                    {match[config.COL_TEAM1_PLAYER1]} &amp; {match[config.COL_TEAM1_PLAYER2]}<br>
                    {match[config.COL_TEAM2_PLAYER1]} &amp; {match[config.COL_TEAM2_PLAYER2]}<br>
                    <strong>{match[config.COL_MATCH_TYPE]}</strong>
                    </div>
                    """
                    st.markdown(court_content, unsafe_allow_html=True)
                else:
                    st.markdown(
                        '<div class="court-content" style="text-align: center;"><br>No Active Match</div>',
                        unsafe_allow_html=True
                    )
    else:
        st.markdown(
            '<div class="court-content" style="text-align: center;">No Active Matches</div>',
            unsafe_allow_html=True
        )

def display_pending(matches_df):
    # Get pending matches
    pending_matches = matches_df[
        matches_df[config.COL_MATCH_STATUS] == config.STATUS_PENDING
    ].head(4)  # Show only next 4 pending matches

    # Get list of players in scheduled matches
    scheduled_matches = matches_df[
        matches_df[config.COL_MATCH_STATUS].isin([config.STATUS_SCHEDULED, config.STATUS_IN_PROGRESS])
    ]
    players_in_scheduled = set()
    if not scheduled_matches.empty:
        for _, match in scheduled_matches.iterrows():
            players_in_scheduled.update([
                match[config.COL_TEAM1_PLAYER1], match[config.COL_TEAM1_PLAYER2],
                match[config.COL_TEAM2_PLAYER1], match[config.COL_TEAM2_PLAYER2]
            ])

    st.markdown('<div class="pending-header">NEXT UP</div>', unsafe_allow_html=True)
    
    if not pending_matches.empty:
        for idx, (_, match) in enumerate(pending_matches.iterrows(), 1):
            # Check if any players in this match are in scheduled matches
            match_players = [
                match[config.COL_TEAM1_PLAYER1], match[config.COL_TEAM1_PLAYER2],
                match[config.COL_TEAM2_PLAYER1], match[config.COL_TEAM2_PLAYER2]
            ]
            
            # Format player names - bold if they're in a scheduled match
            def format_player(name):
                return f"<strong>{name}</strong>" if name in players_in_scheduled else name
            
            has_conflict = any(player in players_in_scheduled for player in match_players)
            conflict_class = ' conflict' if has_conflict else ''
            
            team1_p1 = format_player(match[config.COL_TEAM1_PLAYER1])
            team1_p2 = format_player(match[config.COL_TEAM1_PLAYER2])
            team2_p1 = format_player(match[config.COL_TEAM2_PLAYER1])
            team2_p2 = format_player(match[config.COL_TEAM2_PLAYER2])
            
            pending_content = f"""
            <div class="pending-content{conflict_class}">
            <div class="queue-number">{get_ordinal(idx)}</div>
            <strong>{match[config.COL_MATCH_TYPE]}</strong><br>
            {team1_p1} &amp; {team1_p2}<br>
            {team2_p1} &amp; {team2_p2}
            </div>
            """
            st.markdown(pending_content, unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="pending-content" style="text-align: center;">Check back in a few mins</div>',
            unsafe_allow_html=True
        )

def main():
    # Create two columns with 75:25 ratio
    col1, col2 = st.columns([75, 25])
    
    # Get the data
    matches_df = get_sheet_data()
    
    # Display courts in left column (75%)
    with col1:
        display_courts(matches_df)
    
    # Display pending in right column (25%)
    with col2:
        display_pending(matches_df)
    
    # Rerun every 60 seconds using Streamlit's native functionality
    time.sleep(60)
    st.rerun()

if __name__ == "__main__":
    main()
