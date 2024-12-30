import pandas as pd

class CSVManager:
    def __init__(self):
        self.urls = {
            'players': 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTKnPg-np8V_1ytXq5HkMXg4bJiOHE0S8A8h18-hTlxrwun4yEfIXxt5bE2ks8MZjXS1gck-6OIG0ox/pub?gid=1330314038&single=true&output=csv',
            'matches': 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTKnPg-np8V_1ytXq5HkMXg4bJiOHE0S8A8h18-hTlxrwun4yEfIXxt5bE2ks8MZjXS1gck-6OIG0ox/pub?gid=2141367686&single=true&output=csv',
            'scores': 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTKnPg-np8V_1ytXq5HkMXg4bJiOHE0S8A8h18-hTlxrwun4yEfIXxt5bE2ks8MZjXS1gck-6OIG0ox/pub?gid=1595320677&single=true&output=csv'
        }
        
    def read_sheet(self, sheet_name):
        """Read data from CSV URL based on sheet name."""
        try:
            url = self.urls.get(sheet_name.lower())
            if not url:
                raise ValueError(f"Unknown sheet name: {sheet_name}")
            
            df = pd.read_csv(url)
            return df
        except Exception as e:
            print(f"Error reading CSV data: {str(e)}")
            return pd.DataFrame()  # Return empty DataFrame on error
