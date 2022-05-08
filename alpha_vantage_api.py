"""EE 250L Final Project

Team members:
Humberto Inzunza Velarde
Saif Azimi

Github Repository:
https://github.com/sazimi13/ee250-final
"""
import requests

class AlphaVantageAPI:

    endpoint = 'https://www.alphavantage.co/query'
    AV_API_KEY = 'I73NFDXTSF4A9DNO'

    def __init__(self):
        self.endpoint = 'https://www.alphavantage.co/query'
        self.AV_API_KEY = 'I73NFDXTSF4A9DNO'

    def get_daily_chart (self, symbol):
        params = {
            'function': 'TIME_SERIES_DAILY', # For the daily chart
            'symbol':   symbol,
            'apikey':   self.AV_API_KEY,
            'datatype': 'csv'
        }

        response = requests.get(self.endpoint, params)

        if(response.status_code == 200):  # Status: OK
            return response.content
        else:
            print('Error: got response code %d' % response.status_code)
            print(response.text)
            return []
