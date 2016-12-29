import itertools
import os

import pandas as pd
import psycopg2 as ps
# Imports credentials. Should not import all like this, but *shruggie*
from secret import *
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from string import ascii_uppercase
from os.path import expanduser
import requests
import traceback
import plotly

# Login to Plotly
plotly.tools.set_credentials_file(username=plotly_username, api_key=plotly_api_key)
from subprocess import call

pd.set_option('display.height', 1000)
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)

master_automation_email = 'schwallie@gmail.com'
master_email = 'schwallie@gmail.com'

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



def df_to_google_doc(df, workbook_name, wks_name, include_col_names=True, include_index=True,
                     return_link=False, clear_wks=False):
    """

    :param df: DataFrame to write
    :param workbook_name: Name of workbook
    :param wks_name: Name or worksheet
    :param include_col_names:
    :param include_index:
    :return:
    """
    last_row = len(df.index) if include_col_names else len(df.index) - 1
    # Give final col name
    result = []
    col = len(df.columns) + 1 if include_index else len(df.columns)
    while col:
        col, rem = divmod(col - 1, 26)
        result[:0] = ascii_uppercase[rem]
    last_col = ''.join(result)
    len_cols = len(df.columns)
    # Give first col/row name
    first_col = 'B1' if include_index else 'A1'
    first_row = 'A2' if include_col_names else 'A1'
    wkb = open_connection_to_google_spreadsheet(workbook_name)
    names = [tit.title for tit in wkb.worksheets()]
    if wks_name not in names:
        wkb.add_worksheet(wks_name, 1, 1)
    wks = wkb.worksheet(wks_name)
    if clear_wks:
        # If only 1, need to add a dummy then delete it
        if len(wkb.worksheets()) == 1:
            wkb.add_worksheet('Temp', 1, 1)
        wkb.del_worksheet(wks)
        wkb.add_worksheet(wks_name, rows=last_row + 1, cols=len_cols + 1)
        if wkb.worksheets()[0].title == 'Temp':
            wkb.del_worksheet(wkb.worksheet('Temp'))
        # Not sure if needed, but worried the old pointer could be broken here
        wkb = open_connection_to_google_spreadsheet(workbook_name)
        wks = wkb.worksheet(wks_name)
    else:
        # Add rows/cols to fit dataframe
        wks.resize(rows=last_row + 1, cols=len_cols + 1)

    # Add col names to sheet
    if include_col_names:
        cells = wks.range('%s:%s1' % (first_col, last_col))
        for idx, cell in enumerate(cells):
            cell.value = df.columns[idx]
        wks.update_cells(cells)

    # Add index to sheet if needed
    if include_index:
        cells = wks.range('%s:A%d' % (first_row, last_row + 1))
        for idx, cell in enumerate(cells):
            cell.value = df.index[idx]
        wks.update_cells(cells)

    # Add cell values to sheet
    cells = wks.range('%s%s:%s%d' % (first_col[0], first_row[1], last_col, last_row + 1))
    for ix_idx, idx in enumerate(df.index):
        for ix_col, col in enumerate(df.columns.values):
            col_multiplier = ix_idx * len(df.columns)
            cells[ix_col + col_multiplier].value = df.iloc[ix_idx][col]
    # Chunk for problems with >1k cells in google spreadsheets
    for update in grouper(iter(cells), 1000):
        print update
        wks.update_cells(list(update))
    if return_link:
        return 'https://docs.google.com/spreadsheets/d/{}'.format(wkb.id)


def grouper(it, n):
    while 1:
        chunk = tuple(itertools.islice(it, n))
        if not chunk:
            return
        yield chunk


