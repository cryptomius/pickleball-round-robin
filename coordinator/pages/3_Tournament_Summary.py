import streamlit as st
from pickleball.sheets_manager import SheetsManager
from pickleball import config
import pandas as pd

st.set_page_config(page_title="Tournament Summary - Pickleball Round Robin", layout="wide", initial_sidebar_state="collapsed")
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

# Convert numeric columns to proper types and handle blanks
players_df[config.COL_GAMES_PLAYED] = pd.to_numeric(players_df[config.COL_GAMES_PLAYED], errors='coerce').fillna(0).astype(int)
players_df[config.COL_AVG_POINTS] = pd.to_numeric(players_df[config.COL_AVG_POINTS], errors='coerce').fillna(0.0)

all_active_players = players_df[players_df[config.COL_STATUS] == config.STATUS_PLAYER_ACTIVE]

# Function to get player's match type ratio
def get_player_match_types_ratio(player_name):
    player_matches = matches_df[
        (matches_df[config.COL_MATCH_STATUS] == config.STATUS_COMPLETED) &
        ((matches_df[config.COL_TEAM1_PLAYER1] == player_name) |
         (matches_df[config.COL_TEAM1_PLAYER2] == player_name) |
         (matches_df[config.COL_TEAM2_PLAYER1] == player_name) |
         (matches_df[config.COL_TEAM2_PLAYER2] == player_name))
    ]
    
    match_counts = {
        "Mixed": 0,
        "Mens": 0,
        "Womens": 0
    }
    
    for _, match in player_matches.iterrows():
        match_type = match[config.COL_MATCH_TYPE]
        match_counts[match_type] = match_counts.get(match_type, 0) + 1
    
    total_matches = sum(match_counts.values())
    if total_matches == 0:
        return match_counts
    
    return match_counts

# Function to get standings for a specific match type
def get_match_type_standings(players_df, matches_df, match_type, gender=None):
    # Calculate average points per match type for each player
    player_points = {}
    player_games = {}
    
    for _, player in players_df.iterrows():
        player_name = player[config.COL_NAME]
        if gender and player[config.COL_GENDER] != gender:
            continue
            
        # Get matches for this player of the specified type
        player_matches = matches_df[
            (matches_df[config.COL_MATCH_STATUS] == config.STATUS_COMPLETED) &
            (matches_df[config.COL_MATCH_TYPE] == match_type) &
            ((matches_df[config.COL_TEAM1_PLAYER1] == player_name) |
             (matches_df[config.COL_TEAM1_PLAYER2] == player_name) |
             (matches_df[config.COL_TEAM2_PLAYER1] == player_name) |
             (matches_df[config.COL_TEAM2_PLAYER2] == player_name))
        ]
        
        if len(player_matches) > 0:
            total_points = 0
            for _, match in player_matches.iterrows():
                # Determine if player was on team 1 or 2
                on_team1 = player_name in [match[config.COL_TEAM1_PLAYER1], match[config.COL_TEAM1_PLAYER2]]
                team1_score = int(match[config.COL_TEAM1_SCORE])
                team2_score = int(match[config.COL_TEAM2_SCORE])
                
                # Calculate points for this match
                if on_team1:
                    won = team1_score > team2_score
                    score_diff = abs(team1_score - team2_score)
                else:
                    won = team2_score > team1_score
                    score_diff = abs(team2_score - team1_score)
                
                points = config.POINTS_WIN if won else config.POINTS_LOSS
                bonus = min(config.MAX_BONUS_POINTS, score_diff * config.BONUS_POINT_PER_DIFF)
                total_points += points + (bonus if won else 0)
            
            player_points[player_name] = total_points
            player_games[player_name] = len(player_matches)
    
    # Create standings dataframe
    standings = []
    for player_name in player_points:
        avg_points = player_points[player_name] / player_games[player_name]
        standings.append({
            'name': player_name,
            'avg_points': avg_points,
            'games': player_games[player_name]
        })
    
    standings_df = pd.DataFrame(standings)
    if not standings_df.empty:
        standings_df = standings_df.sort_values('avg_points', ascending=False).head(10)
    
    return standings_df

