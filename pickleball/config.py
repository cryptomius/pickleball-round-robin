import os

# Tournament Settings
COURTS_COUNT = 6

# Scoring System
POINTS_WIN = 2
POINTS_LOSS = 1
BONUS_POINT_PER_DIFF = 0.1
MAX_BONUS_POINTS = 1.0
MIN_GAMES_FOR_RANKING = 3  # Minimum number of games required to be ranked in standings

# Google Sheets Configuration
SPREADSHEET_ID = "1_ga5oUPky7iEBf88KiBjMoCAr4-5eY-DZPuLRRCL86Y"  # To be filled with your Google Sheet ID
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Sheet Names
SHEET_PLAYERS = "Players"
SHEET_MATCHES = "Matches"
SHEET_SCORES = "Scores"

# Column Names
# Players Sheet
COL_NAME = "Player Name"
COL_STATUS = "Status"
COL_GENDER = "Gender"  # New column for gender
COL_TOTAL_POINTS = "Total Points"
COL_GAMES_PLAYED = "Games Played"
COL_CHECK_IN_TIME = "Check-in Time"
COL_LAST_MATCH_TIME = "Last Match Time"
COL_AVG_POINTS = "Average Points Per Game"

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
COL_MATCH_TYPE = "Match Type"  # New column for match type

# Status Values
STATUS_ACTIVE = "Active"
STATUS_INACTIVE = "Inactive"

# Gender Values
GENDER_MALE = "M"
GENDER_FEMALE = "F"

# Match Types
MATCH_TYPE_MENS = "Mens"
MATCH_TYPE_WOMENS = "Womens"
MATCH_TYPE_MIXED = "Mixed"

# Player Status Values
STATUS_PLAYER_ACTIVE = "Active"
STATUS_PLAYER_INACTIVE = "Inactive"

# Match Status Values
STATUS_PENDING = "Pending"
STATUS_SCHEDULED = "Scheduled"
STATUS_IN_PROGRESS = "In Progress"
STATUS_COMPLETED = "Completed"
STATUS_CANCELLED = "Cancelled"

# Scores Sheet
COL_POINTS = "Points"
