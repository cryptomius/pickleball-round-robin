import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
import pandas as pd
import numpy as np
from datetime import datetime
from . import config
import random
import os
import json

class SheetsManager:
    def __init__(self):
        try:
            # Try to get credentials from Streamlit secrets first
            if 'google_credentials_type' in st.secrets:
                # Reconstruct credentials dict from flattened secrets
                creds_info = {
                    'type': st.secrets['google_credentials_type'],
                    'project_id': st.secrets['google_credentials_project_id'],
                    'private_key_id': st.secrets['google_credentials_private_key_id'],
                    'private_key': st.secrets['google_credentials_private_key'],
                    'client_email': st.secrets['google_credentials_client_email'],
                    'client_id': st.secrets['google_credentials_client_id'],
                    'auth_uri': st.secrets['google_credentials_auth_uri'],
                    'token_uri': st.secrets['google_credentials_token_uri'],
                    'auth_provider_x509_cert_url': st.secrets['google_credentials_auth_provider_x509_cert_url'],
                    'client_x509_cert_url': st.secrets['google_credentials_client_x509_cert_url'],
                    'universe_domain': st.secrets['google_credentials_universe_domain']
                }
                self.creds = service_account.Credentials.from_service_account_info(
                    creds_info, scopes=config.SCOPES
                )
            else:
                # Fall back to environment variable
                creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
                if creds_json:
                    creds_info = json.loads(creds_json)
                    self.creds = service_account.Credentials.from_service_account_info(
                        creds_info, scopes=config.SCOPES
                    )
                else:
                    raise Exception("No credentials found in Streamlit secrets or environment variables")
            
            self.service = build('sheets', 'v4', credentials=self.creds)
            self.sheet = self.service.spreadsheets()
            self._last_modified = {}  # Track last modified time for each sheet
        except Exception as e:
            st.write(f"Error initializing SheetsManager: {str(e)}")
            raise

    def get_sheet_modified_time(self, sheet_name):
        """Get the last modified time of a sheet"""
        result = self.sheet.values().get(
            spreadsheetId=config.SPREADSHEET_ID,
            range=sheet_name
        ).execute()
        # Use the values themselves as a proxy for changes
        return str(result.get('values', []))

    def has_sheet_changed(self, sheet_name):
        """Check if a sheet has changed since last check"""
        current_state = self.get_sheet_modified_time(sheet_name)
        last_state = self._last_modified.get(sheet_name)
        self._last_modified[sheet_name] = current_state
        return last_state is None or current_state != last_state

    def read_sheet(self, range_name):
        """Read a sheet and return as DataFrame with proper column names."""
        try:
            result = self.sheet.values().get(
                spreadsheetId=config.SPREADSHEET_ID,
                range=range_name
            ).execute()
            values = result.get('values', [])
            
            if not values:
                # Return empty DataFrame with correct columns
                if range_name == config.SHEET_PLAYERS:
                    return pd.DataFrame(columns=[
                        config.COL_NAME,
                        config.COL_STATUS,
                        config.COL_GENDER,
                        config.COL_TOTAL_POINTS,
                        config.COL_GAMES_PLAYED,
                        config.COL_CHECK_IN_TIME,
                        config.COL_LAST_MATCH_TIME,
                        config.COL_AVG_POINTS
                    ])
                elif range_name == config.SHEET_MATCHES:
                    return pd.DataFrame(columns=[
                        config.COL_MATCH_ID,
                        config.COL_COURT_NUMBER,
                        config.COL_TEAM1_PLAYER1,
                        config.COL_TEAM1_PLAYER2,
                        config.COL_TEAM2_PLAYER1,
                        config.COL_TEAM2_PLAYER2,
                        config.COL_START_TIME,
                        config.COL_END_TIME,
                        config.COL_TEAM1_SCORE,
                        config.COL_TEAM2_SCORE,
                        config.COL_MATCH_STATUS,
                        config.COL_MATCH_TYPE
                    ])
                elif range_name == config.SHEET_SCORES:
                    return pd.DataFrame(columns=[config.COL_MATCH_ID, config.COL_NAME, config.COL_TOTAL_POINTS])
                else:
                    return pd.DataFrame()

            # Get the header row and data
            header = values[0]
            data = values[1:]

            # Create DataFrame with actual headers
            df = pd.DataFrame(data)
            
            # Get expected headers for this sheet
            expected_header = None
            if range_name == config.SHEET_PLAYERS:
                expected_header = [
                    config.COL_NAME,
                    config.COL_STATUS,
                    config.COL_GENDER,
                    config.COL_TOTAL_POINTS,
                    config.COL_GAMES_PLAYED,
                    config.COL_CHECK_IN_TIME,
                    config.COL_LAST_MATCH_TIME,
                    config.COL_AVG_POINTS
                ]
            elif range_name == config.SHEET_MATCHES:
                expected_header = [
                    config.COL_MATCH_ID,
                    config.COL_COURT_NUMBER,
                    config.COL_TEAM1_PLAYER1,
                    config.COL_TEAM1_PLAYER2,
                    config.COL_TEAM2_PLAYER1,
                    config.COL_TEAM2_PLAYER2,
                    config.COL_START_TIME,
                    config.COL_END_TIME,
                    config.COL_TEAM1_SCORE,
                    config.COL_TEAM2_SCORE,
                    config.COL_MATCH_STATUS,
                    config.COL_MATCH_TYPE
                ]
            elif range_name == config.SHEET_SCORES:
                expected_header = [config.COL_MATCH_ID, config.COL_NAME, config.COL_TOTAL_POINTS]

            if expected_header:
                # Map actual column positions to expected columns
                column_mapping = {}
                for i, col in enumerate(header):
                    if col in expected_header:
                        column_mapping[i] = expected_header.index(col)
                
                # Reorder and pad columns as needed
                reordered_data = []
                for row in data:
                    new_row = [''] * len(expected_header)
                    for i, val in enumerate(row):
                        if i in column_mapping:
                            new_pos = column_mapping[i]
                            new_row[new_pos] = val
                    reordered_data.append(new_row)
                
                # Create new DataFrame with expected headers and reordered data
                df = pd.DataFrame(reordered_data, columns=expected_header)
            
            return df

        except Exception as e:
            st.write(f"Error reading sheet: {str(e)}")
            return pd.DataFrame()

    def update_sheet(self, range_name, values):
        """Update a sheet with new values, clearing any existing data first."""
        try:
            # Get expected headers for this sheet
            expected_header = None
            if range_name == config.SHEET_PLAYERS:
                expected_header = [
                    config.COL_NAME,
                    config.COL_STATUS,
                    config.COL_GENDER,
                    config.COL_TOTAL_POINTS,
                    config.COL_GAMES_PLAYED,
                    config.COL_CHECK_IN_TIME,
                    config.COL_LAST_MATCH_TIME,
                    config.COL_AVG_POINTS
                ]
            elif range_name == config.SHEET_MATCHES:
                expected_header = [
                    config.COL_MATCH_ID,
                    config.COL_COURT_NUMBER,
                    config.COL_TEAM1_PLAYER1,
                    config.COL_TEAM1_PLAYER2,
                    config.COL_TEAM2_PLAYER1,
                    config.COL_TEAM2_PLAYER2,
                    config.COL_START_TIME,
                    config.COL_END_TIME,
                    config.COL_TEAM1_SCORE,
                    config.COL_TEAM2_SCORE,
                    config.COL_MATCH_STATUS,
                    config.COL_MATCH_TYPE
                ]
            elif range_name == config.SHEET_SCORES:
                expected_header = [config.COL_MATCH_ID, config.COL_NAME, config.COL_TOTAL_POINTS]

            # Clear the existing content except the header row
            self.sheet.values().clear(
                spreadsheetId=config.SPREADSHEET_ID,
                range=f"{range_name}!A2:ZZ",  # Start from row 2 to preserve header
                body={}
            ).execute()

            # Update with new values, starting from row 2
            values_to_write = values[1:]  # Skip the header row since we're preserving it
            self.sheet.values().update(
                spreadsheetId=config.SPREADSHEET_ID,
                range=f"{range_name}!A2",  # Start from row 2
                valueInputOption='RAW',
                body={'values': values_to_write}
            ).execute()

            return True

        except Exception as e:
            st.write(f"Error updating sheet: {str(e)}")
            return False

    def update_match_status(self, match_id, new_status):
        try:
            matches_df = self.read_sheet(config.SHEET_MATCHES)
            match_index = matches_df[matches_df[config.COL_MATCH_ID] == match_id].index[0]
            match = matches_df.iloc[match_index]
            
            matches_df.at[match_index, config.COL_MATCH_STATUS] = new_status
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if new_status == config.STATUS_IN_PROGRESS:
                matches_df.at[match_index, config.COL_START_TIME] = current_time
            elif new_status == config.STATUS_COMPLETED:
                matches_df.at[match_index, config.COL_END_TIME] = current_time
                
                # Get the court number before updating
                completed_court = match[config.COL_COURT_NUMBER]
                
                # Find the next queued match and assign it to this court
                queued_matches = matches_df[matches_df[config.COL_MATCH_STATUS] == "Queued"]
                if not queued_matches.empty:
                    next_match_index = queued_matches.index[0]
                    matches_df.at[next_match_index, config.COL_COURT_NUMBER] = completed_court
                    matches_df.at[next_match_index, config.COL_MATCH_STATUS] = config.STATUS_SCHEDULED
            
            result = self.update_sheet(config.SHEET_MATCHES, [matches_df.columns.tolist()] + matches_df.values.tolist())
            return result
        except Exception as e:
            st.write(f"Error updating match status: {str(e)}")
            return False

    def update_match_score(self, match_id, team1_score, team2_score):
        """Update match score and handle all related updates."""
        try:
            # Get matches DataFrame
            matches_df = self.read_sheet(config.SHEET_MATCHES)
            
            # Find the match
            match_idx = matches_df[matches_df[config.COL_MATCH_ID] == match_id].index[0]
            match = matches_df.iloc[match_idx]
            
            # Update match scores and status
            matches_df.at[match_idx, config.COL_TEAM1_SCORE] = team1_score
            matches_df.at[match_idx, config.COL_TEAM2_SCORE] = team2_score
            matches_df.at[match_idx, config.COL_MATCH_STATUS] = config.STATUS_COMPLETED
            
            # Calculate points
            point_diff = abs(team1_score - team2_score)
            team1_won = team1_score > team2_score
            
            # Base points
            team1_base = 2 if team1_won else 1
            team2_base = 2 if not team1_won else 1
            
            # Performance bonus
            if team1_won:
                team1_bonus = min(1.0, point_diff * 0.1)  # Winner's bonus (unchanged)
                team2_bonus = (team2_score / team1_score)  # Loser's performance ratio (no 0.1 multiplier)
            else:
                team2_bonus = min(1.0, point_diff * 0.1)  # Winner's bonus (unchanged)
                team1_bonus = (team1_score / team2_score)  # Loser's performance ratio (no 0.1 multiplier)
            
            # Total points for each team
            team1_points = team1_base + team1_bonus
            team2_points = team2_base + team2_bonus
            
            # Get players DataFrame
            players_df = self.read_sheet(config.SHEET_PLAYERS)
            
            # Update points and games played for each player
            for player in [match[config.COL_TEAM1_PLAYER1], match[config.COL_TEAM1_PLAYER2]]:
                if pd.notna(player):
                    player_idx = players_df[players_df[config.COL_NAME] == player].index[0]
                    players_df.at[player_idx, config.COL_TOTAL_POINTS] += team1_points
                    players_df.at[player_idx, config.COL_GAMES_PLAYED] += 1
                    # Update average points
                    total_points = players_df.at[player_idx, config.COL_TOTAL_POINTS]
                    games_played = players_df.at[player_idx, config.COL_GAMES_PLAYED]
                    players_df.at[player_idx, config.COL_AVG_POINTS] = total_points / games_played if games_played > 0 else 0
            
            for player in [match[config.COL_TEAM2_PLAYER1], match[config.COL_TEAM2_PLAYER2]]:
                if pd.notna(player):
                    player_idx = players_df[players_df[config.COL_NAME] == player].index[0]
                    players_df.at[player_idx, config.COL_TOTAL_POINTS] += team2_points
                    players_df.at[player_idx, config.COL_GAMES_PLAYED] += 1
                    # Update average points
                    total_points = players_df.at[player_idx, config.COL_TOTAL_POINTS]
                    games_played = players_df.at[player_idx, config.COL_GAMES_PLAYED]
                    players_df.at[player_idx, config.COL_AVG_POINTS] = total_points / games_played if games_played > 0 else 0
            
            # Update sheets
            self.update_sheet(config.SHEET_MATCHES, [matches_df.columns.tolist()] + matches_df.values.tolist())
            self.update_sheet(config.SHEET_PLAYERS, [players_df.columns.tolist()] + players_df.values.tolist())
            
            return True
            
        except Exception as e:
            st.error(f"Error updating match score: {str(e)}")
            return False

    def get_active_players(self):
        df = self.read_sheet(config.SHEET_PLAYERS)
        # Consider players active if their status is explicitly active or blank/empty
        return df[(df[config.COL_STATUS] == config.STATUS_PLAYER_ACTIVE) | 
                 (df[config.COL_STATUS].isna()) | 
                 (df[config.COL_STATUS] == '')]

    def get_player_history(self, player_name):
        matches_df = self.read_sheet(config.SHEET_MATCHES)
        return matches_df[
            (matches_df[config.COL_TEAM1_PLAYER1] == player_name) |
            (matches_df[config.COL_TEAM1_PLAYER2] == player_name) |
            (matches_df[config.COL_TEAM2_PLAYER1] == player_name) |
            (matches_df[config.COL_TEAM2_PLAYER2] == player_name)
        ]

    def get_leaderboard(self):
        """Get the tournament leaderboard sorted by total points."""
        players_df = self.read_sheet(config.SHEET_PLAYERS)
        scores_df = self.read_sheet(config.SHEET_SCORES)
        
        if players_df.empty:
            return pd.DataFrame(columns=[config.COL_NAME, config.COL_TOTAL_POINTS, config.COL_GAMES_PLAYED])
            
        # Group scores by player and sum their points
        if not scores_df.empty:
            player_scores = scores_df.groupby(config.COL_NAME)[config.COL_TOTAL_POINTS].sum().reset_index()
            games_played = scores_df.groupby(config.COL_NAME).size().reset_index()
            games_played.columns = [config.COL_NAME, config.COL_GAMES_PLAYED]
            
            # Merge scores with player data
            leaderboard = players_df[[config.COL_NAME]].merge(
                player_scores,
                on=config.COL_NAME,
                how='left'
            ).merge(
                games_played,
                on=config.COL_NAME,
                how='left'
            )
        else:
            # If no scores yet, create empty leaderboard with zeros
            leaderboard = players_df[[config.COL_NAME]].copy()
            leaderboard[config.COL_TOTAL_POINTS] = 0
            leaderboard[config.COL_GAMES_PLAYED] = 0
        
        # Fill NaN values with 0
        leaderboard[config.COL_TOTAL_POINTS] = leaderboard[config.COL_TOTAL_POINTS].fillna(0)
        leaderboard[config.COL_GAMES_PLAYED] = leaderboard[config.COL_GAMES_PLAYED].fillna(0)
        
        # Sort by total points (descending)
        leaderboard = leaderboard.sort_values(by=config.COL_TOTAL_POINTS, ascending=False)
        
        return leaderboard

    def update_player_status(self, player_name, status):
        """Update the status of a player."""
        if status not in [config.STATUS_PLAYER_ACTIVE, config.STATUS_PLAYER_INACTIVE]:
            raise ValueError(f"Invalid status: {status}")
        
        players_df = self.read_sheet(config.SHEET_PLAYERS)
        player_idx = players_df[players_df[config.COL_NAME] == player_name].index[0]
        players_df.at[player_idx, config.COL_STATUS] = status
        
        # Update the sheet
        self.update_sheet(config.SHEET_PLAYERS, [players_df.columns.tolist()] + players_df.values.tolist())

    def add_player(self, player_name, is_woman=False):
        """Add a new player to the Players sheet."""
        # Read current players
        players_df = self.read_sheet(config.SHEET_PLAYERS)
        
        # Check if player already exists
        if player_name in players_df[config.COL_NAME].values:
            return False
        
        # Create new player row
        new_player = {
            config.COL_NAME: player_name,
            config.COL_STATUS: config.STATUS_PLAYER_ACTIVE,
            config.COL_GENDER: config.GENDER_FEMALE if is_woman else config.GENDER_MALE,
            config.COL_TOTAL_POINTS: 0,
            config.COL_GAMES_PLAYED: 0,
            config.COL_CHECK_IN_TIME: "",
            config.COL_LAST_MATCH_TIME: "",
            config.COL_AVG_POINTS: 0
        }
        
        # Add new player to dataframe
        players_df = pd.concat([players_df, pd.DataFrame([new_player])], ignore_index=True)
        
        # Update sheet
        try:
            self.update_sheet(config.SHEET_PLAYERS, [players_df.columns.tolist()] + players_df.values.tolist())
            return True
        except Exception as e:
            st.error(f"Error adding player: {str(e)}")
            return False

    def get_match_key(self, team1_players, team2_players):
        """Create a unique key for a match that is the same regardless of player order"""
        # Sort players within each team
        team1_sorted = sorted(team1_players)
        team2_sorted = sorted(team2_players)
        # Sort teams to ensure consistent ordering
        teams_sorted = sorted([tuple(team1_sorted), tuple(team2_sorted)])
        # Create a single tuple of all players in a consistent order
        return tuple(teams_sorted[0] + teams_sorted[1])

    def calculate_match_staleness(self, match_date, current_date, matches_since):
        """Calculate how 'stale' a match is (0.0 = fresh, 1.0 = very stale)
        Takes into account both time passed and matches played since then
        """
        hours_passed = (current_date - match_date).total_seconds() / 3600
        time_staleness = min(1.0, hours_passed / 2.0)  # Full time staleness after 2 hours
        match_staleness = min(1.0, matches_since / 4.0)  # Full match staleness after 4 matches
        
        # Combine both factors, giving more weight to matches played
        return 0.3 * time_staleness + 0.7 * match_staleness

    def is_duplicate_match(self, matches_df, team1_players, team2_players):
        """Check if this match combination exists and is still fresh"""
        match_key = self.get_match_key(team1_players, team2_players)
        current_date = pd.Timestamp.now()
        
        # Get player information including gender
        players_df = self.read_sheet(config.SHEET_PLAYERS)
        
        # Sort matches by date to count matches since a particular match
        matches_df = matches_df.sort_values(config.COL_START_TIME)
        
        for idx, match in matches_df.iterrows():
            # Only check matches with all players still active
            all_players = [
                match[config.COL_TEAM1_PLAYER1], 
                match[config.COL_TEAM1_PLAYER2],
                match[config.COL_TEAM2_PLAYER1], 
                match[config.COL_TEAM2_PLAYER2]
            ]
            # Skip if any players in the match are not in current teams and not active
            if not all(p in team1_players + team2_players or self.is_player_active(p, players_df) for p in all_players if pd.notna(p)):
                continue
                
            existing_key = self.get_match_key(
                [match[config.COL_TEAM1_PLAYER1], match[config.COL_TEAM1_PLAYER2]],
                [match[config.COL_TEAM2_PLAYER1], match[config.COL_TEAM2_PLAYER2]]
            )
            
            if match_key == existing_key:
                # Count completed matches since this one
                matches_since = len(matches_df.loc[idx:][matches_df[config.COL_MATCH_STATUS] == config.STATUS_COMPLETED])
                
                # Check staleness based on time and matches played
                match_date = pd.Timestamp(match[config.COL_START_TIME])
                staleness = self.calculate_match_staleness(match_date, current_date, matches_since)
                
                # If match is still fresh, consider it a duplicate
                if staleness < 0.7:  # Allow repeats after 70% staleness
                    return True
        
        return False

    def is_player_active(self, player_name, players_df=None):
        """Check if a player is currently active"""
        if players_df is None:
            players_df = self.read_sheet(config.SHEET_PLAYERS)
        player_data = players_df[players_df[config.COL_NAME] == player_name]
        if player_data.empty:
            return False
        return player_data[config.COL_STATUS].iloc[0] == config.STATUS_PLAYER_ACTIVE

    def generate_next_matches(self, active_players, court_count):
        """Generate optimal matches based on player history."""
        # Read existing matches
        matches_df = self.read_sheet(config.SHEET_MATCHES)
        
        # Generate new matches
        new_matches = self._generate_matches(active_players, court_count, matches_df)
        
        if not new_matches:
            return False
            
        # Convert new matches to DataFrame rows
        new_rows = []
        for match in new_matches:
            new_rows.append([
                match[config.COL_MATCH_ID],
                match[config.COL_COURT_NUMBER],
                match[config.COL_TEAM1_PLAYER1],
                match[config.COL_TEAM1_PLAYER2],
                match[config.COL_TEAM2_PLAYER1],
                match[config.COL_TEAM2_PLAYER2],
                match[config.COL_START_TIME],
                match[config.COL_END_TIME],
                match[config.COL_TEAM1_SCORE],
                match[config.COL_TEAM2_SCORE],
                match[config.COL_MATCH_STATUS],
                match[config.COL_MATCH_TYPE]
            ])
            
        # Append new matches to existing ones
        all_matches = pd.concat([matches_df, pd.DataFrame(new_rows, columns=matches_df.columns)], ignore_index=True)
        
        # Update the sheet with all matches
        self.update_sheet(config.SHEET_MATCHES, [all_matches.columns.tolist()] + all_matches.values.tolist())
        
        return True

    def _generate_matches(self, active_players, court_count, matches_df):
        """Generate optimal matches based on player history"""
        matches = []
        available_players = active_players.copy()
        random.shuffle(available_players)  # Randomize initial order
        
        # Get player information including gender
        players_df = self.read_sheet(config.SHEET_PLAYERS)
        player_genders = dict(zip(players_df[config.COL_NAME], players_df[config.COL_GENDER]))
        
        # Count games played by each player
        games_played = {player: 0 for player in active_players}
        for _, match in matches_df.iterrows():
            for player in [match[config.COL_TEAM1_PLAYER1], match[config.COL_TEAM1_PLAYER2],
                         match[config.COL_TEAM2_PLAYER1], match[config.COL_TEAM2_PLAYER2]]:
                if player in games_played:
                    games_played[player] += 1
        
        # Create partnership history matrix
        partner_matrix = pd.DataFrame(0, index=active_players, columns=active_players)
        for _, match in matches_df.iterrows():
            team1 = [match[config.COL_TEAM1_PLAYER1], match[config.COL_TEAM1_PLAYER2]]
            team2 = [match[config.COL_TEAM2_PLAYER1], match[config.COL_TEAM2_PLAYER2]]
            for team in [team1, team2]:
                if team[0] in partner_matrix.index and team[1] in partner_matrix.columns:
                    partner_matrix.loc[team[0], team[1]] += 1
                    partner_matrix.loc[team[1], team[0]] += 1
        
        # Calculate maximum games any player should play
        max_allowed_games = min(len(active_players) - 1, 
                              max(games_played.values()) + 2)  # Allow up to 2 more games than current max
        
        # Calculate maximum times players should partner together
        max_partner_count = 2  # Maximum times same partnership should occur
        
        def get_match_type(team1_players, team2_players):
            """Determine the type of match based on player genders"""
            team1_genders = [player_genders.get(p) for p in team1_players]
            team2_genders = [player_genders.get(p) for p in team2_players]
            
            all_men = all(g == config.GENDER_MALE for g in team1_genders + team2_genders)
            all_women = all(g == config.GENDER_FEMALE for g in team1_genders + team2_genders)
            
            if all_men:
                return config.MATCH_TYPE_MENS
            elif all_women:
                return config.MATCH_TYPE_WOMENS
            else:
                return config.MATCH_TYPE_MIXED
        
        def is_valid_team(player1, player2, match_type=None):
            """Check if two players can form a valid team based on gender and match type"""
            gender1 = player_genders.get(player1)
            gender2 = player_genders.get(player2)
            
            if match_type == config.MATCH_TYPE_MENS:
                return gender1 == gender2 == config.GENDER_MALE
            elif match_type == config.MATCH_TYPE_WOMENS:
                return gender1 == gender2 == config.GENDER_FEMALE
            elif match_type == config.MATCH_TYPE_MIXED:
                return gender1 != gender2
            else:
                # If no specific match type, any valid combination is fine
                return True
        
        while len(available_players) >= 4 and len(matches) < court_count:
            # Find players who have played the least number of games
            min_games = min(games_played[p] for p in available_players)
            least_played = [p for p in available_players if games_played[p] == min_games]
            
            # Randomly select first player
            player1 = random.choice(least_played)
            available_players.remove(player1)
            player1_gender = player_genders.get(player1)
            
            # Find potential partners based on match type
            potential_partners = [
                p for p in available_players 
                if partner_matrix.loc[player1, p] < max_partner_count
                and games_played[p] < max_allowed_games
            ]
            
            if not potential_partners:  # If no partners under constraints, try different match type
                potential_partners = [
                    p for p in available_players 
                    if games_played[p] < max_allowed_games
                ]
            
            if not potential_partners:  # If still none, use all available but prioritize least partnered
                potential_partners = available_players.copy()
                potential_partners.sort(key=lambda p: partner_matrix.loc[player1, p])
                potential_partners = potential_partners[:len(potential_partners)//2]
            
            if not potential_partners:  # If still no partners, put player back and try again
                available_players.append(player1)
                continue
            
            # Select partner from potential partners
            partner = random.choice(potential_partners)
            available_players.remove(partner)
            
            # Find opponents
            potential_opponents = [
                p for p in available_players 
                if games_played[p] < max_allowed_games
            ]
            
            if not potential_opponents:  # If no valid opponents, put players back and try again
                available_players.extend([player1, partner])
                continue
            
            # Select first opponent
            opponent1 = random.choice(potential_opponents)
            available_players.remove(opponent1)
            
            # Find second opponent
            potential_opponents2 = [
                p for p in available_players 
                if games_played[p] < max_allowed_games
            ]
            
            if not potential_opponents2:  # If no valid second opponent, put all players back and try again
                available_players.extend([player1, partner, opponent1])
                continue
            
            # Select second opponent
            opponent2 = random.choice(potential_opponents2)
            available_players.remove(opponent2)
            
            # Determine actual match type based on selected team
            actual_match_type = get_match_type([player1, partner], [opponent1, opponent2])
            
            # Check if this would be a duplicate match
            if self.is_duplicate_match(matches_df, [player1, partner], [opponent1, opponent2]):
                # Put players back in available pool
                available_players.extend([player1, partner, opponent1, opponent2])
                continue
            
            # Get next match ID
            match_id_pattern = r'M(\d+)'
            existing_match_ids = matches_df[config.COL_MATCH_ID].str.extract(match_id_pattern, expand=False).astype(float)
            next_match_id = int(existing_match_ids.max() + 1) if not existing_match_ids.empty else 1
            
            # Check IDs in current batch
            if matches:
                batch_ids = pd.Series([m[config.COL_MATCH_ID] for m in matches]).str.extract(match_id_pattern, expand=False).astype(float)
                if not batch_ids.empty:
                    next_match_id = max(next_match_id, int(batch_ids.max() + 1))
            
            # Ensure unique match ID
            while f"M{next_match_id}" in matches_df[config.COL_MATCH_ID].values or \
                  any(m[config.COL_MATCH_ID] == f"M{next_match_id}" for m in matches):
                next_match_id += 1
            
            # Create the match
            match = {
                config.COL_MATCH_ID: f"M{next_match_id}",
                config.COL_COURT_NUMBER: "",  # Will be assigned if courts available
                config.COL_TEAM1_PLAYER1: player1,
                config.COL_TEAM1_PLAYER2: partner,
                config.COL_TEAM2_PLAYER1: opponent1,
                config.COL_TEAM2_PLAYER2: opponent2,
                config.COL_MATCH_STATUS: config.STATUS_PENDING,
                config.COL_START_TIME: "",  # Will be set when scheduled
                config.COL_END_TIME: "",
                config.COL_TEAM1_SCORE: "",
                config.COL_TEAM2_SCORE: "",
                config.COL_MATCH_TYPE: actual_match_type
            }
            
            matches.append(match)
            
            # Update games played count for next iteration
            for player in [player1, partner, opponent1, opponent2]:
                games_played[player] += 1
        
        return matches

    def cancel_match(self, match_id):
        """Cancel a match and assign next pending match if court is available."""
        try:
            # Get matches
            matches_df = self.read_sheet(config.SHEET_MATCHES)
            
            # Find the match to cancel
            match_idx = matches_df[matches_df[config.COL_MATCH_ID] == match_id].index
            if len(match_idx) == 0:
                return False, "Match not found"
            
            # Remove the match
            matches_df = matches_df.drop(match_idx)
            
            # Update the sheet
            success = self.update_sheet(config.SHEET_MATCHES, [matches_df.columns.tolist()] + matches_df.values.tolist())
            
            if success:
                # Check and assign courts after cancellation
                self.check_and_assign_courts()
                return True, "Match cancelled successfully"
            else:
                return False, "Failed to update matches sheet"
                
        except Exception as e:
            return False, f"Error cancelling match: {str(e)}"

    def handle_player_inactivation(self, player_name):
        """Handle matches when a player is marked as inactive."""
        try:
            # Get current matches
            matches_df = self.read_sheet(config.SHEET_MATCHES)
            
            # Find matches involving this player that are scheduled or in progress
            player_matches = matches_df[
                (matches_df[config.COL_MATCH_STATUS].isin([config.STATUS_SCHEDULED, config.STATUS_IN_PROGRESS])) &
                ((matches_df[config.COL_TEAM1_PLAYER1] == player_name) |
                 (matches_df[config.COL_TEAM1_PLAYER2] == player_name) |
                 (matches_df[config.COL_TEAM2_PLAYER1] == player_name) |
                 (matches_df[config.COL_TEAM2_PLAYER2] == player_name))
            ]
            
            if not player_matches.empty:
                # Get match IDs to remove
                match_ids = player_matches[config.COL_MATCH_ID].tolist()
                
                # Remove the matches
                success = self.remove_matches(match_ids)
                
                if success:
                    # Check and assign courts after removing matches
                    self.check_and_assign_courts()
                    return True, f"Removed {len(match_ids)} matches for inactive player"
                else:
                    return False, "Failed to remove matches"
            
            return True, "No active matches found for player"
            
        except Exception as e:
            return False, f"Error handling player inactivation: {str(e)}"

    def assign_pending_matches_to_courts(self, freed_courts):
        """Assign pending matches to freed up courts."""
        if not freed_courts:
            return
            
        matches_df = self.read_sheet(config.SHEET_MATCHES)
        
        # Get players who are currently in active or scheduled matches
        busy_players = set()
        for _, match in matches_df[
            matches_df[config.COL_MATCH_STATUS].isin([config.STATUS_SCHEDULED, config.STATUS_IN_PROGRESS])
        ].iterrows():
            busy_players.update([
                match[config.COL_TEAM1_PLAYER1],
                match[config.COL_TEAM1_PLAYER2],
                match[config.COL_TEAM2_PLAYER1],
                match[config.COL_TEAM2_PLAYER2]
            ])
        
        # Get pending matches (no court assigned and status is pending)
        pending_matches = matches_df[
            (matches_df[config.COL_MATCH_STATUS] == config.STATUS_PENDING)
        ].copy()
        
        if pending_matches.empty:
            return
        
        # Filter out pending matches where any player is already in a match
        valid_pending_matches = []
        for _, match in pending_matches.iterrows():
            match_players = {
                match[config.COL_TEAM1_PLAYER1],
                match[config.COL_TEAM1_PLAYER2],
                match[config.COL_TEAM2_PLAYER1],
                match[config.COL_TEAM2_PLAYER2]
            }
            # Skip if any players in the match are not in current teams and not active
            if not match_players & busy_players:  # No intersection with busy players
                valid_pending_matches.append(match)
        
        pending_matches = pd.DataFrame(valid_pending_matches)
        
        if pending_matches.empty:
            return
        
        # Sort pending matches by match ID to maintain order
        pending_matches = pending_matches.sort_values(by=config.COL_MATCH_ID)
        
        # Track which matches were updated
        updated_matches = []
        
        # Assign courts to pending matches
        for court in freed_courts:
            if pending_matches.empty:
                break
                
            # Get the first pending match
            match_idx = pending_matches.index[0]
            match_id = pending_matches.at[match_idx, config.COL_MATCH_ID]
            
            # Get players in this match
            match = pending_matches.loc[match_idx]
            match_players = {
                match[config.COL_TEAM1_PLAYER1],
                match[config.COL_TEAM1_PLAYER2],
                match[config.COL_TEAM2_PLAYER1],
                match[config.COL_TEAM2_PLAYER2]
            }
            
            # Update busy players set
            busy_players.update(match_players)
            
            # Update the match in the main dataframe
            match_mask = matches_df[config.COL_MATCH_ID] == match_id
            matches_df.loc[match_mask, config.COL_COURT_NUMBER] = court
            matches_df.loc[match_mask, config.COL_MATCH_STATUS] = config.STATUS_SCHEDULED
            
            # Track this match
            updated_matches.append(match_id)
            
            # Remove the match from pending matches
            pending_matches = pending_matches.drop(match_idx)
            
            # Filter remaining pending matches to remove any with now-busy players
            valid_pending_matches = []
            for _, m in pending_matches.iterrows():
                m_players = {
                    m[config.COL_TEAM1_PLAYER1],
                    m[config.COL_TEAM1_PLAYER2],
                    m[config.COL_TEAM2_PLAYER1],
                    m[config.COL_TEAM2_PLAYER2]
                }
                if not m_players & busy_players:  # No intersection with busy players
                    valid_pending_matches.append(m)
            pending_matches = pd.DataFrame(valid_pending_matches)
            
            if pending_matches.empty:
                break
        
        # Only update if we made changes
        if updated_matches:
            # Update the matches sheet
            self.update_sheet(config.SHEET_MATCHES, [matches_df.columns.tolist()] + matches_df.values.tolist())

    def remove_matches(self, match_ids, assign_pending=True, return_freed_courts=False):
        """Remove specified matches from the Matches sheet and optionally assign pending matches to freed courts."""
        matches_df = self.read_sheet(config.SHEET_MATCHES)
        
        # Get courts that will be freed up
        freed_courts = matches_df[
            (matches_df[config.COL_MATCH_ID].isin(match_ids)) &
            (matches_df[config.COL_COURT_NUMBER].notna()) &  # Check for non-empty and non-null
            (matches_df[config.COL_COURT_NUMBER] != "") &
            (matches_df[config.COL_MATCH_STATUS].isin([config.STATUS_SCHEDULED, config.STATUS_IN_PROGRESS]))
        ][config.COL_COURT_NUMBER].unique().tolist()  # Use unique to prevent duplicates
        
        # Remove the matches
        matches_df = matches_df[~matches_df[config.COL_MATCH_ID].isin(match_ids)]
        
        # Update the matches sheet
        self.update_sheet(config.SHEET_MATCHES, [matches_df.columns.tolist()] + matches_df.values.tolist())
        
        # Either assign pending matches or return the freed courts
        if assign_pending and freed_courts:
            self.assign_pending_matches_to_courts(freed_courts)
            return None
        elif return_freed_courts:
            return freed_courts
        return None

    def generate_replacement_matches(self, num_matches):
        """Generate new matches to replace removed ones."""
        players_df = self.read_sheet(config.SHEET_PLAYERS)
        active_players = players_df[players_df[config.COL_STATUS] == config.STATUS_ACTIVE]
        if len(active_players) >= 4:  # Need at least 4 players for a match
            self.generate_next_matches(active_players[config.COL_NAME].tolist(), num_matches)

    def migrate_gender_values(self):
        """Migrate old gender values (W) to new values (M/F)"""
        try:
            # Read current players
            players_df = self.read_sheet(config.SHEET_PLAYERS)
            
            # Update gender values
            players_df[config.COL_GENDER] = players_df[config.COL_GENDER].apply(
                lambda x: config.GENDER_FEMALE if x == "W" else (
                    config.GENDER_MALE if pd.isna(x) or x == "" else x
                )
            )
            
            # Update sheet
            self.update_sheet(config.SHEET_PLAYERS, [players_df.columns.tolist()] + players_df.values.tolist())
            return True
        except Exception as e:
            st.error(f"Error migrating gender values: {str(e)}")
            return False

    def check_and_assign_courts(self):
        """Check for available courts and assign them to pending matches."""
        # Get current matches
        matches_df = self.read_sheet(config.SHEET_MATCHES)
        
        # Find active courts (those with scheduled or in-progress matches)
        active_courts = matches_df[
            matches_df[config.COL_MATCH_STATUS].isin([config.STATUS_SCHEDULED, config.STATUS_IN_PROGRESS])
        ][config.COL_COURT_NUMBER].unique()
        
        # Get list of available courts (1-6)
        available_courts = []
        for i in range(1, 7):  # Courts 1-6
            if str(i) not in active_courts:
                available_courts.append(i)
        
        # If there are available courts, assign them to pending matches
        if available_courts:
            self.assign_pending_matches_to_courts(available_courts)
            return True
        return False
