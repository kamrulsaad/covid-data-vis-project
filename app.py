import os
import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
from flask_caching import Cache

# Setup paths and initialize app
current_dir = os.path.dirname(os.path.abspath(__file__))
data_file_path = os.path.join(current_dir, 'data', 'covid_data.csv')

# Initialize Dash app
app = dash.Dash(__name__)
server = app.server

# Setup caching
cache = Cache(app.server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': 'cache-directory'
})
TIMEOUT = 3600

@cache.memoize(timeout=TIMEOUT)
def load_and_process_data():
    """Load and pre-process data with caching"""
    try:
        print(f"Loading data from: {data_file_path}")
        df = pd.read_csv(data_file_path)
        df['date'] = pd.to_datetime(df['date'])
        
        # Filter data
        df = df[df['date'] <= '2024-06-17']
        df = df[df['continent'] != 'Antarctica']
        
        # Pre-process data for each date
        dates = sorted(df['date'].unique())
        processed_data = {}
        
        for date in dates:
            date_data = df[df['date'] == date].copy()
            date_data['total_deaths_per_million'] = date_data['total_deaths_per_million'].fillna(-1)
            processed_data[pd.Timestamp(date)] = date_data
            
        return processed_data, dates
    except Exception as e:
        print(f"Error in data loading: {e}")
        raise

# Create cache directory if needed
cache_dir = os.path.join(current_dir, 'cache-directory')
os.makedirs(cache_dir, exist_ok=True)

# Load data
print("Loading and processing data...")
PROCESSED_DATA, DATES = load_and_process_data()
print("Data processing complete!")

# Define layout
app.layout = html.Div([
    # Header
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
    
    # Controls
    html.Div([
        # Play button
        html.Button(
            '▶ Play',
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
            }
        ),
        
        # Time slider and interval
        html.Div([
            dcc.Slider(
                id='time-slider',
                min=0,
                max=len(DATES) - 1,
                value=len(DATES) - 1,
                marks={
                    i: date.strftime('%Y-%m')
                    for i, date in enumerate(DATES)
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
    
    # Map
    html.Div([
        dcc.Graph(
            id='covid-map',
            style={
                'height': '77vh',
                'width': '100%'
            },
            config={'displayModeBar': False}
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

# Callback for play/pause button
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

# Callback for time slider animation
@app.callback(
    Output('time-slider', 'value'),
    [Input('interval-component', 'n_intervals'),
     Input('time-slider', 'value')],
    [State('interval-component', 'disabled')]
)
def update_time_slider(n_intervals, slider_value, disabled):
    if disabled:
        return slider_value
    return (slider_value + 1) % len(DATES)

# Callback for map updates
@app.callback(
    Output('covid-map', 'figure'),
    [Input('time-slider', 'value')]
)
def update_map(selected_index):
    selected_date = DATES[selected_index]
    date_data = PROCESSED_DATA[pd.Timestamp(selected_date)]
    
    fig = go.Figure(data=go.Choropleth(
        locations=date_data['iso_code'],
        z=date_data['total_deaths_per_million'],
        text=date_data.apply(
            lambda x: f"Country: {x['location']}<br>"
                     f"Deaths per Million: {int(x['total_deaths_per_million']) if x['total_deaths_per_million'] >= 0 else 'No data'}<br>"
                     f"Total Deaths: {int(x['total_deaths']) if pd.notna(x['total_deaths']) else 'No data'}",
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
        zmax=4000
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

if __name__ == '__main__':
    print("Starting dashboard server...")
    app.run_server(debug=True)