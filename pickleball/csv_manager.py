import pandas as pd
import requests
import io
import logging
import urllib3
import warnings

# Suppress SSL verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class CSVManager:
    def __init__(self):
        self.urls = {
            'players': 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTKnPg-np8V_1ytXq5HkMXg4bJiOHE0S8A8h18-hTlxrwun4yEfIXxt5bE2ks8MZjXS1gck-6OIG0ox/pub?gid=1330314038&single=true&output=csv',
            'matches': 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTKnPg-np8V_1ytXq5HkMXg4bJiOHE0S8A8h18-hTlxrwun4yEfIXxt5bE2ks8MZjXS1gck-6OIG0ox/pub?gid=2141367686&single=true&output=csv',
            'scores': 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTKnPg-np8V_1ytXq5HkMXg4bJiOHE0S8A8h18-hTlxrwun4yEfIXxt5bE2ks8MZjXS1gck-6OIG0ox/pub?gid=1595320677&single=true&output=csv'
        }
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def read_sheet(self, sheet_name):
        """Read data from CSV URL based on sheet name."""
        try:
            url = self.urls.get(sheet_name.lower())
            if not url:
                raise ValueError(f"Unknown sheet name: {sheet_name}")
            
            # Use requests to get the CSV data with SSL verification disabled
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                response = requests.get(url, verify=False)
            response.raise_for_status()  # Raise an exception for bad status codes
            
            # Read CSV data from the response content
            df = pd.read_csv(io.StringIO(response.text))
            self.logger.info(f"Successfully read sheet {sheet_name}. Columns: {df.columns.tolist()}")
            return df
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching CSV data: {str(e)}")
            return pd.DataFrame()
        except Exception as e:
            self.logger.error(f"Error reading CSV data: {str(e)}")
            return pd.DataFrame()
