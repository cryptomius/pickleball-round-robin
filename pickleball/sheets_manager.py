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
import logging

class SheetsManager:
    def __init__(self):
        self.api_calls = 0
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
            self._sheet_cache = {}  # Cache for sheet data
        except Exception as e:
            st.write(f"Error initializing SheetsManager: {str(e)}")
            raise

    def _log_api_call(self, operation):
        """Log API call for tracking"""
        self.api_calls += 1

    def get_sheet_modified_time(self, sheet_name):
        """Get the last modified time of a sheet"""
        self._log_api_call(f"Getting modified time for sheet {sheet_name}")
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
        cache_key = f"{range_name}_{int(time.time() / 60)}"  # Cache key changes every minute
        if cache_key in self._sheet_cache:
            return self._sheet_cache[cache_key]

        self._log_api_call(f"Reading sheet {range_name}")
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
                
                # Cache the result
                self._sheet_cache[cache_key] = df
                return df

            except HttpError as e:
                if e.resp.status == 429:  # Quota exceeded error
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                st.error(f"Error reading sheet after {max_retries} attempts: {str(e)}")
                return pd.DataFrame()
            except Exception as e:
                st.error(f"Error reading sheet: {str(e)}")
                return pd.DataFrame()

    def _clear_cache(self):
        """Clear internal sheet cache"""
        self._sheet_cache = {}
        self._last_modified = {}

    def update_sheet(self, range_name, values):
        """Update a sheet with new values. Updates in-place without clearing first."""
        self._log_api_call(f"Updating sheet {range_name}")
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
                
                # Clear cache after successful write
                self._clear_cache()
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
        try:
            if status not in [config.STATUS_PLAYER_ACTIVE, config.STATUS_PLAYER_INACTIVE]:
                raise ValueError(f"Invalid status: {status}")
            
            players_df = self.read_sheet(config.SHEET_PLAYERS)
            player_idx = players_df[players_df[config.COL_NAME] == player_name].index[0]
            players_df.loc[player_idx, config.COL_STATUS] = status
            
            # Update the sheet
            success = self.update_sheet(config.SHEET_PLAYERS, [players_df.columns.tolist()] + players_df.values.tolist())
            
            if success:
                self._clear_cache()  # Clear cache after successful update
                if status == config.STATUS_PLAYER_INACTIVE:
                    # Handle removal of matches when deactivating
                    self.handle_player_inactivation(player_name)
                return True
            return False
        except Exception as e:
            st.error(f"Error updating player status: {str(e)}")
            return False

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
        success = self.update_sheet(config.SHEET_PLAYERS, [players_df.columns.tolist()] + players_df.values.tolist())
        
        if success:
            self._clear_cache()  # Clear the cache after successful update
        
        return success

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
                #st.success("Successfully assigned courts to pending matches")
                return True
            
            return False
            
        except Exception as e:
            st.error(f"Error assigning courts to pending matches: {str(e)}")
            return False

    def generate_next_matches(self, active_players, court_count):
        """Generate optimal matches based on player history."""
        try:
            import streamlit as st
            
            # Cache the players and matches data
            with st.spinner("Loading player and match data..."):
                players_df = self.read_sheet(config.SHEET_PLAYERS)
                matches_df = self.read_sheet(config.SHEET_MATCHES)
                
                # Pre-calculate wait times for all players using cached matches_df
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.player_wait_times = {
                    player: self._calculate_wait_time(player, current_time, matches_df)
                    for player in active_players
                }
                
                # Filter out any players that are not marked as Active in the sheet
                active_status_players = set(players_df[players_df[config.COL_STATUS] == "Active"][config.COL_NAME])
                active_players = [p for p in active_players if p in active_status_players]
                
                player_genders = dict(zip(players_df[config.COL_NAME], players_df[config.COL_GENDER]))
                
                # Split players by gender using the players sheet information
                male_players = [p for p in active_players if player_genders.get(p) == config.GENDER_MALE]
                female_players = [p for p in active_players if player_genders.get(p) == config.GENDER_FEMALE]
                
                # Pre-calculate all player interactions using cached matches_df
                self.player_interactions = self._get_player_interactions(matches_df)
                for player in active_players:
                    if player not in self.player_interactions:
                        self.player_interactions[player] = {'with': set(), 'against': set()}
                
                # Pre-calculate match counts using cached matches_df
                self.player_match_counts, self.match_type_counts = self._get_player_match_counts(active_players, matches_df)
            
            # Calculate current match type ratios
            total_matches = len(matches_df) if not matches_df.empty else 0
            if total_matches > 0:
                mixed_ratio = len(matches_df[matches_df[config.COL_MATCH_TYPE] == 'Mixed']) / total_matches
                mens_ratio = len(matches_df[matches_df[config.COL_MATCH_TYPE] == 'Mens']) / total_matches
                womens_ratio = len(matches_df[matches_df[config.COL_MATCH_TYPE] == 'Womens']) / total_matches
                print(f"Current match type ratios - Mixed: {mixed_ratio:.2f}, Mens: {mens_ratio:.2f}, Womens: {womens_ratio:.2f}")
            
            # Generate all possible combinations
            from itertools import combinations
            possible_matches = []
            
            with st.spinner("Generating possible match combinations..."):
                progress_bar = st.progress(0)
                total_steps = 3  # Mixed, Mens, Womens
                current_step = 0
                
                # Generate Mixed Doubles combinations
                if len(male_players) >= 2 and len(female_players) >= 2:
                    male_combos = list(combinations(male_players, 2))
                    female_combos = list(combinations(female_players, 2))
                    total_mixed = len(male_combos) * len(female_combos)
                    
                    for i, males in enumerate(male_combos):
                        for females in female_combos:
                            match = {
                                'players': (males[0], females[0], males[1], females[1]),
                                'type': 'Mixed',
                                'score': self.score_combination([males[0], females[0], males[1], females[1]], 'Mixed')
                            }
                            possible_matches.append(match)
                            
                            # Update progress every 100 combinations
                            if len(possible_matches) % 100 == 0:
                                progress = (i * len(female_combos)) / total_mixed / total_steps
                                progress_bar.progress(progress)
                
                current_step += 1
                progress_bar.progress(current_step / total_steps)
                
                # Generate Mens Doubles combinations
                if len(male_players) >= 4:
                    mens_combos = list(combinations(male_players, 4))
                    for i, players in enumerate(mens_combos):
                        match = {
                            'players': players,
                            'type': 'Mens',
                            'score': self.score_combination(players, 'Mens')
                        }
                        possible_matches.append(match)
                        
                        # Update progress every 10 combinations
                        if i % 10 == 0:
                            progress = (current_step + (i / len(mens_combos))) / total_steps
                            progress_bar.progress(progress)
                
                current_step += 1
                progress_bar.progress(current_step / total_steps)
                
                # Generate Womens Doubles combinations
                if len(female_players) >= 4:
                    womens_combos = list(combinations(female_players, 4))
                    for i, players in enumerate(womens_combos):
                        match = {
                            'players': players,
                            'type': 'Womens',
                            'score': self.score_combination(players, 'Womens')
                        }
                        possible_matches.append(match)
                        
                        # Update progress every 10 combinations
                        if i % 10 == 0:
                            progress = (current_step + (i / len(womens_combos))) / total_steps
                            progress_bar.progress(progress)
                
                progress_bar.progress(1.0)
            
            # Sort by score
            with st.spinner("Selecting optimal matches..."):
                possible_matches.sort(key=lambda x: x['score'], reverse=True)
                
                # Select best balanced set
                selected = []
                used_players = set()
                selected_type_counts = {'Mixed': 0, 'Mens': 0, 'Womens': 0}
                
                while len(selected) < court_count and possible_matches:
                    for match in possible_matches[:]:
                        # Skip if any player already used
                        if any(p in used_players for p in match['players']):
                            continue
                        
                        # Check match type balance for this batch
                        current_type = match['type']
                        total_selected = sum(selected_type_counts.values())
                        if total_selected > 0:
                            type_ratio = selected_type_counts[current_type] / total_selected
                            if type_ratio > 0.6:  # No more than 60% of any type
                                continue
                        
                        # Add match
                        selected.append(match)
                        used_players.update(match['players'])
                        selected_type_counts[current_type] += 1
                        possible_matches.remove(match)
                        break
                    else:
                        break  # No valid match found
                
                print(f"Selected match types: {selected_type_counts}")
            
            # Convert to match format and write to sheet
            with st.spinner("Writing matches to sheet..."):
                new_matches = []
                match_id_counter = self._get_next_match_id()
                
                for match in selected:
                    players = match['players']
                    new_match = {
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
                        config.COL_MATCH_TYPE: match['type'],
                        config.COL_MATCH_STATUS: config.STATUS_PENDING
                    }
                    new_matches.append(new_match)
                    match_id_counter += 1
                
                if not new_matches:
                    print("No valid matches could be generated")
                    return []
                
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
                
                # Get existing matches or create empty DataFrame with correct columns
                if matches_df.empty:
                    matches_df = pd.DataFrame(columns=[
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
                
                # Append new matches to existing ones
                new_matches_df = pd.DataFrame(new_rows, columns=matches_df.columns)
                all_matches = pd.concat([matches_df, new_matches_df], ignore_index=True)
                
                # Update the matches sheet
                self.update_sheet(config.SHEET_MATCHES, [all_matches.columns.tolist()] + all_matches.values.tolist())
                
                # Clear cache after successful write
                self._clear_cache()
                
                print(f"Successfully generated and wrote {len(new_matches)} matches")
                
                # Assign courts to pending matches
                print("Assigning courts to pending matches...")
                self.assign_pending_matches_to_courts(court_count)
                
                return new_matches
            
        except Exception as e:
            print(f"Error generating matches: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def score_combination(self, players, match_type):
        score = 0
        matches_df = self.read_sheet(config.SHEET_MATCHES)
        
        # For first run with empty matches sheet, ensure mix of types
        if matches_df.empty:
            # Give slight preference to non-mixed matches initially
            if match_type in ['Mens', 'Womens']:
                score += 50
            return score
        
        # Calculate current match type ratios
        total_matches = len(matches_df)
        mixed_ratio = len(matches_df[matches_df[config.COL_MATCH_TYPE] == 'Mixed']) / total_matches
        mens_ratio = len(matches_df[matches_df[config.COL_MATCH_TYPE] == 'Mens']) / total_matches
        womens_ratio = len(matches_df[matches_df[config.COL_MATCH_TYPE] == 'Womens']) / total_matches
        
        # Adjust score based on match type ratios
        if mixed_ratio > 0.5 and match_type == 'Mixed':
            score -= 300  # Heavy penalty for too many mixed matches
        elif mens_ratio < 0.2 and match_type == 'Mens':
            score += 200  # Bonus for needed mens matches
        elif womens_ratio < 0.2 and match_type == 'Womens':
            score += 200  # Bonus for needed womens matches
        
        # Prefer players with fewer games
        max_games = max(self.player_match_counts.values()) if self.player_match_counts else 1
        for player in players:
            games_played = self.player_match_counts.get(player, 0)
            score += (max_games - games_played) * 2
        
        # Hard requirements for match type balance per player
        for player in players:
            total_matches = self.match_type_counts[player]['Mixed'] + self.match_type_counts[player]['Same']
            if total_matches >= 3:  # Only apply after a few matches
                mixed_ratio = self.match_type_counts[player]['Mixed'] / total_matches
                same_ratio = self.match_type_counts[player]['Same'] / total_matches
                
                # Severe penalty if ratio is too imbalanced (should be close to 0.5)
                if mixed_ratio > 0.6 and match_type == 'Mixed':
                    score -= 400  # Even heavier penalty for too many mixed matches
                elif same_ratio < 0.3 and match_type in ['Mens', 'Womens']:
                    score += 300  # Strong bonus for needed same-gender matches
        
        # Partner repetition penalty
        for i, p1 in enumerate(players):
            for p2 in players[i+1:]:
                if p2 in self.player_interactions[p1]['with']:
                    shared_matches = sum(1 for _, match in matches_df.iterrows() if 
                        ((match[config.COL_TEAM1_PLAYER1] == p1 and match[config.COL_TEAM1_PLAYER2] == p2) or
                         (match[config.COL_TEAM1_PLAYER2] == p1 and match[config.COL_TEAM1_PLAYER1] == p2) or
                         (match[config.COL_TEAM2_PLAYER1] == p1 and match[config.COL_TEAM2_PLAYER2] == p2) or
                         (match[config.COL_TEAM2_PLAYER2] == p1 and match[config.COL_TEAM2_PLAYER1] == p2)))
                    score -= 50 * shared_matches  # Doubled penalty for repeat partnerships
        
        return score

    def _get_player_interactions(self, matches_df=None):
        """Track who has played with/against whom."""
        if matches_df is None:
            matches_df = self.read_sheet(config.SHEET_MATCHES)
        
        interactions = {}
        
        for _, match in matches_df.iterrows():
            team1_players = [match[config.COL_TEAM1_PLAYER1], match[config.COL_TEAM1_PLAYER2]]
            team2_players = [match[config.COL_TEAM2_PLAYER1], match[config.COL_TEAM2_PLAYER2]]
            
            # Initialize player records if not exists
            for player in team1_players + team2_players:
                if pd.notna(player) and player not in interactions:
                    interactions[player] = {'with': set(), 'against': set()}
            
            # Record team1 interactions
            for i, p1 in enumerate(team1_players):
                if pd.notna(p1):
                    # Played with teammates
                    for p2 in team1_players[i+1:]:
                        if pd.notna(p2):
                            interactions[p1]['with'].add(p2)
                            interactions[p2]['with'].add(p1)
                    
                    # Played against opponents
                    for p2 in team2_players:
                        if pd.notna(p2):
                            interactions[p1]['against'].add(p2)
                            interactions[p2]['against'].add(p1)
            
            # Record team2 interactions
            for i, p1 in enumerate(team2_players):
                if pd.notna(p1):
                    for p2 in team2_players[i+1:]:
                        if pd.notna(p2):
                            interactions[p1]['with'].add(p2)
                            interactions[p2]['with'].add(p1)
        
        return interactions

    def _calculate_wait_time(self, player, current_time, matches_df=None):
        """Calculate how long a player has been waiting since their last match."""
        if matches_df is None:
            matches_df = self.read_sheet(config.SHEET_MATCHES)
        
        # Get player's matches
        player_matches = matches_df[
            (matches_df[config.COL_TEAM1_PLAYER1] == player) |
            (matches_df[config.COL_TEAM1_PLAYER2] == player) |
            (matches_df[config.COL_TEAM2_PLAYER1] == player) |
            (matches_df[config.COL_TEAM2_PLAYER2] == player)
        ]
        
        if player_matches.empty:
            return float('inf')  # Player hasn't played any matches
        
        # Get the most recent match
        last_match = player_matches.iloc[-1]
        last_match_time = last_match[config.COL_END_TIME] if pd.notna(last_match[config.COL_END_TIME]) else last_match[config.COL_START_TIME]
        
        if pd.isna(last_match_time) or last_match_time == '':
            return float('inf')
        
        # Calculate time difference
        last_match_dt = datetime.strptime(last_match_time, "%Y-%m-%d %H:%M:%S")
        current_dt = datetime.strptime(current_time, "%Y-%m-%d %H:%M:%S")
        wait_time = (current_dt - last_match_dt).total_seconds() / 60  # Convert to minutes
        
        return wait_time

    def _get_player_match_counts(self, active_players, matches_df=None):
        """Get the number of matches played by each player and their match type distribution"""
        if matches_df is None:
            matches_df = self.read_sheet(config.SHEET_MATCHES)
        
        match_counts = {}
        match_type_counts = {}  # Track mixed vs same-gender matches per player
        
        for player in active_players:
            match_counts[player] = 0
            match_type_counts[player] = {'Mixed': 0, 'Same': 0}  # Same represents Mens/Womens
            
            # Count completed and in-progress matches
            player_matches = matches_df[
                ((matches_df[config.COL_TEAM1_PLAYER1] == player) |
                 (matches_df[config.COL_TEAM1_PLAYER2] == player) |
                 (matches_df[config.COL_TEAM2_PLAYER1] == player) |
                 (matches_df[config.COL_TEAM2_PLAYER2] == player)) &
                (matches_df[config.COL_MATCH_STATUS].isin([config.STATUS_COMPLETED, config.STATUS_IN_PROGRESS, config.STATUS_SCHEDULED, config.STATUS_PENDING]))
            ]
            
            match_counts[player] = len(player_matches)
            
            # Count match types
            for _, match in player_matches.iterrows():
                if match[config.COL_MATCH_TYPE] == 'Mixed':
                    match_type_counts[player]['Mixed'] += 1
                else:
                    match_type_counts[player]['Same'] += 1
        
        return match_counts, match_type_counts

    def _get_next_match_id(self):
        """Get the next available match ID"""
        match_id_pattern = r'M(\d+)'
        existing_match_ids = self.read_sheet(config.SHEET_MATCHES)[config.COL_MATCH_ID].str.extract(match_id_pattern, expand=False).astype(float)
        return int(existing_match_ids.max() + 1) if not existing_match_ids.empty else 1

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
                    self._clear_cache()  # Clear cache after handling matches
                    return True, f"Removed {len(match_ids)} matches for inactive player"
                else:
                    return False, "Failed to remove matches"
            
            return True, "No active matches found for player"
            
        except Exception as e:
            st.error(f"Error handling player matches: {str(e)}")
            return False, f"Error handling player matches: {str(e)}"

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

    def get_available_courts(self, total_courts):
        """Get list of courts that don't have scheduled/in-progress matches."""
        matches_df = self.read_sheet(config.SHEET_MATCHES)
        if matches_df.empty:
            return list(range(1, total_courts + 1))
            
        # Get courts that are currently in use (scheduled or in progress)
        busy_courts = set(matches_df[
            (matches_df[config.COL_MATCH_STATUS].isin([config.STATUS_SCHEDULED, config.STATUS_IN_PROGRESS])) &
            (matches_df[config.COL_COURT_NUMBER].notna()) &
            (matches_df[config.COL_COURT_NUMBER] != "")
        ][config.COL_COURT_NUMBER].astype(int).unique())
        
        # Return available courts
        all_courts = set(range(1, total_courts + 1))
        available_courts = list(all_courts - busy_courts)
        available_courts.sort()  # Keep courts in order
        return available_courts

    def assign_pending_matches_to_courts(self, total_courts):
        """Assign pending matches to available courts."""
        try:
            # Get truly available courts
            available_courts = self.get_available_courts(total_courts)
            if not available_courts:
                print("No courts available")
                return False
                
            # Get current matches
            matches_df = self.read_sheet(config.SHEET_MATCHES)
            if matches_df.empty:
                print("No matches found")
                return False
            
            # Filter for pending matches
            pending_matches = matches_df[
                (matches_df[config.COL_MATCH_STATUS] == config.STATUS_PENDING) & 
                (matches_df[config.COL_COURT_NUMBER].isna() | (matches_df[config.COL_COURT_NUMBER] == ""))
            ]
            
            if pending_matches.empty:
                print("No pending matches found")
                return False
            
            # Assign courts to pending matches
            court_assignments = {}
            available_courts = list(available_courts)  # Make a copy to avoid modifying original
            
            for _, match in pending_matches.iterrows():
                match_id = match[config.COL_MATCH_ID]
                if available_courts:
                    court = available_courts.pop(0)
                    court_assignments[match_id] = court
            
            if not court_assignments:
                print("No courts available to assign")
                return False
            
            # Update matches with court assignments
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for match_id, court in court_assignments.items():
                matches_df.loc[matches_df[config.COL_MATCH_ID] == match_id, config.COL_COURT_NUMBER] = court
                matches_df.loc[matches_df[config.COL_MATCH_ID] == match_id, config.COL_START_TIME] = current_time
                matches_df.loc[matches_df[config.COL_MATCH_ID] == match_id, config.COL_MATCH_STATUS] = config.STATUS_SCHEDULED
            
            # Write updated matches back to sheet
            self.update_sheet(config.SHEET_MATCHES, [matches_df.columns.tolist()] + matches_df.values.tolist())
            
            # Clear cache after update
            self._clear_cache()
            
            print(f"Assigned {len(court_assignments)} matches to courts {list(court_assignments.values())}")
            return True
            
        except Exception as e:
            print(f"Error assigning courts: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
