# Import packages
from dash import Dash, html, dcc, Input, Output, callback_context, State, dash_table, Patch
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
import dash
import sqlite3
import pandas as pd
import pdb
import plotly.express as px
import plotly.io as pio
import plotly.figure_factory as ff
import numpy as np
import os
import sys
from datetime import datetime
from utils import get_alpaca_data

# Initialize the app - incorporate a Dash Bootstrap theme
external_stylesheets = [dbc.themes.CERULEAN]
app = Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=False)

symbol_parcoord_metrics_overview = ['closed_trades_cnt', 'closed_trades_PL', 'win_rate', 'total_return', 'sharpe_ratio']
symbol_parcoord_metrics_positions = ['open_trade_PL', 'open_trade_total_return', 'daily_return', 'cost_basis', 'market_value', \
    'days_opened']

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
        html.Div(id = 'prompts_symbol',
                 children = [

                        dmc.MultiSelect(
                            id = 'select_portfolio',
                            data = [],
                            searchable = True,
                            maxValues = 20,
                            hidePickedOptions=True
                            
                        ) ,
                        
                        dmc.MultiSelect(
                            id = 'select_strategy',
                            data = [],
                            searchable = True,
                            maxValues = 20,
                            hidePickedOptions=True
                            
                        ), 
                        
                        dmc.MultiSelect(
                            id = 'select_symbols',
                            data = [],
                            searchable = True,
                            maxValues = 20,
                            hidePickedOptions=True
                            
                        )                   
                    
                 ],
                 style = {'display':'inline'}),
        html.Div(id = 'prompts_symbol_returns',
                 children = [

                        dmc.RadioGroup([dmc.Radio(l, value=k) for k, l in [['alpaca', 'Alpaca'], ['yf', 'Yahoo Finance']]],
                            id="radio_datapref",
                            value="alpaca",
                            label="Data preference",
                            size="lg")
            
                ],
                 style = {'display':'inline'})],
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
def main_content_layout(pathname):
    if pathname == '/':
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
    elif pathname == '/subportfolios':
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
    elif pathname == '/symbols':
        return html.Div(
            [
                dbc.Tabs(id='tabs_symbols', 
                         children=[
                             dbc.Tab(label='Overview', tab_id='symbols_tab1_overview',
                                     children = []),
                             dbc.Tab(label='Open positions', tab_id='symbols_tab2_positions',
                                     children = []),
                             dbc.Tab(label='Returns', tab_id='symbols_tab3_returns',
                                     children = []),
                             dbc.Tab(label='Trades', tab_id='symbols_tab4_trades',
                                     children = []),
                             dbc.Tab(label='Ratios', tab_id='symbols_tab5_ratios',
                                     children = []),
                             dbc.Tab(label='Data', tab_id='symbols_tab6_data',
                                     children = [])
                         ]
                ),
                html.Div(id = 'tabs_content_symbols'),
                dcc.Store(id='parcoord_filters', data={}),
                dcc.Store(id = 'parcoord_positions_filters', data = {})
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
    [Input('url', 'pathname')]
)
def page_content_children(pathname):
    print('page_content callback')
    
    return main_content_layout(pathname)

# WHOLE PORTFOLIO CALLBACKS

@app.callback(
    Output('tabs_content_whole_portfolio', 'children'),
    [Input('tabs_whole_portfolio', 'active_tab')]
)
def tabs_content__children_wp(active_tab):
    print('tabs content callback')
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
        
        row1 = dbc.Row([dbc.Col(dcc.Graph(id = 'wp_tab2_plot1', figure = plot1), width = 6),
                        dbc.Col(dcc.Graph(id = 'wp_tab2_plot2', figure = plot2), width = 6)])
        row2 = dbc.Row([dbc.Col(dcc.Graph(id = 'wp_tab2_plot3', figure = plot3), width = 6),
                        dbc.Col(dcc.Graph(id = 'wp_tab2_plot4', figure = plot4), width = 6)])
        row3 = dbc.Row([dbc.Col(dcc.Graph(id = 'wp_tab2_plot5', figure = plot5), width = 6),
                        dbc.Col(dcc.Graph(id = 'wp_tab2_plot6', figure = plot6), width = 6)])
        
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
        
        row1 = dbc.Row([dbc.Col(dcc.Graph(id = 'wp_tab3_plot1', figure = plot1), width = 6),
                        dbc.Col(dcc.Graph(id = 'wp_tab3_plot2', figure = plot2), width = 6)])
        row2 = dbc.Row([dbc.Col(dcc.Graph(id = 'wp_tab3_plot3', figure = plot3), width = 6),
                        dbc.Col(dcc.Graph(id = 'wp_tab3_plot4', figure = plot4), width = 6)])
        
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
        
        row1 = dbc.Row([dbc.Col(dcc.Graph(id = 'wp_tab4_plot1', figure = plot1), width = 6),
                        dbc.Col(dcc.Graph(id = 'wp_tab4_plot2', figure = plot2), width = 6)])
        row2 = dbc.Row([dbc.Col(dcc.Graph(id = 'wp_tab4_plot3', figure = plot3), width = 6)])
        
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
        
        row1 = dbc.Row([dbc.Col(dcc.Graph(id = 'wp_tab5_plot1', figure = plot1), width = 6),
                        dbc.Col(dcc.Graph(id = 'wp_tab5_plot2', figure = plot2), width = 6)])
        row2 = dbc.Row([dbc.Col(dcc.Graph(id = 'wp_tab5_plot3', figure = plot3), width = 6)])
        
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

# PORTFOLIOS CALLBACKS

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
    elif active_tab == 'subportfolios_tab2_equity':
        plot1 = px.line(df, x = 'date', y = 'equity', color = 'portfolio_name', title = 'Equity')
        plot2 = px.line(df, x = 'date', y = 'available_cash', color = 'portfolio_name', title = 'Available cash')
        plot3 = px.line(df, x = 'date', y = 'max_drawdown', color = 'portfolio_name', title = 'Max drawdown')
        plot4 = px.line(df, x = 'date', y = 'max_drawdown_duration', color = 'portfolio_name', title = 'Max drawdown duration')
        
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
        
        row1 = dbc.Row([dbc.Col(dcc.Graph(id = 'sp_tab2_plot1', figure = plot1), width = 6),
                        dbc.Col(dcc.Graph(id = 'sp_tab2_plot2', figure = plot2), width = 6)])
        row2 = dbc.Row([dbc.Col(dcc.Graph(id = 'sp_tab2_plot3', figure = plot3), width = 6),
                        dbc.Col(dcc.Graph(id = 'sp_tab2_plot4', figure = plot4), width = 6)])
        
        return [row1, row2]
    elif active_tab == 'subportfolios_tab3_returns':
        plot1 = px.line(df, x = 'date', y = 'total_return', color = 'portfolio_name', title = 'Total return')
        plot2 = px.line(df, x = 'date', y = 'absolute_return', color = 'portfolio_name', title = 'Total absolute return')
        plot3 = px.line(df, x = 'date', y = 'daily_return', color = 'portfolio_name', title = 'Daily returns')
        
        df_daily_ret = df.pivot_table(index=df.index, columns='portfolio_name', values='daily_return')
        daily_ret = [df_daily_ret[column].dropna().tolist() for column in df_daily_ret.columns]
        plot4 = ff.create_distplot(daily_ret, group_labels = df_daily_ret.columns.tolist(),
                                   show_hist = False)
        plot4.update_layout(title_text='Daily returns distplot')
        
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
        
        row1 = dbc.Row([dbc.Col(dcc.Graph(id = 'sp_tab3_plot1', figure = plot1), width = 6),
                        dbc.Col(dcc.Graph(id = 'sp_tab3_plot2', figure = plot2), width = 6)])
        row2 = dbc.Row([dbc.Col(dcc.Graph(id = 'sp_tab3_plot3', figure = plot3), width = 6),
                        dbc.Col(dcc.Graph(id = 'sp_tab3_plot4', figure = plot4), width = 6)])
        
        return [row1, row2]
    
    elif active_tab == 'subportfolios_tab4_trades':
        plot1 = px.line(df, x = 'date', y = 'open_trades_cnt', color = 'portfolio_name', title = 'Open trades count')
        plot2 = px.line(df, x = 'date', y = 'open_trades_PL', color = 'portfolio_name', title = 'Open trades PL')
        plot3 = px.line(df, x = 'date', y = 'closed_trades_cnt', color = 'portfolio_name', title = 'Closed trades count')
        plot4 = px.line(df, x = 'date', y = 'closed_trades_PL', color = 'portfolio_name', title = 'Closed trades PL')
        plot5 = px.line(df, x = 'date', y = 'win_rate', color = 'portfolio_name', title = 'Win rate')
        plot6 = px.line(df, x = 'date', y = 'symbols_to_open_cnt', color = 'portfolio_name', title = 'Symblos to open count')
        plot7 = px.line(df, x = 'date', y = 'symbols_to_close_cnt', color = 'portfolio_name', title = 'Symblos to close count')
        
        for plot in [plot1, plot2, plot3, plot4, plot5, plot6, plot7]:
            plot.update_layout(
                title={
                    'y': 0.9,
                    'x': 0.5,
                    'xanchor': 'center',
                    'yanchor': 'top',
                    'font': {'size': 26}
                }
            )
        
        row1 = dbc.Row([dbc.Col(dcc.Graph(id = 'sp_tab4_plot1', figure = plot1), width = 6),
                        dbc.Col(dcc.Graph(id = 'sp_tab4_plot2', figure = plot2), width = 6)])
        row2 = dbc.Row([dbc.Col(dcc.Graph(id = 'sp_tab4_plot3', figure = plot3), width = 6),
                        dbc.Col(dcc.Graph(id = 'sp_tab4_plot4', figure = plot4), width = 6)])
        row3 = dbc.Row([dbc.Col(dcc.Graph(id = 'sp_tab4_plot5', figure = plot5), width = 6),
                        dbc.Col(dcc.Graph(id = 'sp_tab4_plot6', figure = plot6), width = 6)])
        row4 = dbc.Row([dbc.Col(dcc.Graph(id = 'sp_tab4_plot7', figure = plot7), width = 6)])
        
        return [row1, row2, row3, row4]
    
    elif active_tab == 'subportfolios_tab5_ratios':
        plot1 = px.line(df, x = 'date', y = 'sharpe_ratio', color = 'portfolio_name', title = 'Sharpe ratio')
        plot2 = px.line(df, x = 'date', y = 'calmar_ratio', color = 'portfolio_name', title = 'Calmar ratio')
        plot3 = px.line(df, x = 'date', y = 'sortino_ratio', color = 'portfolio_name', title = 'Sortino ratio')
        
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
        
        row1 = dbc.Row([dbc.Col(dcc.Graph(id = 'sp_tab5_plot1', figure = plot1), width = 6),
                        dbc.Col(dcc.Graph(id = 'sp_tab5_plot2', figure = plot2), width = 6)])
        row2 = dbc.Row([dbc.Col(dcc.Graph(id = 'sp_tab5_plot3', figure = plot3), width = 6)])
        
        return [row1, row2]
    else:
        return html.Div()
    
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

# SYMBOL PROMPTS CALLBACKS

@app.callback(
    Output('prompts_symbol', 'style'),
    [Input('url', 'pathname')]
)
def prompts_style(pathname):   
    if pathname == '/symbols':
        return {'display':'inline'}
    else:
        return {'display':'none'}   
    
@app.callback(
    Output('select_portfolio', 'data'),
    [Input('url', 'pathname')]
)
def select_portfolio__data(pathname):
    if pathname == '/symbols':
        con = sqlite3.connect('../db/calpha.db')
        df = pd.read_sql('select distinct portfolio from symbol_state where date = (select max(date) from symbol_state)', con)
        portfolios = df['portfolio'].sort_values().to_list()
        con.close()
    else:
        portfolios = None
    
    return portfolios

@app.callback(
    Output('select_strategy', 'data'),
    [Input('select_portfolio', 'value')]
)
def select_strategy__data(portfolios):
    con = sqlite3.connect('../db/calpha.db')
    df = pd.read_sql("""select portfolio, strategy 
                     from symbol_state 
                     where date = (select max(date) from symbol_state
                     group by portfolio, strategy)
                     """, con)
    if portfolios:
        strategies = df.loc[df['portfolio'].isin(portfolios), 'strategy'].unique()
    else:
        strategies = df['strategy'].unique()
    
    return strategies

@app.callback(
    Output('select_symbols', 'data'),
    Input('select_portfolio', 'value'),
    Input('select_strategy', 'value'),
    Input('tabs_symbols', 'active_tab')
)
def select_strategy__data(portfolios, strategies, tab):
    con = sqlite3.connect('../db/calpha.db')
    df = pd.read_sql("""select portfolio, strategy, symbol, is_open
                     from symbol_state 
                     where date = (select max(date) from symbol_state
                     group by portfolio, strategy, symbol)
                     """, con)
    
    if tab == 'symbols_tab2_positions':
        df = df.loc[df['is_open'] == 'Y', :]

    if portfolios:
        df = df.loc[df['portfolio'].isin(portfolios), :]
    
    if strategies:
        df = df.loc[df['strategy'].isin(strategies), :]
        
    data = [{"group": portfolio, "items": list(group["symbol"])}
            for portfolio, group in df.groupby("portfolio")]
        
    return data

# SYMBOL CALLBACKS

@app.callback(
    Output('tabs_content_symbols', 'children'),
    [Input('tabs_symbols', 'active_tab')]
)
def tabs_content_symbols__children(active_tab):
    print('tabs content callback')
    
    
    if active_tab == 'symbols_tab1_overview':
        
        row1 = dbc.Row([dbc.Col(html.Div(id = 'symbol_tab1_chart1'), width = 12)])
        row2 = dbc.Row([dbc.Col(html.Div(id = 'symbol_tab1_table'), width = 12)])
        
        
        return [row1 ,row2]
    elif active_tab == 'symbols_tab2_positions':
        
        row1 = dbc.Row([dbc.Col(html.Div(id = 'symbol_tab2_chart1'), width = 12)])
        row2 = dbc.Row([dbc.Col(html.Div(id = 'symbol_tab2_table'), width = 12)])
        
        
        return [row1 ,row2]
    elif active_tab == 'symbols_tab3_returns':
        
        row1 = dbc.Row([dbc.Col(html.Div(id = 'symbol_tab3_chart1'), width = 12)])
        row2 = dbc.Row([dbc.Col(html.Div(id = 'symbol_tab3_chart3'), width = 6),
                        dbc.Col(html.Div(id = 'symbol_tab3_chart4'), width = 6)])
        row3 = dbc.Row([dbc.Col(html.Div(id = 'symbol_tab3_chart5'), width = 6),
                        dbc.Col(html.Div(id = 'symbol_tab3_chart6'), width = 6)])
        row4 = dbc.Row([dbc.Col(html.Div(id = 'symbol_tab3_chart7'), width = 6),
                        dbc.Col(html.Div(id = 'symbol_tab3_chart8'), width = 6)])
        row5 = dbc.Row([dbc.Col(html.Div(id = 'symbol_tab3_chart9'), width = 6)])
        
        return [row1, row2, row3, row4, row5]
    
# SYMBOL CALLBACKS - tab 1 - overview
    
@app.callback(
    Output('symbol_tab1_chart1', 'children'),
    [Input('select_portfolio', 'value'),
     Input('select_strategy', 'value'),
     Input('select_symbols', 'value')]
)
def symbol_tab1_plot1_figure(portfolios, strategies, symbols):
    print('symbol tab 1 callback')
    print(portfolios, strategies, symbols)
    con = sqlite3.connect('../db/calpha.db')
    df = pd.read_sql('select * from symbol_state', con)
        
    if portfolios:
        df = df.loc[df['portfolio'].isin(portfolios), :]
    
    if strategies:
        df = df.loc[df['strategy'].isin(strategies), :]
    
    if symbols:
        df = df.loc[df['symbol'].isin(symbols), :]
        
        
    df_plot = df.loc[df['date'] == df['date'].max(), :]
    
    plot1 = px.parallel_coordinates(
        df_plot,
        dimensions=symbol_parcoord_metrics_overview
    )    
    
    return dcc.Graph(id = 'symbol_tab1_parallel_plot', figure = plot1)

@app.callback(
    Output('symbol_tab1_table', 'children'),
    [Input('parcoord_filters', 'data'),
     Input('select_portfolio', 'value'),
     Input('select_strategy', 'value'),
     Input('select_symbols', 'value')]
)
def symbol_tab1_table__children(data, portfolios, strategies, symbols):
    print('restyleData callback')
    print(data)
    con = sqlite3.connect('../db/calpha.db')
    df = pd.read_sql('select * from symbol_state', con)
    columns = ['symbol', 'strategy', 'portfolio']
    columns.extend(symbol_parcoord_metrics_overview)
    df = df.loc[df['date'] == df['date'].max(), columns]
    
    if portfolios:
        df = df.loc[df['portfolio'].isin(portfolios), :]
    
    if strategies:
        df = df.loc[df['strategy'].isin(strategies), :]
    
    if symbols:
        df = df.loc[df['symbol'].isin(symbols), :]
        
    if data:
        dff = df.copy()
        for col in data:
            if data[col]:
                rng = data[col][0]
                if isinstance(rng[0], list):
                    # if multiple choices combine df
                    dff3 = pd.DataFrame(columns=df.columns)
                    for i in rng:
                        dff2 = dff[dff[col].between(i[0], i[1])]
                        dff3 = pd.concat([dff3, dff2])
                    dff = dff3
                else:
                    # if one choice
                    dff = dff[dff[col].between(rng[0], rng[1])]
    else:
        dff = df
    
    table = dash_table.DataTable(dff.to_dict('records'), [{"name": i, "id": i} for i in dff.columns],
                                 row_selectable='multi',
                                 id = 'symbol_parcoord_table',)
    
    return table

@app.callback(
    Output('parcoord_filters', 'data'),
    Input("symbol_tab1_parallel_plot", "restyleData")
)
def updateFilters(data):
    if data:
        key = list(data[0].keys())[0]
        col = symbol_parcoord_metrics_overview[int(key.split('[')[1].split(']')[0])]
        newData = Patch()
        newData[col] = data[0][key]
        return newData
    return {}

@app.callback(Output('symbol_tab1_parallel_plot', 'figure'), 
              Input('symbol_parcoord_table', 'selected_rows'),
              State('symbol_tab1_parallel_plot', 'figure'),
              State('symbol_parcoord_table', 'data'))
def pick(rows, figure, table_data):
    if rows is None:
        raise PreventUpdate
    df = pd.DataFrame.from_dict(table_data)
    rows_list = df[symbol_parcoord_metrics_overview].loc[rows].values.tolist()
    #pdb.set_trace()
    for i, v in enumerate(figure.get('data')[0].get('dimensions')):
        constraint_range = []
        for row in rows_list:
            if row[i] == 0:
                start_range = -0.000000005
                end_range = 0.
            else:
                start_range = row[i] - abs(row[i])/100_000
                end_range = row[i]
            constraint_range.append([start_range, end_range])   
        v.update({'constraintrange': constraint_range})
    return figure

# SYMBOL CALLBACKS - tab2 - open positions

@app.callback(
    Output('symbol_tab2_chart1', 'children'),
    [Input('select_portfolio', 'value'),
     Input('select_strategy', 'value'),
     Input('select_symbols', 'value')]
)
def symbol_tab2_plot1_figure(portfolios, strategies, symbols):
    con = sqlite3.connect('../db/calpha.db')
    df = pd.read_sql("select * from symbol_state where is_open = 'Y'", con)
        
    if portfolios:
        df = df.loc[df['portfolio'].isin(portfolios), :]
    
    if strategies:
        df = df.loc[df['strategy'].isin(strategies), :]
    
    if symbols:
        df = df.loc[df['symbol'].isin(symbols), :]
        
        
    df_plot = df.loc[df['date'] == df['date'].max(), :]
    
    plot1 = px.parallel_coordinates(
        df_plot,
        dimensions=symbol_parcoord_metrics_positions
    )    
    
    return dcc.Graph(id = 'symbol_tab2_parallel_plot', figure = plot1)

@app.callback(
    Output('symbol_tab2_table', 'children'),
    [Input('parcoord_positions_filters', 'data'),
     Input('select_portfolio', 'value'),
     Input('select_strategy', 'value'),
     Input('select_symbols', 'value')]
)
def symbol_tab1_table__children(data, portfolios, strategies, symbols):
    con = sqlite3.connect('../db/calpha.db')
    df = pd.read_sql("select * from symbol_state where is_open = 'Y'", con)
    columns = ['symbol', 'strategy', 'portfolio', 'side']
    columns.extend(symbol_parcoord_metrics_positions)
    df = df.loc[df['date'] == df['date'].max(), columns]
    
    if portfolios:
        df = df.loc[df['portfolio'].isin(portfolios), :]
    
    if strategies:
        df = df.loc[df['strategy'].isin(strategies), :]
    
    if symbols:
        df = df.loc[df['symbol'].isin(symbols), :]
        
    if data:
        dff = df.copy()
        for col in data:
            if data[col]:
                rng = data[col][0]
                if isinstance(rng[0], list):
                    # if multiple choices combine df
                    dff3 = pd.DataFrame(columns=df.columns)
                    for i in rng:
                        dff2 = dff[dff[col].between(i[0], i[1])]
                        dff3 = pd.concat([dff3, dff2])
                    dff = dff3
                else:
                    # if one choice
                    dff = dff[dff[col].between(rng[0], rng[1])]
    else:
        dff = df
    
    table = dash_table.DataTable(dff.to_dict('records'), [{"name": i, "id": i} for i in dff.columns],
                                 row_selectable='multi',
                                 id = 'symbol_parcoord_table_positions')
    
    return table

@app.callback(
    Output('parcoord_positions_filters', 'data'),
    Input("symbol_tab2_parallel_plot", "restyleData")
)
def updateFilters(data):
    if data:
        key = list(data[0].keys())[0]
        col = symbol_parcoord_metrics_positions[int(key.split('[')[1].split(']')[0])]
        newData = Patch()
        newData[col] = data[0][key]
        return newData
    return {}

@app.callback(Output('symbol_tab2_parallel_plot', 'figure'), 
              Input('symbol_parcoord_table_positions', 'selected_rows'),
              State('symbol_tab2_parallel_plot', 'figure'),
              State('symbol_parcoord_table_positions', 'data'))
def pick(rows, figure, table_data):
    if rows is None:
        raise PreventUpdate
    df = pd.DataFrame.from_dict(table_data)
    rows_list = df[symbol_parcoord_metrics_positions].loc[rows].values.tolist()
    #pdb.set_trace()
    for i, v in enumerate(figure.get('data')[0].get('dimensions')):
        constraint_range = []
        for row in rows_list:
            if row[i] == 0:
                start_range = -0.000000005
                end_range = 0.
            else:
                start_range = row[i] - abs(row[i])/100_000
                end_range = row[i]
            constraint_range.append([start_range, end_range])   
        v.update({'constraintrange': constraint_range})
    return figure

# SYMBOL CALLBACKS - tab 3 - returns
    
@app.callback(
    Output('symbol_tab3_chart1', 'children'),
    [Input('select_symbols', 'value')]
)
def symbol_tab3_plot1_figure(symbols):
    if symbols:
        df = get_alpaca_data(symbols, 
                   datetime(2000, 1, 1), 
                   datetime.today().date(), 
                   5)
    
        plot1 = px.line(df,
                        x = 'timestamp',
                        y = 'close',
                        color = 'symbol')
    else:
        plot1 = px.line()
    
    return dcc.Graph(id = 'symbol_tab3_price', figure = plot1)
    

#TODO symbols tab:
#   sekcie overview, open positions, returns, trades, ratios
#   overview 
#      - polar chart s metrikami (posledne hodnoty) + tabulka pod:
#           closed_trades_cnt
#           closed_trades_pl
#           days since last closed trade
#           win_rate
#           sharpe, calmar, sortino
#           total return
#           max drawdown, max drawdown duration
#           absolute return
#   open positions
#      - polar chart a tabulka pod:
#           - symbol, trade total return, trade PL
#           - cost basis, daily return, days since open, side, cost basis a market value
#   returns (v case)
#       close price symbolu, total return, 
#       absolute return, daily return, 
#       histogram open trades daily returns
#       max drawdown, max drawdown period, 
#       korelacnu maticu daily returns  symbolov
#   trades ( v case)
#       closed trades cnt, closed trades pl, 
#       win rate, closed trades return histogram, closed trades PL histogram
#   ratios (v case)
#       sharpe, calmar, sortino
#   data
#       datatable posledneho runu

#   prompty (na line charty)
#      filter by - portfolio/strategy (select)
#      select symbol - symbols gouped by filter by (multiselect)

# App layout
app.layout = dmc.MantineProvider(html.Div([dcc.Location(id="url"), 
                       sidebar, 
                       html.Div(id="page_content", style={"marginLeft": "1rem", "padding": "2px"})
]))


# Run the app
if __name__ == '__main__':
    app.run(debug=True)
