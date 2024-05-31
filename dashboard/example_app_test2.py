# Import packages
from dash import Dash, html, dcc, Input, Output, callback_context
import dash_bootstrap_components as dbc
import dash
import sqlite3
import pandas as pd

# Initialize the app - incorporate a Dash Bootstrap theme
external_stylesheets = [dbc.themes.CERULEAN]
app = Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=False)

# Sidebar layout
sidebar = html.Div(
    [
        dbc.Card(
            [
                html.H4("C alpha"),
                html.Hr(),
                dbc.Nav(
                    [
                        dbc.NavLink("Whole Portfolio", href="/", id="whole_portfolio_link", active="exact"),
                        dbc.NavLink("Subportfolios", href="/subportfolios", id="subportfolios_link", active="exact"),
                        dbc.NavLink("Strategies", href="/strategies", id="strategies_link", active="exact"),
                        dbc.NavLink("Symbols", href="/symbols", id="symbols_link", active="exact"),
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

# Define the main content layout function
def main_content_layout(button_id):
    if button_id == 'whole_portfolio_link':
        return html.Div(
            [
                dbc.Tabs(id='tabs_whole_portfolio', 
                         children=[
                             dbc.Tab(label='Overview', tab_id='whole_portfolio_tab1_overview',
                                     children = []),
                             dbc.Tab(label='Returns', tab_id='whole_portfolio_tab2_returns',
                                     children = [])
                         ]
                ),
                html.Div(id = 'tabs_content')
            ],
            style={
                "marginLeft": "17rem",
                "padding": "0.5rem 0.5rem",
            }
        )
    elif button_id == 'subportfolios_link':
        return html.Div(
            [
                dbc.Tabs(id='tabs_subportfolios', 
                         children=[
                             dbc.Tab(label='Overview', tab_id='subportfolios_tab1_overview',
                                     children = []),
                             dbc.Tab(label='Returns', tab_id='subportfolios_tab2_returns',
                                     children = [])
                         ]
                ),
                html.Div(id = 'tabs_content')
            ],
            style={
                "marginLeft": "17rem",
                "padding": "0.5rem 0.5rem",
            }
        )
    else:
        return []


# Callback to update the main content based on the selected navigation item
@app.callback(
    Output('page_content', 'children'),
    [Input('whole_portfolio_link', 'n_clicks'),
     Input('subportfolios_link', 'n_clicks'),
     Input('strategies_link', 'n_clicks'),
     Input('symbols_link', 'n_clicks')]
)
def page_content_children(n1, n2, n3, n4):
    print('page_content')
    ctx = callback_context
    if not ctx.triggered:
        return main_content_layout("whole_portfolio_link")
    else:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        return main_content_layout(button_id)

# Callback to update the content of the tabs
@app.callback(
    Output('tabs_content', 'children'),
    [Input('tabs_whole_portfolio', 'active_tab')]
)
def whole_portfolio_tab1_overview_children(active_tab):
    print('update')
    print(active_tab)
    if active_tab == 'whole_portfolio_tab1_overview':
        con = sqlite3.connect('../db/calpha.db')
        query = """
            SELECT equity,
                   long_market_value,
                   short_market_value,
                   non_marginable_buying_power,
                   subportfolios_allocation,
                   total_return,
                   absolute_return,
                   daily_return,
                   open_trades_cnt,
                   closed_trades_cnt,
                   win_rate,
                   max_drawdown,
                   max_drawdown_duration,
                   sharpe_ratio,
                   calmar_ratio,
                   sortino_ratio
            FROM whole_portfolio_state
            ORDER BY date DESC
            LIMIT 1"""
        
        s = pd.read_sql(query, con).squeeze()
        s['equity'] = s['equity'].round(2)
        s['long_market_value'] = s['long_market_value'].round(2)
        s['short_market_value'] = s['short_market_value'].round(2)
        s['non_marginable_buying_power'] = s['non_marginable_buying_power'].round(2)
        s['subportfolios_allocation'] = s['subportfolios_allocation'].round(2)
        s['total_return'] = s['total_return'].round(4)
        s['absolute_return'] = s['absolute_return'].round(2)
        s['daily_return'] = s['daily_return'].round(8)
        s['win_rate'] = s['win_rate'].round(2)
        s['max_drawdown'] = s['max_drawdown'].round(4)
        s['sharpe_ratio'] = s['sharpe_ratio'].round(2)
        s['calmar_ratio'] = s['calmar_ratio'].round(2)
        s['sortino_ratio'] = s['sortino_ratio'].round(2)
        
        s = s.rename(index={
            'equity': 'Equity',
            'long_market_value': 'Long market value',
            'short_market_value': 'Short market value',
            'non_marginable_buying_power': 'Buying power',
            'subportfolios_allocation': 'Subportfolios allocation',
            'total_return': 'Total return',
            'absolute_return': 'Total absolute return',
            'daily_return': 'Last daily return',
            'open_trades_cnt': 'Open trades count',
            'closed_trades_cnt': 'Closed trades count',
            'win_rate': 'Win rate',
            'max_drawdown': 'Max drawdown',
            'max_drawdown_duration': 'Max drawdown duration',
            'sharpe_ratio': 'Sharpe ratio',
            'calmar_ratio': 'Calmar ratio',
            'sortino_ratio': 'Sortino ratio'
        })
                
        return generate_metric_elements(s)
    else:
        return html.Div()
    
categories = {
    "Equity": ["Equity", "Long market value", "Short market value", "Buying power", "Subportfolios allocation", 
               "Max drawdown", "Max drawdown duration"],
    "Returns": ["Total return", "Total absolute return", "Last daily return"],
    "Trades": ["Open trades count", "Closed trades count", "Win rate"],
    "Ratios": ["Sharpe ratio", "Calmar ratio", "Sortino ratio"]
}

def generate_metric_elements(series):
    category_elements = []

    for category, metrics in categories.items():
        card_elements = []
        for metric in metrics:
            value = series.get(metric, 'N/A')
            card_elements.append(
                html.Div(
                    [
                        html.H4(metric),
                        html.P(value),
                        html.Br()
                    ]),
                )
        category_elements.append(
            dbc.Col(
                html.Div([
                    html.H2(category),
                    html.Hr(),
                    *card_elements
                ]),
                width=3
            )
        )

    return dbc.Row(category_elements, className="g-3", style = {'marginTop':'0.2rem'})

# App layout
app.layout = html.Div([dcc.Location(id="url"), 
                       sidebar, 
                       html.Div(id="page_content", style={"marginLeft": "1rem", "padding": "2px"})
])


# Run the app
if __name__ == '__main__':
    app.run(debug=True)
