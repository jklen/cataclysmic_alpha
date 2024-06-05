# Import packages
from dash import Dash, html, dcc, Input, Output, callback_context
import dash_bootstrap_components as dbc
import dash
import sqlite3
import pandas as pd
import pdb
import plotly.express as px

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
                        dbc.NavLink("Market", href="/market", id="market_link", active="exact")
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
                             dbc.Tab(label='Equity', tab_id='whole_portfolio_tab2_equity',
                                     children = []),
                             dbc.Tab(label='Returns', tab_id='whole_portfolio_tab3_returns',
                                     children = []),
                             dbc.Tab(label='Trades', tab_id='whole_portfolio_tab4_trades',
                                     children = []),
                             dbc.Tab(label='Ratios', tab_id='whole_portfolio_tab5_ratios',
                                     children = [])
                         ]
                ),
                html.Div(id = 'tabs_content_whole_portfolio')
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
                             dbc.Tab(label='Equity', tab_id='subportfolios_tab2_equity',
                                     children = []),
                             dbc.Tab(label='Returns', tab_id='subportfolios_tab3_returns',
                                     children = []),
                             dbc.Tab(label='Trades', tab_id='subportfolios_tab4_trades',
                                     children = []),
                             dbc.Tab(label='Ratios', tab_id='subportfolios_tab5_ratios',
                                     children = [])
                         ]
                ),
                html.Div(id = 'tabs_content_subportfolios')
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
    Output('tabs_content_whole_portfolio', 'children'),
    [Input('tabs_whole_portfolio', 'active_tab')]
)
def tabs_content__children_wp(active_tab):
    print('update')
    print(active_tab)
    con = sqlite3.connect('../db/calpha.db')
    query = """
        SELECT *
        FROM whole_portfolio_state
        ORDER BY date ASC
        """
    df = pd.read_sql(query, con)
    df['equity'] = df['equity'].round(2)
    df['long_market_value'] = df['long_market_value'].round(2)
    df['short_market_value'] = df['short_market_value'].round(2)
    df['non_marginable_buying_power'] = df['non_marginable_buying_power'].round(2)
    df['subportfolios_allocation'] = df['subportfolios_allocation'].round(2)
    df['total_return'] = df['total_return'].round(4)
    df['absolute_return'] = df['absolute_return'].round(2)
    df['daily_return'] = df['daily_return'].round(8)
    df['win_rate'] = df['win_rate'].round(2)
    df['max_drawdown'] = df['max_drawdown'].round(4)
    df['sharpe_ratio'] = df['sharpe_ratio'].round(2)
    df['calmar_ratio'] = df['calmar_ratio'].round(2)
    df['sortino_ratio'] = df['sortino_ratio'].round(2)
    
    if active_tab == 'whole_portfolio_tab1_overview':        
        s = df.tail(1).squeeze()
        
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
                
        return generate_metric_elements_wp(s)
    elif active_tab == 'whole_portfolio_tab2_equity':
        plot1 = px.line(df, x = 'date', y = 'equity', title = 'Equity')
        plot2 = px.line(df, x = 'date', y = 'non_marginable_buying_power', title = 'Buying power')
        plot3 = px.line(df, x = 'date', y = 'long_market_value', title = 'Long market value')
        plot4 = px.line(df, x = 'date', y = 'short_market_value', title = 'Short market value')
        plot5 = px.line(df, x = 'date', y = 'subportfolios_allocation', title = 'Subportfolios allocation')
        plot6 = px.line(df, x = 'date', y = 'max_drawdown', title = 'Max drawdown')
        
        for plot in [plot1, plot2, plot3, plot4, plot5, plot6]:
            plot.update_layout(
                title={
                    'y': 0.9,
                    'x': 0.5,
                    'xanchor': 'center',
                    'yanchor': 'top',
                    'font': {'size': 26}
                }
            )
        
        row1 = dbc.Row([dbc.Col(dcc.Graph(id = 'tab2_plot1', figure = plot1), width = 6),
                        dbc.Col(dcc.Graph(id = 'tab2_plot2', figure = plot2), width = 6)])
        row2 = dbc.Row([dbc.Col(dcc.Graph(id = 'tab2_plot3', figure = plot3), width = 6),
                        dbc.Col(dcc.Graph(id = 'tab2_plot4', figure = plot4), width = 6)])
        row3 = dbc.Row([dbc.Col(dcc.Graph(id = 'tab2_plot5', figure = plot5), width = 6),
                        dbc.Col(dcc.Graph(id = 'tab2_plot6', figure = plot6), width = 6)])
        
        return [row1, row2, row3]
    elif active_tab == 'whole_portfolio_tab3_returns':
        plot1 = px.line(df, x = 'date', y = 'total_return', title = 'Total return')
        plot2 = px.line(df, x = 'date', y = 'absolute_return', title = 'Total absolute return')
        plot3 = px.line(df, x = 'date', y = 'daily_return', title = 'Daily returns')
        plot4 = px.histogram(df, x = 'daily_return', title = 'Daily returns histogram')
        
        for plot in [plot1, plot2, plot3, plot4]:
            plot.update_layout(
                title={
                    'y': 0.9,
                    'x': 0.5,
                    'xanchor': 'center',
                    'yanchor': 'top',
                    'font': {'size': 26}
                }
            )
        
        row1 = dbc.Row([dbc.Col(dcc.Graph(id = 'tab3_plot1', figure = plot1), width = 6),
                        dbc.Col(dcc.Graph(id = 'tab3_plot2', figure = plot2), width = 6)])
        row2 = dbc.Row([dbc.Col(dcc.Graph(id = 'tab3_plot3', figure = plot3), width = 6),
                        dbc.Col(dcc.Graph(id = 'tab3_plot4', figure = plot4), width = 6)])
        
        return [row1, row2]
    
    elif active_tab == 'whole_portfolio_tab4_trades':
        plot1 = px.line(df, x = 'date', y = 'open_trades_cnt', title = 'Open trades count')
        plot2 = px.line(df, x = 'date', y = 'closed_trades_cnt', title = 'Closed trades count')
        plot3 = px.line(df, x = 'date', y = 'win_rate', title = 'Win rate')
        
        for plot in [plot1, plot2, plot3]:
            plot.update_layout(
                title={
                    'y': 0.9,
                    'x': 0.5,
                    'xanchor': 'center',
                    'yanchor': 'top',
                    'font': {'size': 26}
                }
            )
        
        row1 = dbc.Row([dbc.Col(dcc.Graph(id = 'tab4_plot1', figure = plot1), width = 6),
                        dbc.Col(dcc.Graph(id = 'tab4_plot2', figure = plot2), width = 6)])
        row2 = dbc.Row([dbc.Col(dcc.Graph(id = 'tab4_plot3', figure = plot3), width = 6)])
        
        return [row1, row2]
    
    elif active_tab == 'whole_portfolio_tab5_ratios':
        plot1 = px.line(df, x = 'date', y = 'sharpe_ratio', title = 'Sharpe ratio')
        plot2 = px.line(df, x = 'date', y = 'calmar_ratio', title = 'Calmar ratio')
        plot3 = px.line(df, x = 'date', y = 'sortino_ratio', title = 'Sortino ratio')
        
        for plot in [plot1, plot2, plot3]:
            plot.update_layout(
                title={
                    'y': 0.9,
                    'x': 0.5,
                    'xanchor': 'center',
                    'yanchor': 'top',
                    'font': {'size': 26}
                }
            )
        
        row1 = dbc.Row([dbc.Col(dcc.Graph(id = 'tab5_plot1', figure = plot1), width = 6),
                        dbc.Col(dcc.Graph(id = 'tab5_plot2', figure = plot2), width = 6)])
        row2 = dbc.Row([dbc.Col(dcc.Graph(id = 'tab5_plot3', figure = plot3), width = 6)])
        
        return [row1, row2]
    else:
        return html.Div()
    
