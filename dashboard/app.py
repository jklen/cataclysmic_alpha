# Import packages
from dash import Dash, html, dcc, callback, Output, Input
import pandas as pd
import plotly.express as px
import dash_bootstrap_components as dbc
import sqlite3


# Initialize the app - incorporate a Dash Bootstrap theme
external_stylesheets = [dbc.themes.CERULEAN]
app = Dash(__name__, external_stylesheets=external_stylesheets)

# Sidebar layout
sidebar = html.Div(
    [
        dbc.Card(
            [
                html.H4("C alpha"),
                html.Hr(),
                dbc.Nav(
                    [
                        dbc.NavLink("Prompt 1", href="#", id="prompt-1-link"),
                        dbc.NavLink("Prompt 2", href="#", id="prompt-2-link"),
                        dbc.NavLink("Prompt 3", href="#", id="prompt-3-link"),
                    ],
                    vertical=True,
                    pills=True,
                ),
            ],
            body=True
        ),
    ],
    style={
        "position": "fixed",
        "top": 0,
        "left": 0,
        "bottom": 0,
        "width": "18rem",
        "padding": "0.5rem 0.5rem",
        "backgroundColor": "#f8f9fa",
    },
)

# Tabs layout
tabs = html.Div(
    [
        dbc.Tabs(
            id='tabs',
            children=[
                dbc.Tab(
                    label='Whole portfolio',
                    tab_id = 'tab1',
                    children=[
                        dbc.Row(id='tab1_daily_metrics', style={"padding": "10px"}),
                        dbc.Row([
                            dbc.Col(
                                children=[
                                    dcc.Graph(figure={}, id='tab1_chart1_equity')
                                ],
                                width=9
                            ),
                            dbc.Col(
                                children=[
                                    html.Div('selected metrics', id='tab1_chart1_selected_metrics')
                                ],
                                width=3
                            ),
                        ]),
                        dbc.Row([
                            dbc.Col(
                                [
                                    dcc.Graph(figure={}, id='tab1_chart2_cum_metrics')
                                ],
                                width=6
                            ),
                            dbc.Col(
                                [
                                    dcc.Graph(figure={}, id='tab1_chart3_rolling_metrics')
                                ],
                                width=6
                            ),
                        ]),
                    ]
                ),
                dbc.Tab(
                    label='Subportfolios',
                    tab_id = 'tab2',
                    children=[
                        dbc.Row([html.Div(id='tab2_daily_metrics')]),
                    ]
                ),
                dbc.Tab(
                    label='Strategies',
                    tab_id = 'tab3',
                    children=[
                        dbc.Row([html.Div(id='tab3_strategies_high_level')]),
                    ]
                ),
                dbc.Tab(
                    label='Symbols',
                    tab_id = 'tab4',
                    children=[
                        dbc.Row([
                            dbc.Col(
                                children=[
                                    dcc.Graph(figure={}, id='tab4_chart1')
                                ]
                            ),
                            dbc.Col(
                                children=[
                                    dcc.Graph(figure={}, id='tab4_chart2')
                                ]
                            ),
                        ]),
                    ]
                ),
            ]
        ),
    ],
    style={
        "marginLeft": "18rem",  # Ensure enough margin to prevent overlap with sidebar
        "padding": "0.5rem 0.5rem",
    }
)

# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX tab 1 callbacks XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# Callback to update metrics
@app.callback(
    Output('tab1_daily_metrics', 'children'),
    Input('tabs', 'active_tab')  # You can choose an appropriate input trigger
)
def update_metrics(active_tab):
    con = sqlite3.connect('../db/calpha.db')
    query = """
        select equity,
                total_return,
                absolute_return,
                daily_return,
                open_trades_cnt,
                closed_trades_cnt,
                win_rate,
                max_drawdown,
                max_drawdown_duration,
                sharpe_ratio
        from whole_portfolio_state
        order by date desc
        limit 1"""
        
    if active_tab == 'tab1':
        s = pd.read_sql(query, con).squeeze()
        s['equity'] = s['equity'].round(0)
        s['total_return'] = s['total_return'].round(4)
        s['absolute_return'] = s['absolute_return'].round(0)
        s['daily_return'] = s['daily_return'].round(8)
        s['max_drawdown'] = s['max_drawdown'].round(4)
        s['sharpe_ratio'] = s['sharpe_ratio'].round(2)
    return generate_metric_elements(s)

def generate_metric_elements(series):
    elements = []

    for metric, value in series.items():
        elements.append(
            dbc.Col(
                html.Div([
                    html.H6(metric),
                    html.P(value)
                ]),
                width="auto",
                className="metric-element"
            )
        )
    return elements

# App layout
app.layout = html.Div([sidebar, tabs])

# Run the app
if __name__ == '__main__':
    app.run(debug=True)

# taby
#
# 1. whole portfolio
#   - current metrics ako singletons (equity, total_return %, total absolute return, last daily return, open trades count,
#           closed trades cnt, win rate, max drawdown, max drawdown duration, SR)
#   - line chart - equity v case
#      - ked selectnem periodu, uvidim dane metriky za danu periodu
#   - chart - kumulativne metriky v case
#   - chart - klzave metriky (1w, 1m, 3m - total_return, SR, absolute_return, nr ov trades, traded symbols, ,,,)
#   - tabulka so vsetkymyi metrikami ako v db
# 2. subportfolios
#   - barharty - current metrics v grafoch, grouped podla subportfolia
#   - line chart - equity v case, grouped podla subportfolia
#      - ked selectnem periodu, uvidim dane metriky za danu periodu pre vsetky subportfolia v barchartoch
#   - chart - kumulativna metrika v case podla subportfolioa, + filter na metriku
#   - chart - klzava metrika v case podla subportfolia - fitler na metriku
#   - chart - vaha symbolov v case + filter na subportfolio
#   - tabulka so vsetkymi metrikami ako v db + filter na subportfolio
#   - tabulka so subportfolio info - napr. sposob vazenia, symboly a pod
# 3. strategies
#   - singletons - pocet strategii, pocet long, pocet short, pocet longshort
#   - line chart - equity v case, grouped podla strategie
#      - select periody => metriky za danu periodu
#   - rovnako ako 1, 2
#   - histogramy daily returns strategii
#   - histogramy vynosov z tradov
# 4. symbols
#   - filter podla subportfolia a strategie a symbol
#   - line chart ceny vs. equity strategie na danom symbole
#      - zobrazene trady
#   - tabulka s tradami podla selekcie v charte
#   - line chart - vaha symbolu v case
#   - line chart equity z backtestu vs. nazivo