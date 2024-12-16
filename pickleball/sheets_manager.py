from google.oauth2 import service_account
from googleapiclient.discovery import build
import pandas as pd
import numpy as np
from datetime import datetime
from . import config
import random
import os
import json
import streamlit as st

class SheetsManager:
    def __init__(self):
        try:
            import streamlit as st
            
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
            print(f"Error initializing SheetsManager: {str(e)}")
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
        """Read a sheet and return as DataFrame with proper column names"""
        result = self.sheet.values().get(
            spreadsheetId=config.SPREADSHEET_ID,
            range=range_name
        ).execute()
        values = result.get('values', [])
        
        if not values:
            # Return empty DataFrame with correct columns based on sheet name
            if range_name == config.SHEET_COURTS:
                return pd.DataFrame(columns=[config.COL_COURT_NUMBER, config.COL_STATUS, config.COL_MATCH_ID])
            elif range_name == config.SHEET_PLAYERS:
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
                    config.COL_MATCH_STATUS
                ])
            elif range_name == config.SHEET_SCORES:
                return pd.DataFrame(columns=[config.COL_MATCH_ID, config.COL_NAME, config.COL_TOTAL_POINTS])
            else:
                return pd.DataFrame()

        # Get the header row and ensure it matches our expected columns
        header = values[0]
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
                config.COL_MATCH_STATUS
            ]
        elif range_name == config.SHEET_COURTS:
            expected_header = [config.COL_COURT_NUMBER, config.COL_STATUS, config.COL_MATCH_ID]
        elif range_name == config.SHEET_SCORES:
            expected_header = [config.COL_MATCH_ID, config.COL_NAME, config.COL_TOTAL_POINTS]

        if expected_header and header != expected_header:
            header = expected_header

        # Ensure all rows have the same number of columns as the header
        data = []
        for row in values[1:]:
            # Pad row with empty strings if it's shorter than header
            padded_row = row + [''] * (len(header) - len(row))
            data.append(padded_row[:len(header)])  # Truncate if longer than header
            
        return pd.DataFrame(data, columns=header)

    def update_sheet(self, range_name, values):
        """Update a sheet with new values, clearing any existing data first."""
        try:
            # Clear the entire range first
            clear_result = self.sheet.values().clear(
                spreadsheetId=config.SPREADSHEET_ID,
                range=range_name
            ).execute()

            # Then update with new values
            body = {
                'values': values
            }
            result = self.sheet.values().update(
                spreadsheetId=config.SPREADSHEET_ID,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            return True
        except Exception as e:
            print(f"Error updating sheet: {str(e)}")
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
            print(f"Error updating match status: {str(e)}")
            return False

    def update_match_score(self, match_id, team1_score, team2_score):
        """Update match score and handle all related updates."""
        try:
            # 1. Update Matches sheet
            matches_df = self.read_sheet(config.SHEET_MATCHES)
            match_index = matches_df[matches_df[config.COL_MATCH_ID] == match_id].index[0]
            match = matches_df.iloc[match_index]
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Update match details
            matches_df.at[match_index, config.COL_TEAM1_SCORE] = team1_score
            matches_df.at[match_index, config.COL_TEAM2_SCORE] = team2_score
            matches_df.at[match_index, config.COL_END_TIME] = current_time
            matches_df.at[match_index, config.COL_MATCH_STATUS] = config.STATUS_COMPLETED
            
            # Get the court number before updating
            completed_court = match[config.COL_COURT_NUMBER]
            
            # Find next pending match to assign to this court
            pending_matches = matches_df[matches_df[config.COL_MATCH_STATUS] == config.STATUS_PENDING]
            if not pending_matches.empty:
                next_match_index = pending_matches.index[0]
                matches_df.at[next_match_index, config.COL_COURT_NUMBER] = completed_court
                matches_df.at[next_match_index, config.COL_MATCH_STATUS] = config.STATUS_SCHEDULED
            
            # Update matches sheet
            self.update_sheet(config.SHEET_MATCHES, [matches_df.columns.tolist()] + matches_df.values.tolist())
            
            # 2. Calculate points based on scores
            score_diff = abs(team1_score - team2_score)
            bonus_points = min(score_diff * config.BONUS_POINT_PER_DIFF, config.MAX_BONUS_POINTS)
            
            if team1_score > team2_score:
                team1_points = config.POINTS_WIN + bonus_points  # Win points (2) + bonus
                team2_points = config.POINTS_LOSS               # Loss points (1)
            else:
                team1_points = config.POINTS_LOSS               # Loss points (1)
                team2_points = config.POINTS_WIN + bonus_points  # Win points (2) + bonus
            
            # 3. Update Players sheet
            players_df = self.read_sheet(config.SHEET_PLAYERS)
            
            # Get player names
            team1_players = [match[config.COL_TEAM1_PLAYER1], match[config.COL_TEAM1_PLAYER2]]
            team2_players = [match[config.COL_TEAM2_PLAYER1], match[config.COL_TEAM2_PLAYER2]]
            
            # Update each player's stats
            for player, points in zip(team1_players + team2_players, 
                                    [team1_points]*2 + [team2_points]*2):
                player_idx = players_df[players_df[config.COL_NAME] == player].index[0]
                
                # Get current values, defaulting to 0 if empty
                current_points = players_df.at[player_idx, config.COL_TOTAL_POINTS]
                current_games = players_df.at[player_idx, config.COL_GAMES_PLAYED]
                
                if pd.isna(current_points) or current_points == '':
                    current_points = 0
                if pd.isna(current_games) or current_games == '':
                    current_games = 0
                
                # Update player stats
                new_points = float(current_points) + points
                new_games = int(current_games) + 1
                
                players_df.at[player_idx, config.COL_TOTAL_POINTS] = new_points
                players_df.at[player_idx, config.COL_GAMES_PLAYED] = new_games
                players_df.at[player_idx, config.COL_LAST_MATCH_TIME] = current_time
                players_df.at[player_idx, config.COL_AVG_POINTS] = round(new_points / new_games, 2)
            
            # Update players sheet
            self.update_sheet(config.SHEET_PLAYERS, [players_df.columns.tolist()] + players_df.values.tolist())
            
            # 4. Update Scores sheet with individual match points
            scores_df = self.read_sheet(config.SHEET_SCORES)
            
            # Create new scores data
            new_scores = []
            for player, points in zip(team1_players + team2_players, 
                                    [team1_points]*2 + [team2_points]*2):
                new_scores.append([match_id, player, points])
            
            new_scores_df = pd.DataFrame(new_scores, columns=[config.COL_MATCH_ID, config.COL_NAME, config.COL_TOTAL_POINTS])
            
            # Ensure data types match before concatenation
            for col in scores_df.columns:
                new_scores_df[col] = new_scores_df[col].astype(scores_df[col].dtype)
            
            scores_df = pd.concat([scores_df, new_scores_df], ignore_index=True)
            self.update_sheet(config.SHEET_SCORES, [scores_df.columns.tolist()] + scores_df.values.tolist())
            
            return True
        except Exception as e:
            print(f"Error updating match score: {str(e)}")
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

    def get_available_courts(self):
        """Get list of available courts."""
        courts_df = self.read_sheet(config.SHEET_COURTS)
        if courts_df.empty:
            return pd.DataFrame()
        return courts_df

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
        try:
            # Read existing players
            players_df = self.read_sheet(config.SHEET_PLAYERS)
            
            # Check if player already exists
            if not players_df.empty and player_name in players_df[config.COL_NAME].values:
                return False, f"Player '{player_name}' already exists"
            
            # Create new player row
            new_player = {
                config.COL_NAME: player_name,
                config.COL_STATUS: config.STATUS_ACTIVE,
                config.COL_GENDER: "W" if is_woman else "",
                config.COL_TOTAL_POINTS: 0,
                config.COL_GAMES_PLAYED: 0,
                config.COL_CHECK_IN_TIME: "",
                config.COL_LAST_MATCH_TIME: "",
                config.COL_AVG_POINTS: 0
            }
            
            # Append new player
            players_df = pd.concat([players_df, pd.DataFrame([new_player])], ignore_index=True)
            
            # Update sheet
            self.update_sheet(config.SHEET_PLAYERS, [players_df.columns.tolist()] + players_df.values.tolist())
            
            return True, f"Successfully added player '{player_name}'"
        except Exception as e:
            return False, f"Error adding player: {str(e)}"

    def generate_next_matches(self, active_players, court_count):
        """Generate optimal matches based on player history"""
        # Get existing matches to check who has played together
        matches_df = self.read_sheet(config.SHEET_MATCHES)
        
        # Create matrices to track playing with and against separately
        partner_matrix = pd.DataFrame(0.0, index=active_players, columns=active_players, dtype=float)
        opponent_matrix = pd.DataFrame(0.0, index=active_players, columns=active_players, dtype=float)
        games_played = pd.Series(0, index=active_players)
        
        # Weight recent matches more heavily using exponential decay
        total_matches = len(matches_df)
        for idx, match in matches_df.iterrows():
            # More recent matches have higher weight (between 0.5 and 1.0)
            recency_weight = 0.5 + 0.5 * (idx + 1) / total_matches
            
            team1 = [match[config.COL_TEAM1_PLAYER1], match[config.COL_TEAM1_PLAYER2]]
            team2 = [match[config.COL_TEAM2_PLAYER1], match[config.COL_TEAM2_PLAYER2]]
            
            # Update games played count
            for player in team1 + team2:
                if player in active_players:
                    games_played[player] += 1
            
            # Update partner counts
            for team in [team1, team2]:
                if team[0] in active_players and team[1] in active_players:
                    partner_matrix.loc[team[0], team[1]] += recency_weight
                    partner_matrix.loc[team[1], team[0]] += recency_weight
            
            # Update opponent counts
            for p1 in team1:
                for p2 in team2:
                    if p1 in active_players and p2 in active_players:
                        opponent_matrix.loc[p1, p2] += recency_weight
                        opponent_matrix.loc[p2, p1] += recency_weight
        
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
        
        # Remove busy players from available players
        available_players = [p for p in active_players if p not in busy_players]
        
        # Generate matches
        matches = []
        max_partner_count = 2  # Maximum times players can be paired together
        min_games = games_played.min()
        max_games = games_played.max()
        
        # Hard cap: no player should play more than min_games + 1 until everyone has played min_games
        max_allowed_games = min_games + (1 if all(games_played >= min_games) else 0)
        
        while len(available_players) >= 4:
            # Filter out players who have reached the hard cap
            eligible_players = [p for p in available_players if games_played[p] < max_allowed_games]
            if not eligible_players:
                # If no eligible players, reset max_allowed_games
                max_allowed_games += 1
                eligible_players = available_players
            
            # Among eligible players, find those who have played the least
            min_eligible_games = min(games_played[p] for p in eligible_players)
            least_played = [p for p in eligible_players if games_played[p] == min_eligible_games]
            
            # Randomly select from the least played players
            player1 = random.choice(least_played)
            available_players.remove(player1)
            
            # Find potential partners (who haven't reached game limit)
            potential_partners = [p for p in available_players 
                                if partner_matrix.loc[player1, p] < max_partner_count
                                and games_played[p] < max_allowed_games]
            
            if not potential_partners:  # If no partners under constraints, relax game count
                potential_partners = [p for p in available_players 
                                   if partner_matrix.loc[player1, p] < max_partner_count]
            
            if not potential_partners:  # If still none, use all available
                potential_partners = available_players.copy()
            
            # Get the minimum games played among potential partners
            min_partner_games = min(games_played[p] for p in potential_partners)
            best_partners = [p for p in potential_partners 
                            if games_played[p] == min_partner_games
                            and partner_matrix.loc[player1, p] == min(partner_matrix.loc[player1, potential_partners])]
            
            # Randomly select from best partners
            partner = random.choice(best_partners)
            available_players.remove(partner)
            
            # Find opponents (who haven't reached game limit)
            potential_opponents = [p for p in available_players 
                                 if games_played[p] < max_allowed_games]
            if not potential_opponents:
                potential_opponents = available_players.copy()
            
            # Get minimum games among potential opponents
            min_opponent_games = min(games_played[p] for p in potential_opponents)
            best_opponents = [p for p in potential_opponents 
                             if games_played[p] == min_opponent_games]
            
            # Randomly select first opponent from best options
            opponent1 = random.choice(best_opponents)
            available_players.remove(opponent1)
            
            # Repeat for second opponent
            potential_opponents = [p for p in available_players 
                                 if games_played[p] < max_allowed_games]
            if not potential_opponents:
                potential_opponents = available_players.copy()
            
            min_opponent_games = min(games_played[p] for p in potential_opponents)
            best_opponents = [p for p in potential_opponents 
                             if games_played[p] == min_opponent_games]
            
            opponent2 = random.choice(best_opponents)
            available_players.remove(opponent2)
            
            # Get next match ID
            match_id_pattern = r'M(\d+)'
            existing_match_ids = matches_df[config.COL_MATCH_ID].str.extract(match_id_pattern, expand=False).astype(float)
            next_match_id = int(existing_match_ids.max() + 1) if not existing_match_ids.empty else 1
            
            # Also check IDs in current batch of matches
            if matches:
                batch_ids = pd.Series([m[config.COL_MATCH_ID] for m in matches]).str.extract(match_id_pattern, expand=False).astype(float)
                if not batch_ids.empty:
                    next_match_id = max(next_match_id, int(batch_ids.max() + 1))

            # Ensure this ID doesn't exist in any matches (including cancelled ones)
            while f"M{next_match_id}" in matches_df[config.COL_MATCH_ID].values or \
                  any(m[config.COL_MATCH_ID] == f"M{next_match_id}" for m in matches):
                next_match_id += 1

            match = {
                config.COL_MATCH_ID: f"M{next_match_id}",
                config.COL_COURT_NUMBER: "",  # Will be assigned if courts available
                config.COL_TEAM1_PLAYER1: player1,
                config.COL_TEAM1_PLAYER2: partner,
                config.COL_TEAM2_PLAYER1: opponent1,
                config.COL_TEAM2_PLAYER2: opponent2,
                config.COL_MATCH_STATUS: config.STATUS_PENDING,
                config.COL_START_TIME: "",
                config.COL_END_TIME: "",
                config.COL_TEAM1_SCORE: "",
                config.COL_TEAM2_SCORE: ""
            }
            matches.append(match)
            
            # Update games played for next iteration
            for player in [player1, partner, opponent1, opponent2]:
                games_played[player] += 1
            
            # Update minimum games and max allowed games
            min_games = games_played[available_players].min() if available_players else 0
            max_allowed_games = min_games + (1 if all(games_played >= min_games) else 0)
            
            if len(matches) >= court_count * 3:  # Generate up to 3x the number of courts
                break

        if matches:
            # Check for available courts
            matches_df = self.read_sheet(config.SHEET_MATCHES)
            courts_df = self.read_sheet(config.SHEET_COURTS)
            
            # Get courts that have active or scheduled matches
            busy_courts = matches_df[
                matches_df[config.COL_MATCH_STATUS].isin([config.STATUS_SCHEDULED, config.STATUS_IN_PROGRESS])
            ][config.COL_COURT_NUMBER].unique()
            
            # Get available courts (including empty strings and NaN)
            available_courts = courts_df[
                ~courts_df[config.COL_COURT_NUMBER].isin(busy_courts)
            ][config.COL_COURT_NUMBER].tolist()
            
            # Get pending matches in order
            pending_matches = matches_df[
                matches_df[config.COL_MATCH_STATUS] == config.STATUS_PENDING
            ].sort_values(by=config.COL_MATCH_ID)
            
            # Combine pending matches with new matches
            all_matches = list(pending_matches.to_dict('records')) + matches
            
            # Assign available courts to matches in order
            for i, match in enumerate(all_matches):
                if i < len(available_courts):
                    match[config.COL_COURT_NUMBER] = available_courts[i]
                    match[config.COL_MATCH_STATUS] = config.STATUS_SCHEDULED
            
            # Add matches to sheet
            matches_df = pd.concat([
                matches_df[~matches_df[config.COL_MATCH_ID].isin([m[config.COL_MATCH_ID] for m in all_matches])],
                pd.DataFrame(all_matches)
            ], ignore_index=True)
            
            self.update_sheet(config.SHEET_MATCHES, [matches_df.columns.tolist()] + matches_df.values.tolist())
            return matches
        
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
                
            # Get the court number if it was assigned
            cancelled_court = matches_df.loc[match_idx[0], config.COL_COURT_NUMBER]
            
            # Remove the match
            matches_df = matches_df.drop(match_idx)
            
            # If court was assigned, try to assign next pending match
            if cancelled_court:
                # Get next pending match
                pending_matches = matches_df[matches_df[config.COL_MATCH_STATUS] == config.STATUS_PENDING]
                if not pending_matches.empty:
                    next_match = pending_matches.iloc[0]
                    next_match_idx = pending_matches.index[0]
                    
                    # Assign court to next match
                    matches_df.loc[next_match_idx, config.COL_COURT_NUMBER] = cancelled_court
                    matches_df.loc[next_match_idx, config.COL_MATCH_STATUS] = config.STATUS_SCHEDULED
            
            # Update sheet
            self.update_sheet(config.SHEET_MATCHES, [matches_df.columns.tolist()] + matches_df.values.tolist())
            return True, "Match cancelled successfully"
            
        except Exception as e:
            print(f"Error cancelling match: {str(e)}")
            return False, f"Error cancelling match: {str(e)}"

    def handle_player_inactivation(self, player_name):
        """Handle matches when a player is marked as inactive."""
        matches_df = self.read_sheet(config.SHEET_MATCHES)
        
        # Find matches involving the player
        player_matches = matches_df[
            ((matches_df[config.COL_TEAM1_PLAYER1] == player_name) |
             (matches_df[config.COL_TEAM1_PLAYER2] == player_name) |
             (matches_df[config.COL_TEAM2_PLAYER1] == player_name) |
             (matches_df[config.COL_TEAM2_PLAYER2] == player_name)) &
            (matches_df[config.COL_MATCH_STATUS].isin([config.STATUS_SCHEDULED, config.STATUS_PENDING]))
        ]
        
        if player_matches.empty:
            return None, None
        
        # Separate current (on court) and scheduled (pending) matches
        current_matches = player_matches[
            (player_matches[config.COL_MATCH_STATUS] == config.STATUS_SCHEDULED) &
            (player_matches[config.COL_COURT_NUMBER] != "")
        ]
        scheduled_matches = player_matches[
            (player_matches[config.COL_MATCH_STATUS] == config.STATUS_PENDING) |
            ((player_matches[config.COL_MATCH_STATUS] == config.STATUS_SCHEDULED) &
             (player_matches[config.COL_COURT_NUMBER] == ""))
        ]
        
        return current_matches, scheduled_matches

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
