from __future__ import print_function
import datetime
import readline
import pickle
import os.path
import re
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from timezones import Pacific
import copy

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/calendar']

def rlinput(prompt, prefill=''):
    readline.set_startup_hook(lambda: readline.insert_text(prefill))
    try:
        return input(prompt)
    finally:
        readline.set_startup_hook()

def yes_no(prompt):
    user_input = None
    while (user_input is None):
        user_input = input(prompt).lower()
        if (user_input != 'y' and user_input != 'n'):
            user_input = None
            print("Invalid input. [Y] or [N] (case insensitive)")
    return user_input == 'y'

def int_prompt(prompt, lower_bound=0, upper_bound=10000):
    user_input = None
    while (user_input is None):
        try:
            user_input = int(input(prompt))
            if (user_input < lower_bound or user_input > upper_bound):
                user_input = None
                raise ValueError
        except ValueError:
            print("Invalid input. ({},{}) inclusive".format(lower_bound, upper_bound))
    return user_input


def get_creds_service():
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)
    if not os.path.exists('calendar_url.txt'):
        api_cal = select_calendar(service)
        with open('calendar_url.txt', 'w') as f:
            f.write(api_cal)
    else:
        with open('calendar_url.txt', 'r') as f:
            api_cal = f.readline().strip()
    return (creds, service, api_cal)

def select_calendar(service):
    list_cals = service.calendarList().list().execute()
    i = 0
    cals = list_cals.get('items')
    for x in cals:
        print("[{}] {}".format(i, x.get("summary")))
        i += 1
    return cals[int_prompt("Select the group meeting calendar: ", lower_bound=0, upper_bound=len(cals))].get("id")

def get_datetime_obj(day, month, year):
    return datetime.datetime(year, month, day).isoformat() + 'Z'

def get_datetime_now():
    return datetime.datetime.combine(datetime.datetime.now(tz=Pacific).date(),
                                     datetime.datetime.min.time()).isoformat() + 'Z'

def get_datetime_2_week_ago():
    return datetime.datetime.combine((datetime.datetime.now(tz=Pacific).date()  - datetime.timedelta(days=14)),
                                     datetime.datetime.min.time()).isoformat() + 'Z'

def datetime_to_api_format(dt, dur):
    dt_copy = datetime.datetime(dt.year, dt.month, dt.day, hour=dt.hour, minute=dt.minute, tzinfo=Pacific)
    return [dt_copy.isoformat(), (dt_copy + dur).isoformat()]

def extract_day(query):
    match = re.search('^(\d{4})-(\d{2})-(\d{2})T.*$', query)
    if (match is None):
        print("No day found")
    return datetime.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))

def extract_time(query):
    match = re.search('^.*T(\d{2}):(\d{2}):\d{2}-.*$', query)
    if (match is None):
        print("No time found")
    return datetime.timedelta(hours=int(match.group(1)), minutes=int(match.group(2)))

def extract_datetime(query):
    match = re.search('^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):\d{2}-.*$', query)
    if (match is None):
        print("No datetime found")
    return datetime.datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)),
                             hour=int(match.group(4)), minute=int(match.group(5)))

def get_event_type(summary):
    match = re.search('^.*\[(.*?)\].*$', summary)
    if (match is None):
        return None
    return match.group(1)

def list_all_research_events(start_date, creds, service, cal='primary'):
    events_result = service.events().list(calendarId=cal, timeMin=start_date,
                                        maxResults=None, singleEvents=True,
                                        orderBy='startTime', timeZone='US/Pacific').execute()
    events = events_result.get('items', [])

    events_info_list = []
    if not events:
        print('No upcoming events found.')
    for event in events:
        event_type = get_event_type(event['summary'])
        if (event_type is not None):
            try:
                day = extract_day(event['start'].get('dateTime', event['start'].get('date')))
                start_time = extract_time(event['start'].get('dateTime', event['start'].get('date')))
                end_time   = extract_time(event['end'].get('dateTime', event['end'].get('date')))
                dur   = end_time - start_time
                event_name = re.search('^.*\[.*\]\s*?(\S.*)$', event['summary']).group(1)
                events_info_list += [Event(event_name, event_type, day, dur)]
            except AttributeError:
                print("AttributeError: {}".format(event['summary']))
    return events_info_list

class Event(object):
    def __init__(self, name, event_type, date, duration):
        self.name = name
        self.event_type = event_type
        self.date = date
        self.dura = duration

    def __str__(self):
        return "{} type [{}] on {} for {}".format(self.name, self.event_type, self.date, self.dura)
