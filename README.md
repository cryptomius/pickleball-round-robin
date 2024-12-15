# Pickleball Round Robin Tournament Coordinator

A Streamlit-based system for managing pickleball round robin tournaments, featuring fair play mechanics and real-time tournament tracking.

## Features

### Player App (`player_app.py`)
- View current and upcoming matches
- Submit match scores
- Track personal performance and standings
- Simple interface for players to focus on the game

### Coordinator App
1. **Player Management**
   - Add and manage players with status tracking
   - Mark players as women for separate standings
   - Track check-in times and participation
   - Toggle player active/inactive status

2. **Match Management**
   - Automatic match generation with fair play balancing
   - Court assignment and management
   - Score submission and verification
   - Match cancellation with automatic court reassignment
   - Real-time match status tracking

3. **Tournament Summary**
   - Overall tournament statistics
   - Sortable standings by total or average points
   - Separate women's standings
   - Real-time performance tracking
   - Game participation metrics

## Fair Play Mechanisms

1. **Equal Play Opportunity**
   - Tracks games played for each player
   - Prioritizes players with fewer games
   - Ensures balanced participation across the tournament

2. **Partner/Opponent Balancing**
   - Avoids repeated partnerships
   - Distributes opponents fairly
   - Weighted history to prevent immediate rematches

3. **Court Assignment**
   - Automatic court rotation
   - Efficient use of available courts
   - Continuous play management

4. **Scoring System**
   - Base points for participation
   - Win/loss points
   - Bonus points for point differential
   - Average points per game tracking

## Setup Instructions

1. Create a Google Cloud Project:
   - Enable Google Sheets API
   - Create service account credentials
   - Share your tournament spreadsheet with the service account email

2. Local Development:
   - Create `.streamlit/secrets.toml` with your Google credentials
   - Install requirements: `pip install -r requirements.txt`
   - Run coordinator: `streamlit run coordinator/Home.py`
   - Run player app: `streamlit run player_app.py`

3. Deployment (Streamlit Cloud):
   - Push code to GitHub (credentials.json excluded)
   - Connect repository to Streamlit Cloud
   - Add Google credentials to Streamlit Cloud secrets
   - Deploy both coordinator and player apps

## Recent Updates

1. **Player Management**
   - Added gender tracking for women players
   - Enhanced player status management
   - Improved check-in time tracking

2. **Match Management**
   - Added match cancellation feature
   - Improved score submission validation
   - Automatic court reassignment after matches

3. **Tournament Summary**
   - Added separate women's standings
   - Enhanced sorting options
   - Improved points display formatting
   - Added real-time tournament metrics

## Dependencies
- streamlit
- pandas
- google-auth
- google-auth-oauthlib
- google-auth-httplib2
- google-api-python-client
- extra-streamlit-components

## Sheet Structure
1. **Players**
   - Player Name
   - Status (Active/Inactive)
   - Gender (W for women)
   - Total Points
   - Games Played
   - Check-in Time
   - Last Match Time
   - Average Points Per Game

2. **Matches**
   - Match ID
   - Court Number
   - Team 1 & 2 Players
   - Start/End Times
   - Scores
   - Match Status

3. **Courts**
   - Court assignments and availability

## Contributing
Feel free to submit issues and enhancement requests!
