# Import necessary libraries
import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
# import os

# Set up the data path and read the data
# project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# data_file_path = os.path.join(project_root, 'data', 'covid_data.csv')

print("Loading data...")
# Read the data and convert date column to datetime
# df = pd.read_csv("https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/owid-covid-data.csv")
df = pd.read_csv("./data/covid_data.csv")
df['date'] = pd.to_datetime(df['date'])

# Remove Antarctica and limit date
df = df[df['continent'] != 'Antarctica']  # Remove Antarctica
df = df[df['date'] <= '2024-06-17']      # Limit to June 17, 2024

# Helper function to format numbers with commas and handle missing values
def format_number(value):
    if pd.isna(value):
        return 'No data'
    return f"{int(value):,}"

# Helper function to prepare data for visualization
def prepare_map_data(date_data):
    """Prepares data for visualization by handling missing values"""
    processed_data = date_data.copy()
    processed_data['total_deaths_per_million'] = processed_data['total_deaths_per_million'].fillna(-1)
    return processed_data

# Create the Dash application
app = dash.Dash(__name__)
#! For Deployment only
# server = app.server

# Define the layout of our dashboard
app.layout = html.Div([
    # Header section
    html.Div([
        html.H1(
            'COVID-19 Deaths per Million People',
            style={
                'textAlign': 'center',
                'color': '#2c3e50',
                'fontSize': '20px',
                'fontWeight': 'normal',
                'marginBottom': '5px',
                'padding': '10px 10% 0 10%'
            }
        ),
        html.P(
            'Visualization shows the cumulative COVID-19 deaths per million people for each country over time.',
            style={
                'textAlign': 'center',
                'color': '#666666',
                'fontSize': '12px',
                'marginBottom': '10px'
            }
        )
    ], style={'height': '10vh'}),
    
    # Time control panel
    html.Div([
        html.Button('▶ Play', 
                   id='play-button',
                   style={
                       'marginRight': '10px',
                       'padding': '3px 12px',
                       'fontSize': '12px',
                       'backgroundColor': '#1d4ed8',
                       'color': 'white',
                       'border': 'none',
                       'borderRadius': '4px',
                       'cursor': 'pointer'
                   }),
        html.Div([
            dcc.Slider(
                id='time-slider',
                min=0,
                max=len(df['date'].unique()) - 1,
                value=len(df['date'].unique()) - 1,
                marks={
                    i: date.strftime('%Y-%m')
                    for i, date in enumerate(sorted(df['date'].unique()))
                    if i % 60 == 0
                },
                updatemode='drag'
            ),
            dcc.Interval(
                id='interval-component',
                interval=100,
                n_intervals=0,
                disabled=True
            ),
        ], style={'width': '100%', 'padding': '0 20px'})
    ], style={
        'width': '80%',
        'margin': '10px auto',
        'padding': '10px',
        'backgroundColor': '#f8f9fa',
        'borderRadius': '5px',
        'display': 'flex',
        'alignItems': 'center',
        'height': '8vh'
    }),
    
    # Map container
    html.Div([
        dcc.Graph(
            id='covid-map',
            style={
                'height': '77vh',
                'width': '100%'
            },
            config={'displayModeBar': False}  # Remove the plotly mode bar
        )
    ], style={
        'display': 'flex',
        'justifyContent': 'center',
        'alignItems': 'center',
        'width': '100%',
        'height': '77vh'
    })
], style={
    'height': '100vh',
    'width': '100%',
    'backgroundColor': '#ffffff',
    'overflow': 'hidden'
})

# Callback to handle play/pause functionality
@app.callback(
    [Output('interval-component', 'disabled'),
     Output('play-button', 'children')],
    [Input('play-button', 'n_clicks')],
    [State('interval-component', 'disabled')]
)
def toggle_animation(n_clicks, current_disabled):
    if n_clicks is None:
        return True, '▶ Play'
    return not current_disabled, '⏸ Pause' if current_disabled else '▶ Play'

# Callback to update the slider during animation
@app.callback(
    Output('time-slider', 'value'),
    [Input('interval-component', 'n_intervals'),
     Input('time-slider', 'value')],
    [State('interval-component', 'disabled')]
)
def update_time_slider(n_intervals, slider_value, disabled):
    if disabled:
        return slider_value
    max_value = len(df['date'].unique()) - 1
    return (slider_value + 1) % max_value

# Callback to update the map
@app.callback(
    Output('covid-map', 'figure'),
    [Input('time-slider', 'value')]
)
def update_map(selected_index):
    dates = sorted(df['date'].unique())
    selected_date = dates[selected_index]
    
    date_data = df[df['date'] == selected_date].copy()
    date_data = prepare_map_data(date_data)
    
    fig = go.Figure(data=go.Choropleth(
        locations=date_data['iso_code'],
        z=date_data['total_deaths_per_million'],  # Changed to deaths per million
        text=date_data.apply(
            lambda x: f"Country: {x['location']}<br>"
                     f"Deaths per Million: {format_number(x['total_deaths_per_million'])}<br>"
                     f"Total Deaths: {format_number(x['total_deaths'])}",
            axis=1
        ),
        colorscale=[
            [0, '#ffffff'],      # No data (white)
            [0.1, '#fee5d9'],    # Lightest red
            [0.3, '#fcae91'],    # Light red
            [0.5, '#fb6a4a'],    # Medium red
            [0.7, '#de2d26'],    # Dark red
            [1.0, '#a50f15']     # Darkest red
        ],
        colorbar=dict(
            title="Deaths per Million",
            thickness=15,
            len=0.5,
            x=1.0,
            y=0.5,
            yanchor='middle',
            tickmode='array',
            ticktext=['No data', '0', '1000', '2000', '3000', '4000'],
            tickvals=[-1, 0, 1000, 2000, 3000, 4000],
            tickfont=dict(size=10)
        ),
        zmin=-1,
        zmax=4000  # Adjusted for deaths per million scale
    ))
    
    fig.update_layout(
        geo=dict(
            showframe=False,
            showcoastlines=True,
            projection_type='equirectangular',
            showland=True,
            landcolor='white',
            showocean=True,
            oceancolor='#eef3f7',
            showcountries=True,
            countrycolor='#cccccc',
            center=dict(lon=0, lat=20),
            projection_scale=1.1
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='white',
        plot_bgcolor='white',
        height=700,
        width=None
    )
    
    return fig

# Run the server
if __name__ == '__main__':
    print("Starting dashboard server...")
    app.run_server(debug=True)