categories_wp = {
    "Equity": ["Equity", "Long market value", "Short market value", "Buying power", "Subportfolios allocation", 
               "Max drawdown", "Max drawdown duration"],
    "Returns": ["Total return", "Total absolute return", "Last daily return"],
    "Trades": ["Open trades count", "Closed trades count", "Win rate"],
    "Ratios": ["Sharpe ratio", "Calmar ratio", "Sortino ratio"]
}

def generate_metric_elements_wp(series):
    category_elements = []

    for category, metrics in categories_wp.items():
        card_elements = []
        for metric in metrics:
            value = series.get(metric, 'N/A')
            card_elements.append(
                html.Div(
                    [
                        html.H4(metric),
                        html.B(value, style = {'font-size': '25px'}),
                        html.Br(),
                        html.Br()
                    ]),
                )
        category_elements.append(
            dbc.Col(
                html.Div([
                    html.H2(category),
                    html.Hr(style = {"width": "70%"}),
                    *card_elements
                ]),
                width=3
            )
        )

    return dbc.Row(category_elements, className="g-3", style = {'marginTop':'0.2rem'})

@app.callback(
    Output('tabs_content_subportfolios', 'children'),
    [Input('tabs_subportfolios', 'active_tab')]
)
def tabs_content__children_subp(active_tab):
    con = sqlite3.connect('../db/calpha.db')
    query = """
        SELECT *
        FROM portfolio_state
        ORDER BY date ASC
        """
    df = pd.read_sql(query, con)
    
    df['equity'] = df['equity'].round(2)
    df['available_cash'] = df['available_cash'].round(2)
    df['total_return'] = df['total_return'].round(4)
    df['absolute_return'] = df['absolute_return'].round(2)
    df['daily_return'] = df['daily_return'].round(8)
    df['open_trades_PL'] = df['open_trades_PL'].round(2)
    df['closed_trades_PL'] = df['closed_trades_PL'].round(2)
    df['win_rate'] = df['win_rate'].round(2)
    df['max_drawdown'] = df['max_drawdown'].round(4)
    df['sharpe_ratio'] = df['sharpe_ratio'].round(2)
    df['calmar_ratio'] = df['calmar_ratio'].round(2)
    df['sortino_ratio'] = df['sortino_ratio'].round(2)
    
    if active_tab == 'subportfolios_tab1_overview':
        df_tab = df.loc[df['date'] == df['date'].max(), :]
        df_tab.rename(columns = {
            'equity':'Equity',
            'available_cash':'Available cash',
            'max_drawdown':'Max drawdown',
            'max_drawdown_duration':'Max drawdown duration',
            'total_return':'Total return',
            'absolute_return':'Total absolute return',
            'daily_return':'Last daily return',
            'open_trades_cnt':'Open trades count',
            'open_trades_PL':'Open trades PL',
            'closed_trades_cnt':'Closed trades count',
            'closed_trades_PL':'Closed trades PL',
            'win_rate':'Win rate',
            'symbols_with_zero_trades_cnt':'Symbols with 0 trades count',
            'symbols_to_open_cnt':'Symbols to open count',
            'symbols_to_close_cnt':'Symbols to close count',
            'sharpe_ratio':'Sharpe ratio',
            'calmar_ratio':'Calmar ratio',
            'sortino_ratio':'Sortino ratio',
            'portfolio_name':'Portfolio'
        }, inplace = True)
        return generate_metric_elements_subp(df_tab)
    
