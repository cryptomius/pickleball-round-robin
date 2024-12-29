import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pandas as pd
import numpy as np
from datetime import datetime
from . import config
import random
import os
import json
import time

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
        max_retries = 3
        retry_delay = 66  # seconds
        
        for attempt in range(max_retries):
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

            except HttpError as e:
                if e.resp.status == 429:  # Quota exceeded error
                    if attempt < max_retries - 1:
                        st.warning(f"Google Sheets quota exceeded. Waiting 1 minute before retry {attempt + 1}/{max_retries}...")
                        time.sleep(retry_delay)
                        continue
                st.error(f"Error reading sheet after {max_retries} attempts: {str(e)}")
                return pd.DataFrame()
            except Exception as e:
                st.error(f"Error reading sheet: {str(e)}")
                return pd.DataFrame()

        return pd.DataFrame()

    def _verify_sheet_update(self, range_name, expected_values, max_retries=3):
        """Verify that the sheet has been updated correctly with the expected values."""
        try:
            # Calculate the range based on the data size
            if len(expected_values) > 1:  # If we have data beyond header
                values_to_verify = expected_values[1:]  # Skip header
                num_rows = len(values_to_verify)
                num_cols = len(values_to_verify[0]) if values_to_verify else len(expected_values[0])
                end_col = chr(ord('A') + num_cols - 1)
                
                # Read the current values including header
                result = self.sheet.values().get(
                    spreadsheetId=config.SPREADSHEET_ID,
                    range=f"{range_name}!A1:{end_col}{num_rows + 1}"  # +1 for header row
                ).execute()
                
                current_values = result.get('values', [])
                
                # Quick length check
                if len(current_values) != len(expected_values):
                    return False
                
                # Compare each row's contents, ignoring trailing empty cells
                for curr_row, exp_row in zip(current_values, expected_values):
                    # Trim any trailing empty cells from both rows
                    while curr_row and curr_row[-1] == '':
                        curr_row.pop()
                    while exp_row and exp_row[-1] == '':
                        exp_row.pop()
                        
                    if curr_row != exp_row:
                        return False
                
                return True
            
            return True  # If no data to verify
            
        except Exception as e:
            st.write(f"Error verifying sheet update: {str(e)}")
            return False

    def update_sheet(self, range_name, values):
        """Update a sheet with new values. Updates in-place without clearing first."""
        if not values:
            st.write(f"Warning: Attempted to update {range_name} with empty values")
            return False

        max_retries = 3
        # Progressive retry delays: 1s, 3s, 6s
        retry_delays = [1, 3, 6]

        for attempt in range(max_retries):
            try:
                # Get the expected header based on the sheet
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

                # Prepare the update data
                if len(values) > 1:
                    values_to_write = values[1:]  # Skip the header row
                    num_rows = len(values_to_write)
                    num_cols = len(values_to_write[0]) if values_to_write else len(expected_header)
                    end_col = chr(ord('A') + num_cols - 1)
                    
                    # Create batch update request
                    batch_update = {
                        'valueInputOption': 'RAW',
                        'data': [
                            {
                                'range': f"{range_name}!A1",
                                'values': [expected_header]
                            },
                            {
                                'range': f"{range_name}!A2:{end_col}{num_rows + 1}",
                                'values': values_to_write
                            }
                        ]
                    }
                    
                    # Execute batch update
                    self.sheet.values().batchUpdate(
                        spreadsheetId=config.SPREADSHEET_ID,
                        body=batch_update
                    ).execute()
                    
                    # Only verify on the final attempt or if previous attempt failed
                    if attempt == max_retries - 1 or attempt > 0:
                        if not self._verify_sheet_update(range_name, values):
                            if attempt < max_retries - 1:
                                time.sleep(retry_delays[attempt])
                                continue
                            st.error(f"Failed to verify update of {range_name} after {max_retries} attempts")
                            return False

                    # Get the total number of rows in the sheet
                    result = self.sheet.values().get(
                        spreadsheetId=config.SPREADSHEET_ID,
                        range=f"{range_name}"
                    ).execute()
                    all_values = result.get('values', [])
                    total_rows = len(all_values)
                    
                    # If there are extra rows beyond our data, clear them
                    if total_rows > num_rows + 1:  # +1 for header
                        self.sheet.values().clear(
                            spreadsheetId=config.SPREADSHEET_ID,
                            range=f"{range_name}!A{num_rows + 2}:{end_col}{total_rows}",
                            body={}
                        ).execute()
                
                return True

            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(retry_delays[attempt])
                    st.write(f"Retry {attempt + 1}/{max_retries} after error: {str(e)}")
                    continue
                st.error(f"Error updating sheet after {max_retries} attempts: {str(e)}")
                return False

        return False

    def update_match_status(self, match_id, new_status):
        try:
            matches_df = self.read_sheet(config.SHEET_MATCHES)
            match_index = matches_df[matches_df[config.COL_MATCH_ID] == match_id].index[0]
            match = matches_df.iloc[match_index]
            
            matches_df.loc[match_index, config.COL_MATCH_STATUS] = new_status
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if new_status == config.STATUS_IN_PROGRESS:
                matches_df.loc[match_index, config.COL_START_TIME] = current_time
            elif new_status == config.STATUS_COMPLETED:
                matches_df.loc[match_index, config.COL_END_TIME] = current_time
                
                # Get the court number before updating
                completed_court = match[config.COL_COURT_NUMBER]
                
                # Find the next queued match and assign it to this court
                queued_matches = matches_df[matches_df[config.COL_MATCH_STATUS] == "Queued"]
                if not queued_matches.empty:
                    next_match_index = queued_matches.index[0]
                    matches_df.loc[next_match_index, config.COL_COURT_NUMBER] = completed_court
                    matches_df.loc[next_match_index, config.COL_MATCH_STATUS] = config.STATUS_SCHEDULED
            
            result = self.update_sheet(config.SHEET_MATCHES, [matches_df.columns.tolist()] + matches_df.values.tolist())
            return result
        except Exception as e:
            st.write(f"Error updating match status: {str(e)}")
            return False

    def update_match_score(self, match_id, team1_score, team2_score):
        """Update match score and handle all related updates."""
        try:
            # Convert scores to integers
            team1_score = int(team1_score)
            team2_score = int(team2_score)
            
            # Get matches DataFrame
            matches_df = self.read_sheet(config.SHEET_MATCHES)
            
            # Find the match
            match_idx = matches_df[matches_df[config.COL_MATCH_ID] == match_id].index[0]
            match = matches_df.iloc[match_idx]
            
            # Store the court number before updating status
            freed_court = match[config.COL_COURT_NUMBER]
            
            # Update match scores and status
            matches_df.loc[match_idx, config.COL_TEAM1_SCORE] = team1_score
            matches_df.loc[match_idx, config.COL_TEAM2_SCORE] = team2_score
            matches_df.loc[match_idx, config.COL_MATCH_STATUS] = config.STATUS_COMPLETED
            matches_df.loc[match_idx, config.COL_END_TIME] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Calculate points
            point_diff = abs(team1_score - team2_score)
            team1_won = team1_score > team2_score
            
            # Base points
            team1_base = 2 if team1_won else 1
            team2_base = 2 if not team1_won else 1
            
            # Performance bonus
            if team1_won:
                team1_bonus = min(1.0, point_diff * 0.1)  # Winner's bonus (unchanged)
                team2_bonus = float(team2_score) / float(team1_score)  # Loser's performance ratio
            else:
                team2_bonus = min(1.0, point_diff * 0.1)  # Winner's bonus (unchanged)
                team1_bonus = float(team1_score) / float(team2_score)  # Loser's performance ratio
            
            # Total points for each team
            team1_points = team1_base + team1_bonus
            team2_points = team2_base + team2_bonus
            
            # Get players DataFrame and scores DataFrame
            players_df = self.read_sheet(config.SHEET_PLAYERS)
            scores_df = self.read_sheet(config.SHEET_SCORES)
            
            # Prepare new scores data
            new_scores = []
            
            # Update points and games played for each player
            for player in [match[config.COL_TEAM1_PLAYER1], match[config.COL_TEAM1_PLAYER2]]:
                if pd.notna(player):
                    player_idx = players_df[players_df[config.COL_NAME] == player].index[0]
                    
                    # Get current values, defaulting to 0 if empty or NaN
                    current_points = players_df.loc[player_idx, config.COL_TOTAL_POINTS]
                    current_points = float(current_points) if pd.notna(current_points) and current_points != '' else 0.0
                    
                    current_games = players_df.loc[player_idx, config.COL_GAMES_PLAYED]
                    current_games = int(float(current_games)) if pd.notna(current_games) and current_games != '' else 0
                    
                    # Update values
                    players_df.loc[player_idx, config.COL_TOTAL_POINTS] = current_points + team1_points
                    players_df.loc[player_idx, config.COL_GAMES_PLAYED] = current_games + 1
                    
                    # Update average points
                    total_points = players_df.loc[player_idx, config.COL_TOTAL_POINTS]
                    games_played = players_df.loc[player_idx, config.COL_GAMES_PLAYED]
                    players_df.loc[player_idx, config.COL_AVG_POINTS] = total_points / games_played if games_played > 0 else 0
                    
                    # Add score record
                    new_scores.append([match_id, player, team1_points])
            
            for player in [match[config.COL_TEAM2_PLAYER1], match[config.COL_TEAM2_PLAYER2]]:
                if pd.notna(player):
                    player_idx = players_df[players_df[config.COL_NAME] == player].index[0]
                    
                    # Get current values, defaulting to 0 if empty or NaN
                    current_points = players_df.loc[player_idx, config.COL_TOTAL_POINTS]
                    current_points = float(current_points) if pd.notna(current_points) and current_points != '' else 0.0
                    
                    current_games = players_df.loc[player_idx, config.COL_GAMES_PLAYED]
                    current_games = int(float(current_games)) if pd.notna(current_games) and current_games != '' else 0
                    
                    # Update values
                    players_df.loc[player_idx, config.COL_TOTAL_POINTS] = current_points + team2_points
                    players_df.loc[player_idx, config.COL_GAMES_PLAYED] = current_games + 1
                    
                    # Update average points
                    total_points = players_df.loc[player_idx, config.COL_TOTAL_POINTS]
                    games_played = players_df.loc[player_idx, config.COL_GAMES_PLAYED]
                    players_df.loc[player_idx, config.COL_AVG_POINTS] = total_points / games_played if games_played > 0 else 0
                    
                    # Add score record
                    new_scores.append([match_id, player, team2_points])
            
            # Update sheets
            self.update_sheet(config.SHEET_MATCHES, [matches_df.columns.tolist()] + matches_df.values.tolist())
            self.update_sheet(config.SHEET_PLAYERS, [players_df.columns.tolist()] + players_df.values.tolist())
            
            # Update scores sheet
            if scores_df.empty:
                # If scores sheet is empty, create it with headers
                scores_data = [[config.COL_MATCH_ID, config.COL_NAME, config.COL_TOTAL_POINTS]] + new_scores
            else:
                # Append new scores to existing data
                scores_data = [scores_df.columns.tolist()] + scores_df.values.tolist() + new_scores
            
            self.update_sheet(config.SHEET_SCORES, scores_data)
            
            # Try to assign courts to the newly added matches
            self.assign_courts_to_pending_matches()
            
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
        players_df.loc[player_idx, config.COL_STATUS] = status
        
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

    def check_and_assign_courts(self):
        """Check for available courts and assign them to pending matches."""
        return self.assign_courts_to_pending_matches()

    def assign_courts_to_pending_matches(self):
        """Assign available courts to pending matches."""
        try:
            # Get current matches
            matches_df = self.read_sheet(config.SHEET_MATCHES)
            
            # Find courts that are currently in use (only scheduled or in-progress matches)
            active_matches = matches_df[
                (matches_df[config.COL_MATCH_STATUS].isin([config.STATUS_SCHEDULED, config.STATUS_IN_PROGRESS])) &
                (matches_df[config.COL_COURT_NUMBER].notna()) &  # Must have a court number
                (matches_df[config.COL_COURT_NUMBER] != "")  # Must not be empty string
            ]
            
            # Get players who are currently in active matches
            busy_players = set()
            for _, match in active_matches.iterrows():
                players = [
                    match[config.COL_TEAM1_PLAYER1],
                    match[config.COL_TEAM1_PLAYER2],
                    match[config.COL_TEAM2_PLAYER1],
                    match[config.COL_TEAM2_PLAYER2]
                ]
                busy_players.update(p for p in players if pd.notna(p))
            
            used_courts = set(str(court) for court in active_matches[config.COL_COURT_NUMBER] if pd.notna(court) and court != "")
            
            # Get available courts (1-6)
            available_courts = [str(i) for i in range(1, 7) if str(i) not in used_courts]
            
            if not available_courts:
                return False
            
            # Find pending matches
            pending_matches = matches_df[
                (matches_df[config.COL_MATCH_STATUS] == config.STATUS_PENDING)
            ].copy()
            
            if pending_matches.empty:
                st.info("No pending matches to assign courts to")
                return False
                
            updates_made = False
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # For each pending match, assign a court if available and players aren't busy
            for idx, match in pending_matches.iterrows():
                match_id = match[config.COL_MATCH_ID]
                
                # Skip if match already has a valid court number
                court_number = match[config.COL_COURT_NUMBER]
                if pd.notna(court_number) and court_number != "":
                    continue
                
                # Check if any players in this match are already playing
                match_players = {
                    match[config.COL_TEAM1_PLAYER1],
                    match[config.COL_TEAM1_PLAYER2],
                    match[config.COL_TEAM2_PLAYER1],
                    match[config.COL_TEAM2_PLAYER2]
                }
                match_players = {p for p in match_players if pd.notna(p)}  # Remove any NaN values
                
                # If any players are busy, skip this match
                if match_players & busy_players:
                    #st.write(f"Skipping match {match_id} - players already in active matches")
                    continue
                
                if available_courts:  # We have courts available
                    court = available_courts.pop(0)  # Take the first available court
                    
                    # Update match in the matches_df DataFrame
                    matches_df.loc[idx, config.COL_COURT_NUMBER] = court
                    matches_df.loc[idx, config.COL_MATCH_STATUS] = config.STATUS_SCHEDULED
                    matches_df.loc[idx, config.COL_START_TIME] = current_time
                    updates_made = True
                    
                    # Add these players to busy_players for subsequent matches
                    busy_players.update(match_players)
            
            # Update the sheet if changes were made
            if updates_made:
                self.update_sheet(config.SHEET_MATCHES, [matches_df.columns.tolist()] + matches_df.values.tolist())
                st.success("Successfully assigned courts to pending matches")
                return True
            
            return False
            
        except Exception as e:
            st.error(f"Error assigning courts to pending matches: {str(e)}")
            return False

    def generate_next_matches(self, active_players, court_count):
        """Generate optimal matches based on player history."""
        try:
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
                    config.STATUS_PENDING,  # Set initial status as pending
                    match[config.COL_MATCH_TYPE]
                ])
                
            # Append new matches to existing ones
            all_matches = pd.concat([matches_df, pd.DataFrame(new_rows, columns=matches_df.columns)], ignore_index=True)
            
            # Update the matches sheet
            self.update_sheet(config.SHEET_MATCHES, [all_matches.columns.tolist()] + all_matches.values.tolist())

            # Try to assign courts to the newly added matches
            self.assign_courts_to_pending_matches()
            
            return True
            
        except Exception as e:
            st.error(f"Error generating matches: {str(e)}")
            return False

    def _get_player_interactions(self, matches_df):
        """Track who has played with/against whom."""
        interactions = {}  # {player: {'with': set(), 'against': set()}}
        
        for _, match in matches_df.iterrows():
            team1 = [match[config.COL_TEAM1_PLAYER1], match[config.COL_TEAM1_PLAYER2]]
            team2 = [match[config.COL_TEAM2_PLAYER1], match[config.COL_TEAM2_PLAYER2]]
            all_players = team1 + team2
            
            # Initialize if needed
            for player in all_players:
                if player not in interactions:
                    interactions[player] = {'with': set(), 'against': set()}
            
            # Record interactions
            for p1 in team1:
                interactions[p1]['with'].add(team1[1] if p1 == team1[0] else team1[0])
                for p2 in team2:
                    interactions[p1]['against'].add(p2)
            
            for p1 in team2:
                interactions[p1]['with'].add(team2[1] if p1 == team2[0] else team2[0])
                for p2 in team1:
                    interactions[p1]['against'].add(p2)
        
        return interactions

    def _calculate_wait_time(self, player, current_time):
        """Calculate how long a player has been waiting since their last match."""
        matches_df = self.read_sheet(config.SHEET_MATCHES)
        player_matches = matches_df[
            (matches_df[config.COL_TEAM1_PLAYER1] == player) |
            (matches_df[config.COL_TEAM1_PLAYER2] == player) |
            (matches_df[config.COL_TEAM2_PLAYER1] == player) |
            (matches_df[config.COL_TEAM2_PLAYER2] == player)
        ]
        
        if player_matches.empty:
            return float('inf')  # Player hasn't played yet
            
        last_match = player_matches.iloc[-1]
        last_match_time = last_match[config.COL_END_TIME]
        
        if pd.isna(last_match_time) or last_match_time == "":
            return float('inf')
            
        try:
            last_match_dt = datetime.strptime(last_match_time, "%Y-%m-%d %H:%M:%S")
            current_dt = datetime.strptime(current_time, "%Y-%m-%d %H:%M:%S")
            wait_time = (current_dt - last_match_dt).total_seconds() / 60  # Convert to minutes
            return wait_time
        except:
            return float('inf')

    def score_combination(self, players, match_type):
        score = 0
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Get wait times for all players
        wait_times = [self._calculate_wait_time(p, current_time) for p in players]
        max_wait_time = max(wait_times)
        
        # Heavily prioritize players who have been waiting longer
        score += max_wait_time * 3  # Increase score for players waiting longer
        
        # Prioritize players with fewer games
        games_played = [self.player_match_counts.get(p, 0) for p in players]
        score -= max(games_played) * 2  # Penalize players with many games
        
        # Check previous interactions
        for i, p1 in enumerate(players):
            for p2 in players[i+1:]:
                # Penalize if they've played together or against each other
                if p2 in self.player_interactions[p1]['with']:
                    score -= 3
                if p2 in self.player_interactions[p1]['against']:
                    score -= 2
        
        return score

    def _generate_matches(self, active_players, court_count, matches_df):
        """Generate optimal matches based on player history"""
        try:
            # Get player genders from players sheet
            players_df = self.read_sheet(config.SHEET_PLAYERS)
            
            # Filter out any players that are not marked as Active in the sheet
            active_status_players = set(players_df[players_df[config.COL_STATUS] == "Active"][config.COL_NAME])
            active_players = [p for p in active_players if p in active_status_players]
            
            player_genders = dict(zip(players_df[config.COL_NAME], players_df[config.COL_GENDER]))
            
            # Split players by gender using the players sheet information
            male_players = [p for p in active_players if player_genders.get(p) == config.GENDER_MALE]
            female_players = [p for p in active_players if player_genders.get(p) == config.GENDER_FEMALE]
            
            # Debug information
            st.write(f"Male players: {len(male_players)}")
            st.write(f"Female players: {len(female_players)}")
            
            # Calculate match type ratios for each gender from match history
            male_match_counts = {"mens": 0, "mixed": 0}
            female_match_counts = {"womens": 0, "mixed": 0}
            
            for _, match in matches_df.iterrows():
                match_type = match[config.COL_MATCH_TYPE]
                players = [
                    match[config.COL_TEAM1_PLAYER1],
                    match[config.COL_TEAM1_PLAYER2],
                    match[config.COL_TEAM2_PLAYER1],
                    match[config.COL_TEAM2_PLAYER2]
                ]
                
                if match_type == "Mixed":
                    for player in players:
                        if pd.notna(player):
                            if player_genders.get(player) == config.GENDER_MALE:
                                male_match_counts["mixed"] += 1
                            elif player_genders.get(player) == config.GENDER_FEMALE:
                                female_match_counts["mixed"] += 1
                elif match_type == "Mens":
                    for player in players:
                        if pd.notna(player):
                            male_match_counts["mens"] += 1
                elif match_type == "Womens":
                    for player in players:
                        if pd.notna(player):
                            female_match_counts["womens"] += 1
            
            # Calculate ratios
            male_ratio = 0
            total_male_matches = male_match_counts["mens"] + male_match_counts["mixed"]
            if total_male_matches > 0:
                male_ratio = male_match_counts["mixed"] / total_male_matches
                
            female_ratio = 0
            total_female_matches = female_match_counts["womens"] + female_match_counts["mixed"]
            if total_female_matches > 0:
                female_ratio = female_match_counts["mixed"] / total_female_matches
            
            # Calculate dynamic distribution based on available players and match history
            total_players = len(male_players) + len(female_players)
            available_pairs = min(len(male_players), len(female_players))
            
            # Adjust match type distribution based on current ratios
            total_matches = min(court_count, len(active_players) // 4)
            
            # Prioritize match types to balance ratios
            match_types = []
            if male_ratio > 0.5 and len(male_players) >= 4:
                match_types.append("Mens")
            if female_ratio > 0.5 and len(female_players) >= 4:
                match_types.append("Womens")
            if (male_ratio < 0.5 or female_ratio < 0.5) and len(male_players) >= 2 and len(female_players) >= 2:
                match_types.append("Mixed")
                
            # If no preferred types available, fall back to all possible types
            if not match_types:
                if len(male_players) >= 4:
                    match_types.append("Mens")
                if len(female_players) >= 4:
                    match_types.append("Womens")
                if len(male_players) >= 2 and len(female_players) >= 2:
                    match_types.append("Mixed")
            
            # Get match history and interactions
            player_match_counts = self._get_player_match_counts(matches_df, active_players)
            player_interactions = self._get_player_interactions(matches_df)
            
            # Initialize if not in interactions
            for player in active_players:
                if player not in player_interactions:
                    player_interactions[player] = {'with': set(), 'against': set()}
            
            new_matches = []
            match_id_counter = self._get_next_match_id(matches_df)
            
            # Determine match generation order based on last match type
            last_match = matches_df.iloc[-1] if not matches_df.empty else None
            last_type = last_match[config.COL_MATCH_TYPE] if last_match is not None else None
            
            match_types = []
            if last_type == "Mixed":
                match_types = ["Mens", "Womens", "Mixed"]
            elif last_type == "Mens":
                match_types = ["Womens", "Mixed", "Mens"]
            else:
                match_types = ["Mixed", "Mens", "Womens"]
            
            # Helper function to score player combinations
            def score_combination(players, match_type):
                score = 0
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Get wait times for all players
                wait_times = [self._calculate_wait_time(p, current_time) for p in players]
                max_wait_time = max(wait_times)
                
                # Heavily prioritize players who have been waiting longer
                score += max_wait_time * 3  # Increase score for players waiting longer
                
                # Prioritize players with fewer games
                games_played = [player_match_counts.get(p, 0) for p in players]
                score -= max(games_played) * 2  # Penalize players with many games
                
                # Check previous interactions
                for i, p1 in enumerate(players):
                    for p2 in players[i+1:]:
                        # Penalize if they've played together or against each other
                        if p2 in player_interactions[p1]['with']:
                            score -= 3
                        if p2 in player_interactions[p1]['against']:
                            score -= 2
                
                return score
            
            # Helper function to get optimal player combination
            def get_optimal_players(available_players, count):
                if len(available_players) < count:
                    return None
                
                # Get players with fewest games first
                sorted_players = sorted(available_players, key=lambda p: player_match_counts.get(p, 0))
                candidates = sorted_players[:min(count * 2, len(sorted_players))]
                
                # Try different combinations of players
                best_score = float('-inf')
                best_combination = None
                
                from itertools import combinations
                for combo in combinations(candidates, count):
                    score = score_combination(combo, "")
                    if score > best_score:
                        best_score = score
                        best_combination = combo
                
                return list(best_combination) if best_combination else None
            
            # Generate matches in determined order
            for match_type in match_types:
                count = 1
                for _ in range(count):
                    if match_type == "Mixed":
                        if len(male_players) >= 2 and len(female_players) >= 2:
                            males = get_optimal_players(male_players, 2)
                            females = get_optimal_players(female_players, 2)
                            if males and females:
                                match = {
                                    config.COL_MATCH_ID: f"M{match_id_counter}",
                                    config.COL_COURT_NUMBER: "",
                                    config.COL_TEAM1_PLAYER1: males[0],
                                    config.COL_TEAM1_PLAYER2: females[0],
                                    config.COL_TEAM2_PLAYER1: males[1],
                                    config.COL_TEAM2_PLAYER2: females[1],
                                    config.COL_START_TIME: "",
                                    config.COL_END_TIME: "",
                                    config.COL_TEAM1_SCORE: "",
                                    config.COL_TEAM2_SCORE: "",
                                    config.COL_MATCH_TYPE: "Mixed"
                                }
                                new_matches.append(match)
                                match_id_counter += 1
                                
                                # Update counts and remove used players
                                for player in males + females:
                                    player_match_counts[player] = player_match_counts.get(player, 0) + 1
                                male_players = [p for p in male_players if p not in males]
                                female_players = [p for p in female_players if p not in females]
                    
                    elif match_type == "Mens" and len(male_players) >= 4:
                        players = get_optimal_players(male_players, 4)
                        if players:
                            match = {
                                config.COL_MATCH_ID: f"M{match_id_counter}",
                                config.COL_COURT_NUMBER: "",
                                config.COL_TEAM1_PLAYER1: players[0],
                                config.COL_TEAM1_PLAYER2: players[1],
                                config.COL_TEAM2_PLAYER1: players[2],
                                config.COL_TEAM2_PLAYER2: players[3],
                                config.COL_START_TIME: "",
                                config.COL_END_TIME: "",
                                config.COL_TEAM1_SCORE: "",
                                config.COL_TEAM2_SCORE: "",
                                config.COL_MATCH_TYPE: "Mens"
                            }
                            new_matches.append(match)
                            match_id_counter += 1
                            
                            # Update counts and remove used players
                            for player in players:
                                player_match_counts[player] = player_match_counts.get(player, 0) + 1
                            male_players = [p for p in male_players if p not in players]
                    
                    elif match_type == "Womens" and len(female_players) >= 4:
                        players = get_optimal_players(female_players, 4)
                        if players:
                            match = {
                                config.COL_MATCH_ID: f"M{match_id_counter}",
                                config.COL_COURT_NUMBER: "",
                                config.COL_TEAM1_PLAYER1: players[0],
                                config.COL_TEAM1_PLAYER2: players[1],
                                config.COL_TEAM2_PLAYER1: players[2],
                                config.COL_TEAM2_PLAYER2: players[3],
                                config.COL_START_TIME: "",
                                config.COL_END_TIME: "",
                                config.COL_TEAM1_SCORE: "",
                                config.COL_TEAM2_SCORE: "",
                                config.COL_MATCH_TYPE: "Womens"
                            }
                            new_matches.append(match)
                            match_id_counter += 1
                            
                            # Update counts and remove used players
                            for player in players:
                                player_match_counts[player] = player_match_counts.get(player, 0) + 1
                            female_players = [p for p in female_players if p not in players]
            
            return new_matches if new_matches else None
            
        except Exception as e:
            st.error(f"Error generating matches: {str(e)}")
            return None

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
                self.assign_courts_to_pending_matches()
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
                    self.assign_courts_to_pending_matches()
                    return True, f"Removed {len(match_ids)} matches for inactive player"
                else:
                    return False, "Failed to remove matches"
            
            return True, "No active matches found for player"
            
        except Exception as e:
            return False, f"Error handling player inactivation: {str(e)}"

    def remove_matches(self, match_ids, assign_pending=True, return_freed_courts=False):
        """Remove specified matches from the Matches sheet and optionally assign pending matches to freed courts."""
        matches_df = self.read_sheet(config.SHEET_MATCHES)
        
        # Get courts that will be freed up
        freed_courts = matches_df[
            (matches_df[config.COL_MATCH_ID].isin(match_ids)) &
            (matches_df[config.COL_COURT_NUMBER].notna()) &  # Must have a court number
            (matches_df[config.COL_COURT_NUMBER] != "") &  # Must not be empty string
            (matches_df[config.COL_MATCH_STATUS].isin([config.STATUS_SCHEDULED, config.STATUS_IN_PROGRESS]))
        ][config.COL_COURT_NUMBER].unique().tolist()  # Use unique to prevent duplicates
        
        # Remove the matches
        matches_df = matches_df[~matches_df[config.COL_MATCH_ID].isin(match_ids)]
        
        # Update the matches sheet
        self.update_sheet(config.SHEET_MATCHES, [matches_df.columns.tolist()] + matches_df.values.tolist())
        
        # Either assign pending matches or return the freed courts
        if assign_pending and freed_courts:
            self.assign_courts_to_pending_matches()
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

    def _get_player_match_counts(self, matches_df, active_players):
        """Get the number of matches played by each player"""
        player_match_counts = {}
        for _, match in matches_df.iterrows():
            for player in [match[config.COL_TEAM1_PLAYER1], match[config.COL_TEAM1_PLAYER2],
                         match[config.COL_TEAM2_PLAYER1], match[config.COL_TEAM2_PLAYER2]]:
                if player in active_players:
                    player_match_counts[player] = player_match_counts.get(player, 0) + 1
        return player_match_counts

    def _get_next_match_id(self, matches_df):
        """Get the next available match ID"""
        match_id_pattern = r'M(\d+)'
        existing_match_ids = matches_df[config.COL_MATCH_ID].str.extract(match_id_pattern, expand=False).astype(float)
        return int(existing_match_ids.max() + 1) if not existing_match_ids.empty else 1
