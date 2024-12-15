from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
import pandas as pd
from datetime import datetime
import config

class SheetsManager:
    def __init__(self):
        self.creds = service_account.Credentials.from_service_account_file(
            config.CREDENTIALS_FILE, scopes=config.SCOPES
        )
        self.service = build('sheets', 'v4', credentials=self.creds)
        self.sheet = self.service.spreadsheets()
        self._last_modified = {}  # Track last modified time for each sheet

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
                    config.COL_TOTAL_POINTS,
                    config.COL_GAMES_PLAYED,
                    config.COL_CHECK_IN_TIME,
                    config.COL_LAST_MATCH_TIME
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
                config.COL_TOTAL_POINTS,
                config.COL_GAMES_PLAYED,
                config.COL_CHECK_IN_TIME,
                config.COL_LAST_MATCH_TIME
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
        try:
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
        try:
            matches_df = self.read_sheet(config.SHEET_MATCHES)
            match_row = matches_df[matches_df[config.COL_MATCH_ID] == match_id].iloc[0]
            
            # Update match scores
            matches_df.loc[matches_df[config.COL_MATCH_ID] == match_id, [config.COL_TEAM1_SCORE, config.COL_TEAM2_SCORE]] = [team1_score, team2_score]
            self.update_sheet(config.SHEET_MATCHES, [matches_df.columns.tolist()] + matches_df.values.tolist())
            
            # Calculate points based on scores
            score_diff = abs(team1_score - team2_score)
            bonus_points = min(score_diff * config.BONUS_POINT_PER_DIFF, config.MAX_BONUS_POINTS)
            
            if team1_score > team2_score:
                team1_points = config.POINTS_WIN + bonus_points  # Win points (2) + bonus
                team2_points = config.POINTS_LOSS               # Loss points (1)
            else:
                team1_points = config.POINTS_LOSS               # Loss points (1)
                team2_points = config.POINTS_WIN + bonus_points  # Win points (2) + bonus
            
            # Update players sheet with total points and games played
            players_df = self.read_sheet(config.SHEET_PLAYERS)
            
            # Get player names
            team1_players = [match_row[config.COL_TEAM1_PLAYER1], match_row[config.COL_TEAM1_PLAYER2]]
            team2_players = [match_row[config.COL_TEAM2_PLAYER1], match_row[config.COL_TEAM2_PLAYER2]]
            
            # Update each player's total points and games played
            for player in team1_players:
                current_points = players_df.loc[players_df[config.COL_NAME] == player, config.COL_TOTAL_POINTS].iloc[0]
                current_games = players_df.loc[players_df[config.COL_NAME] == player, config.COL_GAMES_PLAYED].iloc[0]
                
                if pd.isna(current_points) or current_points == '':
                    current_points = 0
                if pd.isna(current_games) or current_games == '':
                    current_games = 0
                    
                new_points = float(current_points) + team1_points
                new_games = int(current_games) + 1
                
                players_df.loc[players_df[config.COL_NAME] == player, config.COL_TOTAL_POINTS] = new_points
                players_df.loc[players_df[config.COL_NAME] == player, config.COL_GAMES_PLAYED] = new_games
                players_df.loc[players_df[config.COL_NAME] == player, config.COL_LAST_MATCH_TIME] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            for player in team2_players:
                current_points = players_df.loc[players_df[config.COL_NAME] == player, config.COL_TOTAL_POINTS].iloc[0]
                current_games = players_df.loc[players_df[config.COL_NAME] == player, config.COL_GAMES_PLAYED].iloc[0]
                
                if pd.isna(current_points) or current_points == '':
                    current_points = 0
                if pd.isna(current_games) or current_games == '':
                    current_games = 0
                    
                new_points = float(current_points) + team2_points
                new_games = int(current_games) + 1
                
                players_df.loc[players_df[config.COL_NAME] == player, config.COL_TOTAL_POINTS] = new_points
                players_df.loc[players_df[config.COL_NAME] == player, config.COL_GAMES_PLAYED] = new_games
                players_df.loc[players_df[config.COL_NAME] == player, config.COL_LAST_MATCH_TIME] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            self.update_sheet(config.SHEET_PLAYERS, [players_df.columns.tolist()] + players_df.values.tolist())
            
            # Return data for scores sheet update
            return [[match_id, player, team1_points] for player in team1_players] + \
                   [[match_id, player, team2_points] for player in team2_players]
        except Exception as e:
            print(f"Error updating match score: {str(e)}")
            return None

    def get_active_players(self):
        df = self.read_sheet(config.SHEET_PLAYERS)
        # Consider players active if their status is explicitly active or blank/empty
        return df[(df[config.COL_STATUS] == config.STATUS_ACTIVE) | 
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
        """Get list of available courts"""
        courts_df = self.read_sheet(config.SHEET_COURTS)
        return courts_df[courts_df[config.COL_STATUS] == config.STATUS_COURT_ACTIVE]

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
        if status not in [config.STATUS_ACTIVE, config.STATUS_INACTIVE]:
            raise ValueError(f"Invalid status: {status}")
        
        players_df = self.read_sheet(config.SHEET_PLAYERS)
        player_idx = players_df[players_df[config.COL_NAME] == player_name].index[0]
        players_df.at[player_idx, config.COL_STATUS] = status
        
        # Update the sheet
        self.update_sheet(config.SHEET_PLAYERS, [players_df.columns.tolist()] + players_df.values.tolist())
