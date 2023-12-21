import pandas as pd
import requests

def get_current(lat, long, api_key, DEBUG=False):
    # gets current weather at lat, long
    # returns json weather data
    api_url = "http://api.openweathermap.org/data/2.5/weather?lat={}&lon={}&units=imperial&appid={}".format(lat, long, api_key)
    if DEBUG:
        print(api_url)

    r = requests.get(api_url)
    return r.json()

def get_forecast(lat, long, api_key, DEBUG=False):
    # gets forecasted weather at lat, long
    # returns json weather data
    api_url = "https://api.openweathermap.org/data/2.5/forecast?lat={}&lon={}&units=imperial&appid={}".format(lat, long, api_key)
    if DEBUG:
        print(api_url)

    r = requests.get(api_url)
    return r.json()

def build_forecast_df(config):
    # Get forecasted air pressure
    forecast = get_forecast(config['lat'], config['long'], config['api'])
    # convert json to data frame
    df1 = pd.DataFrame(forecast['list'])
    df2 = pd.json_normalize(df1['main'])
    df3 = pd.json_normalize(df1['weather']) # returns list of dictionaries
    df3 = pd.json_normalize(df3[0])
    df4 = pd.json_normalize(df1['wind'])

    # localize time from UTC to US/Pacific by converting to date format and back to string
    df1['dt_txt'] = pd.to_datetime(df1['dt_txt'])
    df1['dt_txt'] = df1['dt_txt'].dt.tz_localize('UTC').dt.tz_convert('US/Pacific')
    df1['dt_txt'] = df1['dt_txt'].dt.strftime('%Y-%m-%d %H:%M:%S')

    # build result dataframe
    result = pd.concat([
        df1["dt_txt"],
        df2['temp'],
        df2["pressure"],
        df3['description'],
        df3['icon'],
        df1['pop'],
        df4['speed'],
        df4['gust'],
        df4['deg']
    ], axis=1)
    result.rename(columns={
        'dt_txt': 't',
        'pressure': 'Forecasted Pressure'
    }, inplace=True)

    return result

def deg_to_compass(deg):
    # converts compass degrees to cardinal direction
    val = int((deg/22.5)+0.5)
    arr = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
    direction = arr[(val % 16)]
    return direction