categories_subp = {
    "Equity": [("Equity", "Available cash"), 
               ("Max drawdown", "Max drawdown duration")],
    "Returns": [("Total return", "Total absolute return"), ("Last daily return",)],
    "Trades": [("Open trades count", "Open trades PL"), ("Closed trades count", "Closed trades PL"), 
               ("Win rate", "Symbols with 0 trades count"), ("Symbols to open count", 
               "Symbols to close count")],
    "Ratios": [("Sharpe ratio", "Calmar ratio"), ("Sortino ratio", )]
}

def generate_metric_elements_subp(df):
    category_elements = []

    for category, metrics in categories_subp.items():
        card_elements = []
        for metric in metrics:
            try:
                metric[1]
                df_f = df[['Portfolio', metric[0], metric[1]]]
            except:
                df_f = df[['Portfolio', metric[0]]]
            card_elements.append(
                html.Div(
                    [
                        #html.H4(metric),
                        dbc.Card(
                            dbc.Table.from_dataframe(df_f,
                                                    striped = True,
                                                    header = True,
                                                    style = {'marginBottom':'15px',
                                                             'marginTop':'10px'}),
                            style = {'marginTop':'15px'}
                        )
                    ]),
                )
        category_elements.append(
            dbc.Col(
                html.Div([
                    html.H2(category),
                    html.Hr(style = {"width": "70%"}),
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