# Function to get match types for a player
def get_player_match_types(player_name):
    player_matches = matches_df[
        (matches_df[config.COL_MATCH_STATUS] == config.STATUS_COMPLETED) &
        ((matches_df[config.COL_TEAM1_PLAYER1] == player_name) |
         (matches_df[config.COL_TEAM1_PLAYER2] == player_name) |
         (matches_df[config.COL_TEAM2_PLAYER1] == player_name) |
         (matches_df[config.COL_TEAM2_PLAYER2] == player_name))
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

def display_standings(players_df, title, min_games=config.MIN_GAMES_FOR_RANKING):
    """Helper function to display standings with minimum games requirement"""
    qualified_players = players_df[players_df[config.COL_GAMES_PLAYED] >= min_games]
    unqualified_players = players_df[players_df[config.COL_GAMES_PLAYED] < min_games]
    
    st.subheader(title)
    
    if not qualified_players.empty:
        st.markdown(f"**Qualified Players (≥{min_games} games)**")
        qualified_players = qualified_players.sort_values(config.COL_AVG_POINTS, ascending=False).head(10)
        for i, (_, player) in enumerate(qualified_players.iterrows()):
            match_types = get_player_match_types(player[config.COL_NAME])
            trophy = "🏆 " if i == 0 else "🥈 " if i == 1 else ""
            st.write(
                f"{i+1}. {trophy}{player[config.COL_NAME]} - "
                f"{float(player[config.COL_AVG_POINTS]):.1f} "
                f"({int(player[config.COL_GAMES_PLAYED])}: {match_types})"
            )
    else:
        st.write(f"No players with {min_games} or more games yet.")
    
    if not unqualified_players.empty:
        st.markdown(f"**Unranked Players (<{min_games} games)**")
        unqualified_players = unqualified_players.sort_values(config.COL_AVG_POINTS, ascending=False)
        for _, player in unqualified_players.iterrows():
            match_types = get_player_match_types(player[config.COL_NAME])
            st.write(
                f"• {player[config.COL_NAME]} - "
                f"{float(player[config.COL_AVG_POINTS]):.1f} "
                f"({int(player[config.COL_GAMES_PLAYED])}: {match_types})"
            )

def display_match_type_standings(standings_df, title, min_games=config.MIN_GAMES_FOR_RANKING):
    """Helper function to display match type specific standings with minimum games requirement"""
    st.subheader(title)
    
    if not standings_df.empty:
        qualified_players = standings_df[standings_df['games'] >= min_games]
        unqualified_players = standings_df[standings_df['games'] < min_games]
        
        if not qualified_players.empty:
            st.markdown(f"**Qualified Players (≥{min_games} games)**")
            qualified_players = qualified_players.reset_index(drop=True)
            for i, row in qualified_players.iterrows():
                trophy = "🏆 " if i == 0 else "🥈 " if i == 1 else ""
                st.write(
                    f"{i+1}. {trophy}{row['name']} - "
                    f"{row['avg_points']:.1f} "
                    f"({int(row['games'])})"
                )
        else:
            st.write(f"No players with {min_games} or more games in this category yet.")
            
        if not unqualified_players.empty:
            st.markdown(f"**Unranked Players (<{min_games} games)**")
            for _, row in unqualified_players.iterrows():
                st.write(
                    f"• {row['name']} - "
                    f"{row['avg_points']:.1f} "
                    f"({int(row['games'])})"
                )
    else:
        st.write("No matches played in this category yet.")

# Create two rows of three columns each
st.header("Tournament Standings")
st.markdown("**Match Types:** M = Men's Doubles, W = Women's Doubles, X = Mixed Doubles")

# First row - Overall standings
row1_col1, row1_col2, row1_col3 = st.columns(3)

with row1_col1:
    display_standings(all_active_players, "Overall Standings")

with row1_col2:
    active_men = all_active_players[all_active_players[config.COL_GENDER] == config.GENDER_MALE]
    display_standings(active_men, "Men's Standings")

with row1_col3:
    active_women = all_active_players[all_active_players[config.COL_GENDER] == config.GENDER_FEMALE]
    display_standings(active_women, "Women's Standings")

# Second row - Match type specific standings
row2_col1, row2_col2, row2_col3 = st.columns(3)

with row2_col1:
    mixed_standings = get_match_type_standings(players_df, matches_df, "Mixed")
    display_match_type_standings(mixed_standings, "Mixed Doubles Standings")

with row2_col2:
    mens_standings = get_match_type_standings(players_df, matches_df, "Mens", config.GENDER_MALE)
    display_match_type_standings(mens_standings, "Men's Doubles Standings")

with row2_col3:
    womens_standings = get_match_type_standings(players_df, matches_df, "Womens", config.GENDER_FEMALE)
    display_match_type_standings(womens_standings, "Women's Doubles Standings")
