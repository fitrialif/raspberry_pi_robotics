import os
from secret import *
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from subprocess import call

main_folder = '/data/saved_files/'
if not os.path.isdir(main_folder):
    call(['mkdir ' + main_folder], shell=True)

def open_connection_to_google_spreadsheet(spreadsheet_name, open_by_key=False, open_by_url=False):
    """
    Opens a Google spreadsheet
    :param spreadsheet_name: The name of the spreadsheet
    :return: workbook object
    """
    scope = ['https://spreadsheets.google.com/feeds']

    credentials = ServiceAccountCredentials.from_json_keyfile_dict(drive_details, scope)
    gc = gspread.authorize(credentials)
    if open_by_key:
        return gc.open_by_key(spreadsheet_name)
    elif open_by_url:
        return gc.open_by_url(spreadsheet_name)
    return gc.open(spreadsheet_name)


def get_df_from_google_spreadsheet(spreadsheet_name, sheet_title, open_by_key=False, open_by_url=False, headers=True):
    import pandas as pd
    wkb = open_connection_to_google_spreadsheet(spreadsheet_name, open_by_key=open_by_key, open_by_url=open_by_url)
    # Expects an int, need to find what integer title is if int is not provided
    if type(sheet_title) == int:
        wks = wkb.get_worksheet(sheet_title)
    else:
        for ix, wks in enumerate(wkb.worksheets()):
            if wks.title == sheet_title:
                break
        wks = wkb.get_worksheet(ix)
    df = pd.DataFrame.from_records(wks.get_all_values())
    if headers:
        df.columns = df.ix[0].values
        df = df.ix[1:]
    return wkb, df

def format_percent(item):
    return '{:.1%}'.format(item)


def format_money(item, locale='us'):
    if locale == 'uk':
        return u'\xA3{:,.0f}'.format(item)
    else:
        return '${:,.0f}'.format(item)


def format_money_gbp(item, locale='uk'):
    if locale == 'uk':
        return u'\xA3{:,.0f}'.format(item)
    else:
        return '${:,.0f}'.format(item)


def format_money_w_decimal(item, locale='us'):
    if locale == 'uk':
        return u'\xA3{:,.0f}'.format(item)
    else:
        return '${:,.2f}'.format(item)


def format_number(item):
    return '{:,.0f}'.format(item)


def format_number_w_decimal(item):
    return '{:,.1f}'.format(item)



__author__ = "Chase Schwalbach"
__credits__ = ["Chase Schwalbach"]
__version__ = "1.0"
__maintainer__ = "Chase Schwalbach"
__email__ = "schwallie@gmail.com"
__status__ = "Production"
