import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import requests
import weather

DEBUG = True


def get_data(beginDate, endDate, product, stationId = "9444900", datum = "MLLW"):
    # takes date range, data product (prediction, water_level, pressure), station ID, and datum
    # builds API call
    # returns json data
    # get tide data from NOAA station
    # https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?begin_date=20231201&end_date=20231202&station=9444900&product=predictions&datum=MLLW&time_zone=lst_ldt&units=english&format=json
    # https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?begin_date=20231129&end_date=20231201&station=9444900&product=water_level&datum=MLLW&time_zone=lst_ldt&units=english&format=json

    api_url = ("https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?begin_date={}&end_date={}"
               "&station={}&product={}&datum={}&time_zone=lst_ldt&units=english&format=json").format(
        beginDate.strftime('%Y%m%d'),
        endDate.strftime('%Y%m%d'),
        stationId,
        product,
        datum,
    )
    if DEBUG:
        print(api_url)
    r = requests.get(api_url)

    return r.json()

def build_df(config):
    FUTURE_DAYS = 5
    PAST_DAYS = 1

    # Get predicted tides
    json_predicted = get_data(
        beginDate=datetime.today() - timedelta(days=PAST_DAYS),
        endDate=datetime.today() + timedelta(days=FUTURE_DAYS),
        product='predictions',
        stationId=config['tide_station'],
        datum = config['datum'],
        )

    # Get measured tides
    json_measured = get_data(
        beginDate=datetime.today() - timedelta(days=PAST_DAYS),
        endDate=datetime.today(),
        product='water_level',
        stationId=config['tide_station'],
        datum = config['datum'],
        )
    station_name = json_measured["metadata"]['name']

    # Get measured air pressure
    json_pressure = get_data(
        beginDate=datetime.today() - timedelta(days=PAST_DAYS),
        endDate=datetime.today(),
        product='air_pressure',
        stationId=config['tide_station'],
        datum = config['datum'],
        )

    # get 2 day air pressure prediction from OpenWeather (3 hour intervals)
    # TODO: reuse dataframe from weather forecast
    fc_press_df = weather.build_forecast_df(config)
    fc_press_df['t'] = pd.to_datetime(fc_press_df['t'])

    # convert json to dataframes and clean up
    p_df = pd.DataFrame(json_predicted["predictions"])
    p_df['t'] = pd.to_datetime(p_df['t'])
    p_df.rename(columns={'v': 'Predicted Height'}, inplace=True)

    a_df = pd.DataFrame(json_measured["data"])
    a_df['t'] = pd.to_datetime(a_df['t'])
    a_df.rename(columns={'v': 'Measured Height'}, inplace=True)
    a_df.drop(["s", "f", "q"], axis=1, inplace=True)   # remove unused data

    m_press_df = pd.DataFrame(json_pressure["data"])
    m_press_df['t'] = pd.to_datetime((m_press_df['t']))
    m_press_df.rename(columns={'v': 'Measured Pressure'}, inplace=True)
    m_press_df.drop(['f'], axis=1, inplace=True)

    # merge data frames
    result_df = pd.merge(left=p_df, right=a_df, how='left', left_on='t', right_on='t')
    result_df = pd.merge(left=result_df, right=m_press_df, how='left', left_on='t', right_on='t')
    result_df = pd.merge_asof(left=result_df, right=fc_press_df,  left_on='t', right_on='t')

    # convert data fields to plottable data types
    result_df["t"] = pd.to_datetime(result_df["t"])
    result_df[['Predicted Height','Measured Height','Measured Pressure','Forecasted Pressure']] = (
        result_df[['Predicted Height','Measured Height','Measured Pressure','Forecasted Pressure']].apply(pd.to_numeric)
    )

    # calculate new tide levels from predicted barometric pressure
    result_df['Estimated Height'] = result_df['Predicted Height'] + result_df['Forecasted Pressure'].apply(est_rise)

    return result_df, station_name

def est_rise(pressure):
    # takes a barometric pressure and returns an estimated increase in tide due to low pressure
    # returns tide rise in feet

    # slope of -0.3937 in/mPA calculated from:
    #  tide_rise = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16] # inches rise
    #mbar = [1013.003, 1010.463, 1007.923, 1005.383, 1002.843, 1000.303, 997.7631,
    #        995.2233, 992.6832, 990.1431, 987.6033, 985.0631, 982.5233, 979.9832,
    #        977.443, 974.9032, 972.3631] # matching pressure levels
    REF_PRESSURE = 1013.003 # mPA
    SLOPE = -0.3937  # inches / mPA

    if pd.isna(pressure):
        rise = np.nan   # no pressure data
    elif pressure < REF_PRESSURE:
        # air pressure could cause higher water level
        rise = (1/12) * SLOPE * (pressure - REF_PRESSURE) # rise in feet
    else:
        rise = np.nan   # pressure effect is 0, NaN to show predicted plot

    return rise