def get_first_bday_of_month(mnth=None, yr=None):
    '''
    Return the first business day of the current month if no variables provided
    Return the first business day of the month and year provided if variables provided

    Tests:
    In [188]: config.get_first_bday_of_month(12,2015)
    Out[188]: datetime.date(2015, 12, 1)

    In [189]: config.get_first_bday_of_month(11,2015)
    Out[189]: datetime.date(2015, 11, 2)

    In [190]: config.get_first_bday_of_month(10,2015)
    Out[190]: datetime.date(2015, 10, 1)

    In [191]: config.get_first_bday_of_month(1,2016)
    Out[191]: datetime.date(2016, 1, 4)

    In [192]: config.get_first_bday_of_month(8,2015)
    Out[192]: datetime.date(2015, 8, 3)
    :param mnth:
    :param yr:
    :return:
    '''
    from calendar import monthrange
    from pandas.tseries.holiday import USFederalHolidayCalendar
    from pandas.tseries.offsets import CustomBusinessDay
    if yr is None or mnth is None:
        yr = pd.datetime.now().year if pd.datetime.now().month != 1 else pd.datetime.now().year - 1
        mnth = pd.datetime.now().month - 1 if pd.datetime.now().month != 1 else 12
    else:
        yr = yr if mnth != 1 else yr - 1
        mnth = mnth - 1 if mnth != 1 else 12
    end_last = monthrange(yr, mnth)
    end_last = pd.Timestamp('%s/%s/%s' % (mnth, end_last[1], yr)).date()
    cal = USFederalHolidayCalendar()
    holidays = cal.holidays(start=end_last - pd.tseries.offsets.Day(60),
                            end=end_last + pd.tseries.offsets.Day(60)).to_pydatetime()
    bday_cus = CustomBusinessDay(holidays=holidays)
    return (end_last + bday_cus).date()


def get_last_weekday_value(weekday):  # Mon = 0, Sun = 6
    '''
    If you want to get the last Friday, use weekday=4, last Thurs = 3, Sun = 6
    '''
    day_minus = pd.datetime.today().weekday() + weekday - 1
    return (pd.datetime.today() - pd.tseries.offsets.Day(day_minus)).date()


def plotly_retries(url):
    """
    Can mostly get away without using this as we
    implemented this type of behavior directly into Plotly,
    but it's not a bad check to handle Plotly's servers
    being wonky
    :param url:
    :return:
    """
    print url
    import logging
    logging.basicConfig(filename='%splotly.log' % excel_folder, level=logging.DEBUG,
                        format='%(asctime)s %(message)s')
    attempts = 0
    logging.debug('status code == {}, embed status code == {}, {}, attempt {}'.format(
        requests.get(url.split('?')[0] + '.png?' + url.split('?')[1]).status_code,
        requests.get(url.split('?')[0] + '.embed?' + url.split('?')[1]).status_code,
        url, attempts))
    while (requests.get(url.split('?')[0] + '.png?' + url.split('?')[1]).status_code == 404 or
                   requests.get(url.split('?')[0] + '.embed?' + url.split('?')[1]).status_code == 404):
        logging.debug('404 on {}, attempt {}'.format(url, attempts))
        attempts += 1
        if attempts == 7:
            break
        # attempt to add secret sharing permissions again
        url = plotly.plotly.plotly.add_share_key_to_url(url.split('?')[0])
    url_split = url.split('?')
    return url_split


def return_under_state_usury(tape):
    tape = tape[(tape.state != 'VT') | ((tape.state == 'VT') & (tape.apr < .12))]
    tape = tape[(tape.state != 'CT') | ((tape.state == 'CT') & (tape.apr < .12))]
    tape = tape[(tape.state != 'NY') | ((tape.state == 'NY') & (tape.apr < .16))]
    return tape

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


def bigrams_trigrams(df, col='Stars', text_col='Body'):
    import nltk
    from collections import Counter
    from nltk.util import ngrams
    from wordcloud import WordCloud
    from nltk.corpus import stopwords
    s = set(stopwords.words('english'))
    s.add('$')
    s.add(u"n't")
    s.add('would')
    s.add('get')
    s.add('got')
    for val in df[col].unique():
        if pd.isnull(val):
            continue
        print val
        piece = df[df[col] == val]
        text = " ".join(piece[text_col].values.tolist())
        token = nltk.word_tokenize(text.decode('utf-8'))
        bigrams = ngrams(token, 1)
        trigrams = ngrams(token, 2)
        lst_bi = []
        [lst_bi.append(x[0]) for x in bigrams if x[0].lower() not in s]
        lst_tri = []
        [lst_tri.append(x) for x in trigrams]
        x = pd.DataFrame.from_dict(Counter(lst_bi), orient='index')
        print x.sort_values(x.columns[0], ascending=False).head(10)
        x = pd.DataFrame.from_dict(Counter(lst_tri), orient='index')
        print x.sort_values(x.columns[0], ascending=False).head(10)
        try:
            wc = WordCloud(margin=10, random_state=3)
            # from_freqencies ignores "stopwords" so we have to do it ourselves
            wc.generate_from_frequencies(lst_bi)
            image = wc.to_image()
            image.save('/Users/chaseschwalbach/Desktop/ImgSave_Tri_%s.png' % val)
            wc = WordCloud(margin=10, random_state=3)
            # from_freqencies ignores "stopwords" so we have to do it ourselves
            wc.generate_from_frequencies(lst_tri)
            image = wc.to_image()
            image.save('/Users/chaseschwalbach/Desktop/ImgSave_Bi_%s.png' % val)
        except Exception:
            print traceback.format_exc()


