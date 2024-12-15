from google.oauth2 import service_account
from googleapiclient.discovery import build
import config

def initialize_sheets():
    # Set up credentials and service
    creds = service_account.Credentials.from_service_account_file(
        config.CREDENTIALS_FILE, scopes=config.SCOPES
    )
    service = build('sheets', 'v4', credentials=creds)
    sheets = service.spreadsheets()

    # First, create the sheets if they don't exist
    try:
        spreadsheet = sheets.get(spreadsheetId=config.SPREADSHEET_ID).execute()
        existing_sheets = [sheet['properties']['title'] for sheet in spreadsheet['sheets']]
        
        # Define the sheets we need
        required_sheets = ["Players", "Matches", "Courts", "Scores", "Settings"]
        
        # Create any missing sheets
        requests = []
        for sheet_name in required_sheets:
            if sheet_name not in existing_sheets:
                requests.append({
                    "addSheet": {
                        "properties": {
                            "title": sheet_name
                        }
                    }
                })
        
        if requests:
            sheets.batchUpdate(
                spreadsheetId=config.SPREADSHEET_ID,
                body={"requests": requests}
            ).execute()
            print(f"Created sheets: {[req['addSheet']['properties']['title'] for req in requests]}")
    
        # Initialize each sheet with headers
        players_headers = [
            [config.COL_NAME, config.COL_STATUS, config.COL_TOTAL_POINTS,
             config.COL_GAMES_PLAYED, config.COL_CHECK_IN_TIME, config.COL_LAST_MATCH_TIME]
        ]

        matches_headers = [
            [config.COL_MATCH_ID, config.COL_COURT_NUMBER,
             config.COL_TEAM1_PLAYER1, config.COL_TEAM1_PLAYER2,
             config.COL_TEAM2_PLAYER1, config.COL_TEAM2_PLAYER2,
             config.COL_START_TIME, config.COL_END_TIME,
             config.COL_TEAM1_SCORE, config.COL_TEAM2_SCORE,
             config.COL_MATCH_STATUS]
        ]

        courts_headers = [
            [config.COL_COURT_NUMBER, config.COL_STATUS, config.COL_MATCH_ID]
        ]
        
        # Initialize courts data with 6 courts
        courts_data = [
            [f"Court {i}", config.STATUS_COURT_ACTIVE, ""] for i in range(1, 7)
        ]

        scores_headers = [
            ["Match ID", "Player Name", "Total Points"]
        ]

        settings_data = [
            ["Setting", "Value"],
            ["Tournament Date", "2025-01-03"],
            ["Start Time", "10:00"],
            ["Lunch Start", "12:00"],
            ["Lunch Duration", "60"],
            ["Max Duration", "360"],
            ["Courts Count", "6"],
            ["Points Win", "2"],
            ["Points Loss", "1"],
            ["Bonus Point Per Diff", "0.1"],
            ["Max Bonus Points", "1.0"]
        ]

        # Update each sheet
        sheets.values().update(
            spreadsheetId=config.SPREADSHEET_ID,
            range="Players!A1",
            valueInputOption="RAW",
            body={"values": players_headers}
        ).execute()

        sheets.values().update(
            spreadsheetId=config.SPREADSHEET_ID,
            range="Matches!A1",
            valueInputOption="RAW",
            body={"values": matches_headers}
        ).execute()

        sheets.values().update(
            spreadsheetId=config.SPREADSHEET_ID,
            range="Courts!A1",
            valueInputOption="RAW",
            body={"values": courts_headers + courts_data}
        ).execute()

        sheets.values().update(
            spreadsheetId=config.SPREADSHEET_ID,
            range="Scores!A1",
            valueInputOption="RAW",
            body={"values": scores_headers}
        ).execute()

        sheets.values().update(
            spreadsheetId=config.SPREADSHEET_ID,
            range="Settings!A1",
            valueInputOption="RAW",
            body={"values": settings_data}
        ).execute()

        # Format headers (make them bold and freeze them)
        format_requests = []
        for sheet_name in required_sheets:
            sheet_id = get_sheet_id(sheets, config.SPREADSHEET_ID, sheet_name)
            if sheet_id is not None:
                format_requests.append({
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 0,
                            "endRowIndex": 1
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {
                                    "red": 0.9,
                                    "green": 0.9,
                                    "blue": 0.9
                                },
                                "textFormat": {
                                    "bold": True
                                }
                            }
                        },
                        "fields": "userEnteredFormat(backgroundColor,textFormat)"
                    }
                })
                
                # Freeze the header row
                format_requests.append({
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": sheet_id,
                            "gridProperties": {
                                "frozenRowCount": 1
                            }
                        },
                        "fields": "gridProperties.frozenRowCount"
                    }
                })

        if format_requests:
            sheets.batchUpdate(
                spreadsheetId=config.SPREADSHEET_ID,
                body={"requests": format_requests}
            ).execute()

        print("Successfully initialized all sheets!")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise

def get_sheet_id(sheets, spreadsheet_id, sheet_name):
    spreadsheet = sheets.get(spreadsheetId=spreadsheet_id).execute()
    for sheet in spreadsheet['sheets']:
        if sheet['properties']['title'] == sheet_name:
            return sheet['properties']['sheetId']
    return None

if __name__ == "__main__":
    initialize_sheets()