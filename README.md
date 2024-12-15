# Pickleball Round Robin Tournament Manager

A tournament management system for Lakes Entrance Pickleball Club's round-robin competition. The system ensures fair play through optimized match generation and balanced scoring.

## Features

### Player App
- View your current and completed matches
- Submit match scores for your games
- Track your total points and games played
- See your current match court assignment
- View your team members and opponents

### Coordinator App
1. **Player Management**
   - Add/remove players
   - Track player check-in/out status
   - Monitor player participation

2. **Match Management**
   - Real-time court status overview
   - Generate balanced matches automatically
   - Submit and track match scores
   - Cancel matches if needed
   - View pending matches queue

3. **Tournament Summary**
   - Real-time leaderboard
   - Sort by total points or average points per game
   - Track total games completed
   - Monitor player statistics

## Fair Play Mechanisms

### Match Generation
The system ensures fair play through several mechanisms:

1. **Equal Play Opportunity**
   - Tracks games played for each player
   - Players with fewer games are prioritized in match generation
   - Hard cap ensures no player plays more than one game ahead of others

2. **Partner/Opponent Balancing**
   - Maintains history of partnerships and opponents
   - Uses weighted scoring to avoid repeated partnerships
   - Considers recent matches more heavily than older ones
   - Maximum partner count prevents playing with the same person too often

3. **Court Assignment**
   - Automatic court assignment for new matches
   - When a match finishes or is cancelled, the next pending match is automatically assigned
   - Ensures continuous play across all courts

### Scoring System
1. **Base Points**
   - Winning team: 2 points per player
   - Losing team: 1 point per player

2. **Bonus Points**
   - 0.1 points per point difference
   - Maximum bonus of 1.0 points
   - Encourages competitive play while preventing excessive score differences

3. **Statistics**
   - Tracks total points and games played
   - Calculates average points per game
   - Allows sorting by either metric for different perspectives on performance

## Deployment to Streamlit Cloud

1. **Create a GitHub Repository**
   - Create a new repository for the project
   - Add `.gitignore` to exclude `credentials.json`
   - Push code to repository

2. **Prepare Credentials**
   - Open your `credentials.json` file
   - Copy the entire contents
   - Convert to a single line (remove newlines)

3. **Set Up Streamlit Cloud**
   - Connect your GitHub repository to Streamlit Cloud
   - In app settings, add the following secret:
     - Key: `GOOGLE_CREDENTIALS_JSON`
     - Value: [Your credentials.json contents as a single line]

4. **Deploy Apps**
   - Deploy both coordinator and player apps
   - Each will use the same credentials from environment variables
   - Local development will still use `credentials.json` file

## Setup Instructions

1. Create a Google Cloud Project and enable Google Sheets API
2. Create service account credentials and download JSON key
3. Create a Google Sheet with the following structure:
   - Players
   - Matches
   - Courts
   - Scores

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

## Sheet Structure

### Players Sheet
- Player Name
- Status (Active/Inactive)
- Total Points
- Games Played
- Average Points per Game
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
- Match Status (Pending/Scheduled/In Progress/Completed)

### Courts Sheet
- Court Number
- Status
- Current Match ID

### Scores Sheet
- Match ID
- Player Name
- Points Earned

## Recent Updates
1. **Match Management**
   - Added match cancellation feature
   - Improved court reassignment logic
   - Fixed duplicate match ID issues

2. **Player Management**
   - Enhanced player addition with error handling
   - Added check-in time tracking
   - Improved status management

3. **Tournament Summary**
   - Added sorting options (total/average points)
   - Improved points display formatting
   - Added games completed counter

4. **Score Submission**
   - Unified scoring logic between coordinator and player apps
   - Enhanced error handling and validation
   - Added automatic court reassignment after match completion
