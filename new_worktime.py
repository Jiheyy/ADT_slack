#_*_ coding:utf_8_*_
import pymssql
import time
from datetime import datetime
import logging
import urllib3
import json
import requests
import pandas as pd
from slacker import Channels, Slacker


# =====================================================
AGENT_NAME = "ADT timesheet"
G_COMMON_LIB_VER = '0.0.6'
G_COMMON_LIB_DATE = '2021-07-05'
# by min(jh)
# =====================================================
# slack_token
API_TOKEN = 'xoxb-000000000000000000'
# white list
WHITE_LIST = [2, 10]
CHANNELS = '#mytest'
# =====================================================

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(message)s')
file_handler = logging.FileHandler('worktime.log')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

E_MODE = {'attndance':'1', 'leave': '2', 'entry': '3', 'anounymous_enter_success': '4', 'anounymous_enter_failed': '5'}


def db_connect():
    try:
        # this is default id, password 
        conn = pymssql.connect(server="127.0.0.1", user="fdmsusr", password="fdmsamho", database=  "ACSDB", charset='utf8')
    except:
        print('db connection failed')
    
    return conn


def slack_message(msg, channel=CHANNELS, trial=0):
    try :
        sc = Slacker(API_TOKEN)
        sc.chat.post_message(channel = channel, text = msg, username="jhmin")
        print(msg)
    except Exception as ex : 
        slack_message(msg,tial=trial+1)
        if trial > 4:
            sc.chat.post_message(channel = channel, text = 'adt slack sender error', username="jhmin")


def sender(name, time, mode):
    text = name
    if mode == 'attndance' : text = text + ' attendance. ('+time+')'
    elif mode == 'leave' : text = text + ' leave. ('+time+')'
    elif mode == 'out' : text = text + ' out ('+time+')'
    elif mode == 'back': text = text + 'back ('+ time+')'
    elif mode  == 'anounymous_enter_success' : text = 'anounymous_enter_success. ('+time+')'
    elif mode  == 'anounymous_enter_failed' : text = 'anounymous_enter_failed.('+time+')'

    slack_message(text)


def convert(time) :
    return time[0]+time[1]+":"+time[2]+time[3]+":"+time[4]+time[5]


def check_anonymous(d):
    if d.e_name is ' ':
        if d.e_result == 0:
            sender(d.e_name, convert(d.e_time), 'anounymous_enter_success')
        else:
            sender(d.e_name, convert(d.e_time), 'anounymous_enter_failed')

 

def execute(ex_time):
    cur_time = datetime.datetime.now()
    cur_date = cur_time.strftime("%Y%m%d")
    cur_time = cur_time.strftime('%H%M%S')

    if int(cur_time) < int('000100'):
        yesterdate = datetime.date.today() - datetime.timedelta(1)
        cur_date = yesterdate.strftime('%Y%m%d')
        cur_time = '246060'

    conn = db_connect()

    cmd = "SELECT * FROM dbo.tenter WHERE e_date = "+str(cur_date)+" \
        AND e_time >= "+ str(ex_time)+" AND e_time < "+str(cur_time)+"\
        AND e_id < 120 AND e_id > 0 AND e_result != 'c' AND e_result != 'a' AND e_result = 0"

    try:
        df = pd.read_sql(cmd, conn)
    except Exception as ex:
        print(ex)
        return

    for idx, d in df.iterrows():
        if d.e_id in WHITE_LIST: continue
        
        check_anonymous(d)

        if d.e_mode == E_MODE['attndance']:        
            sender(d.e_name, convert(d.e_time), 'attndance')

        elif d.e_mode == E_MODE['leave']:
            sender(d.e_name, convert(d.e_time), 'leave')

        elif d.e_mode == E_MODE['entry']:
            # out
            if d.g_id == 5:
                sender(d.e_name, convert(d.e_time), 'stop')
            # back
            elif d.g_id == 1:
                sender(d.e_name, convert(d.e_time), 'back')
                            
    conn.close()

    if cur_time == '246060':
        cur_time = '000000'

    return cur_time 


def workday() : 
    today =datetime.datetime.now().strftime("%m%d")

    conn = db_connect()
    df = pd.read_sql("SELECT * FROM dbo.nHoliday WHERE d_date = "+str(today), conn)

    # holiday or sunday
    if len(df) >= 1 or time.localtime().tm_wday > 5 : 
        return False
    return True             


if __name__ == "__main__":

    cur_time = datetime.datetime.now()
    ex_time = cur_time.strftime("%H%M%S")

    while True:
        try:
            ex_time = execute(ex_time)
        except Exception as ex :
            logger.info(str(ex))
            
        time.sleep(60)
        