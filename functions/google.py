from __future__ import print_function
from logging import Logger

import os.path
from dotenv import dotenv_values

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

fields_nums = {
        "username": 1,
        "chat_id": 2,
        "user_id": 3,
        "twitter": 4,
        "discord": 5,
        "email": 6,
        "metamask": 7,
        "finished": 8
    }

field_letters = {
        "username": "A",
        "twitter": "B",
        "discord": "C",
        "metamask": "D",
        "email": "E",
        "chat_id": "F",
        "user_id": "G",
        "finished": "H",
        "start_time": "I"
}

if os.path.exists('.env'):
    config = dotenv_values(".env")
else:
    config = dotenv_values("functions/.env")

# The ID and range of a sample spreadsheet.
SPREADSHEET_ID=config["SPREADSHEET_ID"]

def add_row(logger: Logger, num, username, twitter, discord, metamask, email, chat_id, user_id, finished, start_time):
    logger.info("{} - adding google row".format(username))
    if os.path.exists('token.json'):
        creds = service_account.Credentials.from_service_account_file("token.json", scopes=SCOPES)
    else:
        creds = service_account.Credentials.from_service_account_file("functions/token.json", scopes=SCOPES)
    try:
        service = build('sheets', 'v4', credentials=creds)
        # Call the Sheets API
        service.spreadsheets().values().update(
				spreadsheetId=SPREADSHEET_ID,
				range="A{}:I{}".format(num+1, num+1),
				body={
					"majorDimension": "ROWS",
					"values": [[username, twitter, discord, metamask, email, chat_id, user_id, finished, start_time]]
				},
				valueInputOption="USER_ENTERED"
			).execute()	
    except HttpError as err:
        return err
    return None

def update_info(logger: Logger, field: str, row: list):
    logger.info("{} - adding google row".format(row[1]))
    if os.path.exists('token.json'):
        creds = service_account.Credentials.from_service_account_file("token.json", scopes=SCOPES)
    else:
        creds = service_account.Credentials.from_service_account_file("functions/token.json", scopes=SCOPES)
    try:
        service = build('sheets', 'v4', credentials=creds)
        service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                    range="{}{}".format(field_letters[field],row[0]+1),
                    body={
                        "majorDimension": "ROWS",
                        "values": [
                                [row[fields_nums[field]]]
                            ]
                    },
                    valueInputOption="USER_ENTERED"
                ).execute()	
    except HttpError as err:
        return err
    return None