def get_freq_of_words_over_time(df, col='Stars', text_col='Body'):
    import nltk
    from collections import Counter
    from nltk.util import ngrams
    from nltk.corpus import stopwords
    from send_email import EmailHandler
    df = pd.read_pickle('/data/saved_files/CreditKarmaCustReviews.p')
    df["Date"] = pd.to_datetime(df['Date'])
    df = df[df.Date > '2016-07-01']
    df['Body'] = df['Body'].str.replace('?', "")
    df['Body'] = df['Body'].str.replace('.', "")
    df['Body'] = df['Body'].str.replace('!', "")
    df['Body'] = df['Body'].str.replace('&quot;', "")
    df['Body'] = df['Body'].str.replace('&#39;', "'")
    df['Body'] = df['Body'].str.replace('&nbsp;', '')
    df['Body'] = df['Body'].str.replace('<br>', '')
    df['Body'] = df['Body'].str.replace('<br />', '')
    df['Body'] = df['Body'].str.replace('</strong>', '')
    df['Body'] = df['Body'].str.replace('<strong>', '')
    df['Body'] = df['Body'].str.replace('</p>', '')
    df['Body'] = df['Body'].str.replace('<p>', '')
    df['Body'] = df['Body'].str.replace(',', '')
    s = set(stopwords.words('english'))
    s.add('$')
    s.add(u"n't")
    s.add('would')
    s.add('get')
    s.add('got')
    s.add('%')
    s.add(')')
    s.add('(')
    s.add("'s")
    s.add('one')
    s.add('could')
    s.add('needed')
    s.add("make")
    eh = EmailHandler(to='chase.schwalbach@avant.com', subject='Word Frequencies Over Time')
    for val in ["1", "5"]:
        if pd.isnull(val):
            continue
        print val
        piece = df[df[col] == val]
        text = " ".join(piece[text_col].values.tolist())
        token = nltk.word_tokenize(text.decode('utf-8'))
        bigrams = ngrams(token, 1)
        lst_bi = []
        [lst_bi.append(x[0]) for x in bigrams if x[0].lower() not in s]
        top_words = pd.DataFrame.from_dict(Counter(lst_bi), orient='index')
        top_words = top_words.sort_values(top_words.columns[0], ascending=False).head(20)
        for newcol in top_words.index:
            piece[newcol] = 0
            piece.loc[piece.Body.str.contains(newcol), newcol] = 1
        piece['Count'] = 1
        piece['Date'] = pd.to_datetime(piece['Date'])
        piece.index = piece['Date']
        piece = piece.resample('3M').sum()
        piece = piece.fillna(0)
        for newcol in top_words.index:
            piece[newcol] = piece[newcol] / piece['Count']
        del piece['Count']
        print piece
        x = piece.iloc[-1] - piece.iloc[-2]
        x = x.sort_values()
        print x
        url = piece.iplot(sharing='secret', title=val)
        url_split = config.plotly_retries(url.resource)
        eh.add_plot_text(url_split, scale=.5)
        eh.add_random_text('<br>Amount change over last two full months: <br> %s' % x.to_frame().to_html())


__author__ = "Chase Schwalbach"
__credits__ = ["Chase Schwalbach"]
__version__ = "1.0"
__maintainer__ = "Chase Schwalbach"
__email__ = "schwallie@gmail.com"
__status__ = "Production"
