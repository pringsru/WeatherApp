# Weather App for Maxwelton Farm

# import modules
import os
import dash
from dash import dcc, html, dash_table
from flask import Flask
import dash_bootstrap_components as dbc
import configparser
import pandas as pd
from datetime import datetime
import plotly.express as px

import tides
import weather


# initiate the app
server = Flask(__name__)
app = dash.Dash(__name__,
                server=server,
                external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP]
                )
#server = app.server

# set debug flag
DEBUG = False

# pull in data
def get_config():
    # read location information
    config = configparser.ConfigParser()
    config.read('config.ini')
    # get API key environment variable
    # also needs to be stored on the server
    config['weather']['api'] = os.environ.get('OPENWEATHER_API')
    return config['weather']


# build web page components
config = get_config()
header_component = html.H1(children="Maxwelton Weather Dashboard", style={})

def build_cell(df, ind):
    # builds html table cell contents
    cols = ["temp", "speed", "gust", "pop"]
    #TODO: move formatting to original dataframe
    # remove decimals, convert to strings
    df[cols] = df[cols].astype(int).astype(str)

    desc = html.Div(df['description'][ind])
    #icon = html.Div(df['icon'][ind])
    # build temperature text
    temp = html.Div("Temp " + df['temp'][ind] + " °F")
    # build wind text
    wind = html.Div("Wind " + df['speed'][ind] + "mph from " + weather.deg_to_compass(df['deg'][ind]))
    if df['speed'][ind] != df['gust'][ind]:
        gust = html.Div("Gusting to " + df['gust'][ind])
        wind = html.Div([wind, gust])
    # build rain text
    if df['pop'][ind] != '0':
        rain = html.Div(df['pop'][ind] + "% chance precip")
    else:
        rain = html.Div([""])
    cell = html.Td([desc, temp, wind, rain])

    return cell

def build_forecast_table(df):
    # Forecast Table
    # Column for each 3-hour forecast
    # Row for each day
    # Each cell contains: Description, Temp, PoP, Wind Speed, Gusts, Direction

    #TODO: after converting from UTC time, logic no longer works (midnight is 8 am)

    table_header = [html.Thead([
        html.Td("Date"),
        html.Td("Midnight"),
        html.Td("6 AM"),
        html.Td("Noon"),
        html.Td("6 PM"),
    ])]

    df['t'] = pd.to_datetime(df['t'])  # convert from string to datetime object
    df['hour'] = df['t'].dt.hour
    df['day'] = df['t'].dt.day

    table = []
    day_index = 0
    first_row = True
    row = []

    for ind in df.index:
        # for new day start a new table row
        if day_index == 0:
            # first time through
            day_index = df['day'][ind]
            # new row with date
            row = [html.Td(df['day'][ind])]

        elif df['day'][ind] != day_index:
            # subsequent times through, new day, new row
            day_index = df['day'][ind]
            table.append(html.Tr(row))
            # new row with date
            row = [html.Td(df['day'][ind])]

        # for a new hour, place the data in a cell
        if df['hour'][ind] == 0:
            # midnight
            if first_row:
                first_row = False
            cell = build_cell(df, ind)
            row.append(cell)
        elif df['hour'][ind] == 6:
            # 6am
            if first_row:
                row.append([html.Td()]) # blank cell
                first_row = False

            cell = build_cell(df, ind)
            row.append(cell)
        elif df['hour'][ind] == 12:
            # noon
            if first_row:
                row.append([html.Td(),html.Td()]) # blank cell
                first_row = False

            cell = build_cell(df, ind)
            row.append(cell)
        elif df['hour'][ind] == 18:
            # 6pm
            if first_row:
                row.append([html.Td(),html.Td(),html.Td()]) # blank cell
                first_row = False

            cell = build_cell(df, ind)
            row.append(cell)

    table_body = [html.Tbody(table, style={'font-size': '80%'})]
    # TODO: style table here
    table = dbc.Table(table_header + table_body,
                      bordered=True,
                      style={'text-align': 'center',
                             'margin': '10'},
                      )

    return table

