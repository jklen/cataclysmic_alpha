# Import packages
from dash import Dash, html, dcc, Input, Output
import pandas as pd
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
                        dbc.NavLink("Whole Portfolio", href="#", id="whole-portfolio-link"),
                        dbc.NavLink("Subportfolios", href="#", id="subportfolios-link"),
                        dbc.NavLink("Strategies", href="#", id="strategies-link"),
                        dbc.NavLink("Symbols", href="#", id="symbols-link"),
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
                dbc.Tab(label='Whole portfolio', tab_id='tab1'),
                dbc.Tab(label='Subportfolios', tab_id='tab2'),
                dbc.Tab(label='Strategies', tab_id='tab3'),
                dbc.Tab(label='Symbols', tab_id='tab4'),
            ],
        ),
    ],
    style={
        "marginLeft": "18rem",
        "padding": "0.5rem 0.5rem",
    }
)

# Define the categories and their corresponding metrics
categories = {
    "Equity": ["equity", "long_market_value", "short_market_value", "non_marginable_buying_power", "subportfolios_allocation", "max_drawdown", "max_drawdown_duration"],
    "Returns": ["total_return", "absolute_return", "daily_return"],
    "Trades": ["open_trades_cnt", "closed_trades_cnt", "win_rate"],
    "Ratios": ["sharpe_ratio", "calmar_ratio", "sortino_ratio"]
}

# Callback to update metrics
@app.callback(
    Output('tab-content', 'children'),
    Input('tabs', 'active_tab')
)
def update_metrics(active_tab):
    con = sqlite3.connect('../db/calpha.db')
    query = """
        select equity,
               long_market_value,
               short_market_value,
               non_marginable_buying_power,
               subportfolios_allocation,
               max_drawdown,
               max_drawdown_duration,
               total_return,
               absolute_return,
               daily_return,
               open_trades_cnt,
               closed_trades_cnt,
               win_rate,
               sharpe_ratio,
               calmar_ratio,
               sortino_ratio
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
        s['calmar_ratio'] = s['calmar_ratio'].round(2)
        s['sortino_ratio'] = s['sortino_ratio'].round(2)
        s['win_rate'] = s['win_rate'].round(4)
        con.close()
        return generate_category_elements(s)
    else:
        return html.Div()

def generate_category_elements(series):
    category_elements = []

    for category, metrics in categories.items():
        card_elements = []
        for metric in metrics:
            value = series.get(metric, 'N/A')
            card_elements.append(
                dbc.Card(
                    dbc.CardBody([
                        html.H5(metric),
                        html.P(value)
                    ]),
                    className="mb-4"
                )
            )
        category_elements.append(
            dbc.Col(
                html.Div([
                    html.H3(category),
                    *card_elements
                ]),
                width=3
            )
        )

    return dbc.Row(category_elements, className="g-3")

# App layout
app.layout = html.Div([sidebar, tabs, html.Div(id='tab-content', style={"marginLeft": "18rem", "padding": "20px"})])

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
