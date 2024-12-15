import os
from datetime import datetime, time

# Tournament Settings
TOURNAMENT_DATE = datetime(2025, 1, 3)
START_TIME = time(10, 0)
LUNCH_START = time(12, 0)
LUNCH_DURATION = 60  # minutes
MAX_DURATION = 360  # minutes (6 hours)
COURTS_COUNT = 6

# Scoring System
POINTS_WIN = 2
POINTS_LOSS = 1
BONUS_POINT_PER_DIFF = 0.1
MAX_BONUS_POINTS = 1.0

# Google Sheets Configuration
SPREADSHEET_ID = "1_ga5oUPky7iEBf88KiBjMoCAr4-5eY-DZPuLRRCL86Y"  # To be filled with your Google Sheet ID
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
CREDENTIALS_FILE = "credentials.json"  # Place your Google Sheets API credentials here

# Sheet Names
SHEET_PLAYERS = "Players"
SHEET_MATCHES = "Matches"
SHEET_COURTS = "Courts"
SHEET_SCORES = "Scores"
SHEET_SETTINGS = "Settings"

# Column Names
# Players Sheet
COL_NAME = "Player Name"
COL_STATUS = "Status"
COL_TOTAL_POINTS = "Total Points"
COL_GAMES_PLAYED = "Games Played"
COL_CHECK_IN_TIME = "Check-in Time"
COL_LAST_MATCH_TIME = "Last Match Time"

# Matches Sheet
COL_MATCH_ID = "Match ID"
COL_COURT_NUMBER = "Court Number"
COL_TEAM1_PLAYER1 = "Team 1 - Player 1"
COL_TEAM1_PLAYER2 = "Team 1 - Player 2"
COL_TEAM2_PLAYER1 = "Team 2 - Player 1"
COL_TEAM2_PLAYER2 = "Team 2 - Player 2"
COL_START_TIME = "Start Time"
COL_END_TIME = "End Time"
COL_TEAM1_SCORE = "Team 1 Score"
COL_TEAM2_SCORE = "Team 2 Score"
COL_MATCH_STATUS = "Match Status"

# Courts Sheet
COL_COURT_NUMBER = "Court Number"
COL_STATUS = "Status"
COL_MATCH_ID = "Match ID"

# Status Values
# Match Status Values
STATUS_SCHEDULED = "Scheduled"
STATUS_IN_PROGRESS = "In Progress"
STATUS_COMPLETED = "Completed"
STATUS_CANCELLED = "Cancelled"

# Player Status Values
STATUS_ACTIVE = "Active"
STATUS_INACTIVE = "Inactive"

# Court Status Values
STATUS_COURT_ACTIVE = "Active"
STATUS_COURT_INACTIVE = "Inactive"
