# Pickleball Round Robin Tournament Manager

A tournament management system for Lakes Entrance Pickleball Club's round-robin competition.

## Features

- **Player App:**
  - View current and upcoming matches
  - Report match scores
  - Easy player check-in/out
  - Court assignments
  - Partner and opponent information

- **Coordinator App:**
  - Real-time leaderboard
  - Court status monitoring
  - Match scheduling optimization
  - Player participation tracking
  - Tournament management

## Setup Instructions

1. Create a Google Cloud Project and enable Google Sheets API
2. Create service account credentials and download JSON key
3. Create a Google Sheet with the following structure:
   - Players
   - Matches
   - Courts
   - Scores
   - Settings

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Run the apps:
```bash
# For Players
streamlit run player_app.py

# For Coordinators
streamlit run coordinator_app.py
```

## Google Sheets Structure

### Players Sheet
- Player Name
- Status (Active/Inactive)
- Total Points
- Games Played
- Check-in Time
- Last Match Time

### Matches Sheet
- Match ID
- Court Number
- Team 1 - Player 1
- Team 1 - Player 2
- Team 2 - Player 1
- Team 2 - Player 2
- Start Time
- End Time
- Team 1 Score
- Team 2 Score
- Match Status (Scheduled/In Progress/Completed)

### Courts Sheet
- Court Number
- Status (Active/Inactive)
- Current Match ID

### Scores Sheet
- Match ID
- Player Name
- Total Points

### Settings Sheet
- Tournament Date: 2025-01-03
- Start Time: 10:00
- Lunch Start: 12:00
- Lunch Duration: 60
- Max Duration: 360
- Courts Count: 6
- Points Win: 2
- Points Loss: 1
- Bonus Point Per Diff: 0.1
- Max Bonus Points: 1.0

## Scoring System
- Winning team: 2 points per player
- Losing team: 1 point per player
- Bonus points: 0.1 per point difference (max 1.0)

## Tournament Details
- Date: January 3rd, 2025
- Time: 10:00 AM - 4:00 PM
- Lunch Break: 12:00 PM - 1:00 PM
- Courts: 6
- Expected Players: ~40
