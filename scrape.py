import os
from dotenv import load_dotenv
import http.client
import json
import pandas as pd
import openai

load_dotenv()

X_RapidAPI_Key = os.getenv('X_RapidAPI_Key')
openai.api_key = os.getenv('OpenAI')

def find_user_id(username):
    conn = http.client.HTTPSConnection("twitter135.p.rapidapi.com")

    headers = {
        'X-RapidAPI-Key': f"{X_RapidAPI_Key}",
        'X-RapidAPI-Host': "twitter135.p.rapidapi.com"
    }

    conn.request("GET", "/v2/UserByScreenName/?username={}".format(username), headers=headers)

    res = conn.getresponse()
    data = json.loads(res.read().decode('utf-8'))

    return data["data"]["user"]["result"]["rest_id"]

def scrape_tweets(username):
    count = 100
    conn = http.client.HTTPSConnection("twitter135.p.rapidapi.com")

    headers = {
        'X-RapidAPI-Key': f"{X_RapidAPI_Key}",
        'X-RapidAPI-Host': "twitter135.p.rapidapi.com"
    }
    
    conn.request("GET", "/v2/UserTweets/?id={}&count={}".format(find_user_id(username), count), headers=headers)

    res = conn.getresponse()
    data = json.loads(res.read().decode('utf-8'))
    tweets = data["data"]["user"]["result"]["timeline_v2"]["timeline"]["instructions"][1]["entries"]
    meta = [tweet["content"] for tweet in tweets]
    time, text = [], []

    for entry in meta:
        if "itemContent" in entry: 
            legacy = entry["itemContent"]["tweet_results"]["result"]["legacy"]
            time.append(legacy["created_at"])
            text.append(legacy["full_text"])
    
    tweets = pd.DataFrame(data={'username': username, 'time': pd.to_datetime(time, format='%a %b %d %H:%M:%S +0000 %Y'), 'text': text})
    return tweets

def scrape_all():
    full_df = pd.DataFrame(columns=['username', 'time', 'text'])

    with open("users.txt", "r") as file:
        for line in file:
            username = line.strip()
            full_df = pd.concat([full_df, scrape_tweets(username)], ignore_index=True)

    return full_df

def extract_statements(df, start_date, end_date):
    df_time = df[(df['time'] >= start_date) & (df['time'] <= end_date)]

    return df_time

def gpt_summarize(df):
    system_msg = 'You are an assistant who wants to summarize the recent activities of a startup from reading their tweets.'
    user_msg = 'Write a short summary of any recent product releases or raises of a startup given these tweets. Feel free to ignore tweets that are irrelevant\
    to the company\'s product. Use active tense. The tweets are presented here in chronological order: '

    for user in df.username.unique():
        df_sorted = df[df.username == user].sort_values(by='time')
        tweets = " ".join(df_sorted['text'])

        response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": system_msg},
                            {"role": "user", "content": user_msg + tweets}
                ])

        concise = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": system_msg},
                            {"role": "user", "content": 'Make this response more natural and concise: ' + response["choices"][0]["message"]["content"]}
                ])
        
        print(concise["choices"][0]["message"]["content"])

df = scrape_all()
df_dates = extract_statements(df, pd.to_datetime('2023-04-01'), pd.to_datetime('2023-04-30'))
gpt_summarize(df_dates)