def build_weather_comp(config):
    #TODO: Update real time weather from Tempest?
    current_data = weather.get_current(config['lat'], config['long'], config['api'])

    temp = "{0:.1f}".format(current_data["main"]["temp"])
    conditions = current_data["weather"][0]["main"]
    location = current_data["name"]
    pressure = current_data["main"]["pressure"]
    wind_speed = current_data["wind"]["speed"]
    wind_dir = weather.deg_to_compass(current_data["wind"]["deg"])

    #TODO: reuse weather forecast
    #forecast_data = weather.build_forecast_df(config)
    #fc_table = build_forecast_table(forecast_data)

    #        html.Br,
    #        dcc.Link("NOAA Point Forecast for Maxwelton Beach", href="https://forecast.weather.gov/MapClick.php?lon=-122.43913&lat=47.94203"),

    wc = html.Div(children=[
        html.H3(["Weather in ", location, ": ", conditions], className="text-center"),
        html.H2([temp,"°F"], className="text-center"),
        html.H3(["Wind ",wind_speed," mph from ", wind_dir], className="text-center"),
        html.H3([pressure, " mbar"], className="text-center"),
        dcc.Link("Tempest Weather Station at Maxwelton Beach",
                 href="https://tempestwx.com/station/65019/"),
    ], style={'background-color':'light-blue',
              'display':'inline-block',
              'padding':20,
              'margin':10,
              'border-radius':10})
    return wc

tide_df, station_name = tides.build_df(config)
def build_tide_comp(df, station_name):

    title = "".join(map(str,["Tide at ", station_name]))
    fig = px.line(df, x="t", y=["Predicted Height", "Measured Height", "Estimated Height"])
    fig.add_vline(x=datetime.now())
    fig.update_layout(
        title_text = title,
        title_x = 0.5,
        xaxis_title = "",
        yaxis_title = "Height MLLW (ft)",
        legend={'title':None},
    )
    # Legend location top right
    fig.update_layout(legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ))
    # annual max and min tide levels (MLLW: min -4.3',  max 12')
    TIDE_MIN = -4
    TIDE_MAX = 14
    fig.update_yaxes(range=[TIDE_MIN, TIDE_MAX])
    fig.update_yaxes(zeroline=True, zerolinewidth=2, zerolinecolor='gray')

    # add inundation levels
    TIDE_INN_MOD = 11.2   # Tide level for moderate inundation
    TIDE_INN_SEV = 12     # Tide level for severe inundation
    fig.add_hrect(y0=TIDE_INN_MOD, y1=TIDE_INN_SEV, line_width=0, fillcolor='yellow', opacity=0.2)
    fig.add_hrect(y0=TIDE_INN_SEV, y1=TIDE_MAX, line_width=0, fillcolor='red', opacity=0.2)
    return fig

def build_pressure_comp(df):
    fig = px.line(df, x="t", y=["Measured Pressure", "Forecasted Pressure"])
    fig.add_vline(x=datetime.now())
    fig.update_layout(
        title_text="Barometric Pressure",
        title_x=0.5,
        xaxis_title="",
        yaxis_title="mBar",
        legend={'title':None},
     )
    # Legend location top right
    fig.update_layout(legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ))
    # barometric pressure extremes
    PRESS_MIN = 970
    PRESS_MAX = 1050
    fig.update_yaxes(range=[PRESS_MIN, PRESS_MAX])

    return fig


# design the app layout
app.layout = html.Div(
    (
        dbc.Row(header_component),
        dbc.Row(build_weather_comp(config)),
        dbc.Row([dcc.Graph(figure=build_tide_comp(tide_df, station_name))]),
        dbc.Row([dcc.Graph(figure=build_pressure_comp(tide_df))]),
    )
)

#        dbc.Row([dcc.Link("Port Townsend Inundation Dashboard", href="https://tidesandcurrents.noaa.gov/inundationdb/inundation.html?id=9444900"),]),
#        dbc.Row([dcc.Link("Barometric Pressure Point Forecast",href="https://barometricpressure.app/results?lat=47.94203lng--122.43913"),]),


if __name__ == "__main__":
    # run the app
    app.run_server(debug=True)