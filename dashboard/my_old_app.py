
import dash

import dash_core_components as dcc  

import dash_html_components as html

from plotly.graph_objs import Figure, Scatter

from dash.dependencies import Input, Output

import numpy as np

import pandas as pd

from datetime import datetime

import io

import base64

 

app = dash.Dash(__name__)

app.css.append_css({'external_url':'https://codepen.io/amyoshino/pen/jzXypZ.css'})

#app.config['suppress_callback_exceptions']=True

 

 

styles = {

    'tab':{'backgroundColor':'#fdfdfd',

           'padding':'10px'},

    'selected_tab':{'backgroundColor':'#D1FFF0',

                    'padding':'10px'}

}

   

def read_df(time_dim):

    df = pd.read_csv('data\\df_' + time_dim + '.tsv', sep = '\t')

    df.loc[:, 'date'] = pd.to_datetime(df['date'])

    df.set_index(['date', 'id_typuct'], inplace = True)

    return df

 

def read_jira(time_dim):

    df = pd.read_csv('data\\df_jira_' + time_dim + '.tsv', sep = '\t')

    df.loc[:, 'date'] = pd.to_datetime(df['date'])

    df.set_index(['date', 'project', 'digi_proces'], inplace = True)

    return df

 

def read_banks72(time_dim):

    df = pd.read_csv('data\\df_banks72_' + time_dim + '.tsv', sep = '\t')

    df.loc[:, 'date'] = pd.to_datetime(df['date'])

    df.set_index(['date', 'id_typuct'], inplace = True)

    return df

 

def read_ocr(time_dim):

    df = pd.read_csv('data\\df_ocr_' + time_dim + '.tsv', sep = '\t')

    df.loc[:, 'date'] = pd.to_datetime(df['date'])

    df.set_index('date', inplace = True)

    return df

 

def read_logins(time_dim):

    df = pd.read_csv('data\\df_logins_' + time_dim + '.tsv', sep = '\t')

    df.loc[:, 'date'] = pd.to_datetime(df['date'])

    df.set_index('date', inplace = True)

    return df

 

def read_pmix(time_dim):

    df = pd.read_csv('data\\df_pmix_' + time_dim + '.tsv', sep = '\t')

    df.loc[:, 'date'] = pd.to_datetime(df['date'])

    df.set_index('date', inplace = True)

    return df

 

def read_trans(time_dim):

    df = pd.read_csv('data\\df_trans_out_' + time_dim + '.tsv', sep = '\t')

    df.loc[:, 'date'] = pd.to_datetime(df['date'])

    #df.set_index(['date', 'id_typuct', 'pri_vklad', 'kat_txn'], inplace = True)

    return df

 

def calculate_assumption(last_date, period, x):

    last_date_period = last_date.to_period(period)

    period_start = last_date_period.start_time

    period_end = last_date_period.end_time

   

    if period == 'W':

        days_since_period_start = last_date.dayofweek + 1

        days_in_period = 7

    elif period == 'M':

        days_since_period_start = last_date.day

        days_in_period = last_date.daysinmonth

    elif period == 'Q':

        days_since_period_start = last_date - period_start

        days_since_period_start = days_since_period_start/np.timedelta64(1,'D') + 1

       

        days_in_period = period_end - period_start

        days_in_period = days_in_period/np.timedelta64(1,'D') + 1

    elif period == 'Y':

        days_since_period_start = last_date.dayofyear

        days_in_period = 365

   

    x_assumed = (x/days_since_period_start)*days_in_period

   

    return x_assumed

 

 

def lay():

    return html.Div([

                html.Div(id = 'prompts', children = [

                        html.H5('Perioda'),

                        dcc.Dropdown(id = 'dropdown_period',

                                     options = [

                                             {'label':'Denna', 'value':'D'},

                                             {'label':'Tyzdnova', 'value':'W'},

                                             {'label':'Mesacna', 'value':'M'},

                                             {'label':'Kvartalna', 'value':'Q'},

                                             {'label':'Rocna', 'value':'Y'}

                                        ],

                                     value = 'M',

                                     style={'marginBottom': 10, 'marginTop': 5, 'marginLeft':5, 'marginRight':30}),

                        html.H5('Obdobie'),

                        dcc.DatePickerRange(id = 'datepicker_range',

                                            min_date_allowed = datetime(2017, 1, 1), #datetime(2017, 9, 19),

                                            max_date_allowed = datetime(2019, 12, 31), #datetime.now(),

                                            initial_visible_month = datetime.now(),

                                            start_date = datetime(2019,1,1),

                                            end_date = datetime.now(),

                                            calendar_orientation = 'horizontal',

                                     style={'marginBottom': 10, 'marginTop': 5, 'marginLeft':10, 'marginRight':0}),

                        html.Div(id = 'login_prompts', style = {'display':'none'}, children = [

                            html.Hr(),

                            html.H5('Pocet loginov'),

                            dcc.Slider(

                                id = 'slider_logins',

                                marks = {0:'0', 3:'3', 5:'5', 8:'8', 10:'10'},

                                min = 0,

                                max = 10,

                                value = 4,

                                dots = False,

                                step = 1

                            ),

                            html.Div(id = 'slider_logins_output', style = {'marginTop':25}),

                            html.H5('Suma odchazajucich transakcii'),

                            dcc.Slider(

                                id = 'slider_trans',

                                marks = {0:'0', 200:'200', 500:'500', 700:'700', 1000:'1000'},

                                min = 0,

                                max = 1000,

                                value = 200,

                                dots = False,

                                step = 10

                            ),

                            html.Div(id = 'slider_trans_output', style = {'marginTop':25})

                        ]),

                        html.Div(id = 'pmix_prompts', style = {'display':'none'}, children = [

                                html.Hr(),

                                html.H5('Operator'),

                                dcc.RadioItems(id = 'radio_pmix',

                                             options = [{'label':'AND', 'value':'and'},

                                                        {'label':'OR', 'value':'or'}],

                                            value = 'and',

                                            style={'marginBottom': 10, 'marginTop': 5, 'marginLeft':5, 'marginRight':30},

                                            labelStyle = {'display':'inline-block'}),

                                html.H5('Produkt'),

                                dcc.Checklist(id = 'checklist_pmix',

                                              options = [{'label':'Bezny ucet', 'value':'70_account'},

                                                         {'label':'Sporiaci ucet', 'value':'72_sporenie'},

                                                         {'label':'Sysliaci ucet', 'value':'71_syslenie'},

                                                         {'label':'Google pay', 'value':'gpay'}],

                                            values = ['70_account', '72_sporenie', '71_syslenie', 'gpay'],

                                            style={'marginBottom': 10, 'marginTop': 5, 'marginLeft':5, 'marginRight':30})

                       ]),

                        html.Div(id = 'trans_prompts', style = {'display':'none'}, children = [

                                html.Hr(),

                                html.H5('Typ uctu'),

                                dcc.Dropdown(id = 'dropdown_trans_ucet',

                                             options = [{'label':'Bezny ucet', 'value':70},

                                                        {'label':'Sporiaci ucet', 'value':72},

                                                        {'label':'Sysliaci ucet', 'value':71}],

                                            value = 70,

                                            style={'marginBottom': 10, 'marginTop': 5, 'marginLeft':5, 'marginRight':30}),

                                html.H5('Typ transakcie'),

                                dcc.RadioItems(id = 'radio_trans_vklad',

                                              options = [{'label':'Prichadzajuca', 'value':1},

                                                         {'label':'Odchadzajuca', 'value':0}],

                                            value = 1,

                                            style={'marginBottom': 10, 'marginTop': 5, 'marginLeft':5, 'marginRight':30},

                                            labelStyle = {'display':'inline-block'}),

                                html.H5('Kategoria transakcie'),

                                dcc.Checklist(id = 'checklist_trans', values = [])

                        ]),

                        html.Div(id = 'download', children = [

                                html.A("download excel", id = 'download_link', href="", download = 'data.xlsx', target = '_blank')

                        ])

                        

                ], className = 'two columns'),

               

                html.Div(children = [

                        html.Div([

                                dcc.Tabs(id = 'tabs', value = 'tab1', children = [

                                        dcc.Tab(label = 'Vybrane metriky', value = 'tab1', style = styles['tab'],

                                                selected_style = styles['selected_tab'], children = [

                                                        html.Div(id = 'content1')]),

                                        dcc.Tab(label = 'Ucty', value = 'tab2', style = styles['tab'],

                                                selected_style = styles['selected_tab'], children = [

                                                        html.Div(id = 'content2')]),

                                        dcc.Tab(label = 'Sporenia', value = 'tab3', style = styles['tab'],

                                                selected_style = styles['selected_tab'], children = [

                                                        dcc.Tabs(id = 'tabs_sporenie', value = 'tab1', children = [

                                                                dcc.Tab(label = 'Vseobecne metriky', value = 'tab1', style = styles['tab'],

                                                                        selected_style = styles['selected_tab'], children = [

                                                                                html.Div(id = 'content3_1')]),

                                                                dcc.Tab(label = 'Specificke metriky', value = 'tab2', style = styles['tab'],

                                                                        selected_style = styles['selected_tab'], children = [

                                                                                html.Div(id = 'content3_2')])

                       

                                                        ])

                                                       

                                        ]),

                                        dcc.Tab(label = 'Syslenia', value = 'tab4', style = styles['tab'],

                                                selected_style = styles['selected_tab'], children = [

                                                        dcc.Tabs(id = 'tabs_syslenie', value = 'tab1', children = [

                                                                dcc.Tab(label = 'Vseobecne metriky', value = 'tab1', style = styles['tab'],

                                                                        selected_style = styles['selected_tab'], children = [

                                                                                html.Div(id = 'content4_1')]),

                                                                dcc.Tab(label = 'Specificke metriky', value = 'tab2', style = styles['tab'],

                                                                        selected_style = styles['selected_tab'], children = [

                                                                                html.Div(id = 'content4_2')])

                                                        ])

                                        ]),

                                        dcc.Tab(label = 'Aktivita', value = 'tab5', style = styles['tab'],

                                                selected_style = styles['selected_tab'], children = [

                                                        html.Div(id = 'content5')]),

                                        dcc.Tab(label = 'Produktovy mix', value = 'tab6', style = styles['tab'],

                                                selected_style = styles['selected_tab'], children = [

                                                        html.Div(id = 'content6')]),

                                        dcc.Tab(label = 'Transakcie', value = 'tab7', style = styles['tab'],

                                                selected_style = styles['selected_tab'], children = [

                                                        html.Div(id = 'content7')]),

                                        dcc.Tab(label = 'Jira', value = 'tab8', style = styles['tab'],

                                                selected_style = styles['selected_tab'], children = [

                                                        dcc.Tabs(id = 'tabs_jira', value = 'tab1', children = [

                                                                dcc.Tab(label = 'Prijate vs. uzavrete ziadosti', value = 'tab1', style = styles['tab'],

                                                                        selected_style = styles['selected_tab'], children = [

                                                                                html.Div(id = 'content8_1')]),

                                                                dcc.Tab(label = 'Projekty a ich DIGI process', value = 'tab2', style = styles['tab'],

                                                                        selected_style = styles['selected_tab'], children = [

                                                                                html.Div(id = 'content8_2')])

                                                        ])

                                        ]),

                                        dcc.Tab(label = 'Info', value = 'tab9', style = styles['tab'],

                                                selected_style = styles['selected_tab'], children = [

                                                        html.Div(id = 'content9')

                                        ])

 

                                       

                                ])

                        ])                       

                        

                ], className = 'ten columns')

           

        ])

 

app.layout = lay()

 

########################################################################### DOWNLOAD LINK CALLBACKS #####################################

@app.callback(Output('download_link', 'href'),

             [Input('tabs', 'value'),

              Input('dropdown_period', 'value'),

               Input('datepicker_range', 'start_date'),

               Input('datepicker_range', 'end_date'),

               Input('slider_logins', 'value'),

               Input('slider_trans', 'value'),

               Input('radio_pmix', 'value'),

               Input('checklist_pmix', 'values'),

               Input('dropdown_trans_ucet', 'value'),

               Input('radio_trans_vklad', 'value'),

               Input('checklist_trans', 'values')])

def download_link_href(tab, period, start, end, logins, trans, operator, product, ucet, typ_trans, kat_trans):

   

    if tab == 'tab1':

        df = tab1_data(period, start, end)\

            .rename(columns = {'existing_accounts_nr_70':'Pocet existujucich beznych uctov',

                               'existing_accounts_nr_72':'Pocet existujucich sporiacich uctov',

                               'existing_accounts_nr_71':'Pocet existujucich sysliacich uctov',

                               'new_accounts_nr_70':'Pocet novych beznych uctov',

                              'new_accounts_nr_71':'Pocet novych sysliacich uctov',

                               'new_accounts_nr_72':'Pocet novych sporiacich uctov',

                               'zostatok_70':'Zostatok na beznych uctoch',

                               'zostatok_72':'Zostatok na sporiacich uctoch',

                               'zostatok_71':'Zostatok na sysliacich uctoch',

                               'plan_zostatky_accounts':'Planovane zostatky na beznych uctoch',

                               'plan_zostatky_all':'Planovane celkove zostatky',

                               'plan_existing_accounts_nr':'Planovany pocet existujucich beznych uctov',

                               '70pocet_txn_avg_client_0':'Priemerny pocet prichadzajucich transakcii na klienta',

                               '70pocet_txn_avg_client_1':'Priemerny pocet odchadzajucich transakcii na klienta',

                               '70suma_txn_avg_client_0':'Priemerna suma prichadzajucich transakcii na klienta',

                               '70suma_txn_avg_client_1':'Priemerna suma odchadzaujich transakcii na klienta',

                               'plan_zostatky_71_72':'Plan zostatkov na sporiacich + sysliacich uctoch',

                               '72_clientsnr_with_atleast_1spu':'Pocet klientov s aspon 1 sporiacim uctom',

                               '72_new_clientsnr':'Pocet klientov, ktory si prvy krat zalozili sporiaci ucet',

                               'approved':'Pocet schvalenych onboardingovych ziadosti',

                               'rejected':'Pocet zamietnutych onboardingovych ziadosti',

                               'onb_compl_rate': 'Onboarding completion rate',

                               'zostatok_all':'Celkovy zostatok',

                               'zostatok_71_72':'Zostatok na sporiacich a sysliacich uctoch',

                               'perc_zostatok_all':'Percento plnenia planu celkovych zostatkov',

                               'perc_zostatok_70':'Percento plnenia planu zostatkov na beznych uctoch',

                               'perc_zostatok_71_72':'Percento plnenia planu zostatkov na sporiacich a sysliacich uctoch',

                               'avg_zostatok_all':'Celkovy priemerny zostatok',

                               'avg_zostatok_70':'Priemerny zostatok na beznych uctoch',

                               'avg_zostatok_71_72':'Priemerny zostatok na sporiacich a sysliacich uctoch',

                               'avg_plan_zostatok_all':'Celkovy planovany priemerny zostatok',

                               'avg_plan_zostatok_70':'Planovany priemerny zostatok na beznych uctoch',

                               'avg_plan_zostatok_71_72':'Planovany priemerny zostatok na sporiacich a sysliacich uctoch',

                               'perc_avg_zostatok_all':'Percento plnenia planu celkoveho priemerneho zostatku',

                               'perc_avg_zostatok_70':'Percento plnenia planu priemerneho zostatku na beznych uctoch',

                               'perc_avg_zostatok_71_72':'Percento plnenia planu priemerneho zostatku na sporiacich a sysliacich uctoch',

                               'perc_71_existing_accounts_nr':'Percento existujucich sysliacich uctov',

                               'perc_72_existing_accounts_nr':'Percento existujucich sporiacich uctov',

                               'perc_72_clients_nr':'Percento klientov so sporiacim uctom',

                               'perc_71_new_accounts_nr':'Percento novych sysliacich uctov z existujucich klientov',

                               'perc_72_new_accounts_nr':'Percento novych sporiacich uctov z existujucich klientov',

                               'perc_72_new_clients_nr':'Percentov novych sporiacich klientov z existujucich klientov'})

    elif tab == 'tab2':

        df = tab2_data(period, start, end)\

                .rename(columns = {'existing_accounts_nr':'Pocet existujucich beznych uctov',

                                   'plan_existing_accounts_nr':'Planovany pocet existujucich beznych uctov',

                                   'new_accounts_nr':'Pocet novych beznych uctov',

                                   'plan_new_accounts_nr':'Planovany pocet novych uctov',

                                   'zostatok':'Zostatok na beznych uctoch',

                                   'plan_zostatky_accounts':'Planovane zostatky na beznych uctoch',

                                   'activated_accounts_nr':'Pocet zaktivovanych beznych uctov',

                                   'activated_and_new_accounts_nr':'Pocet zaktivovanych a zaroven novych beznych uctov',

                                   'terminated_accounts_nr':'Pocet zrusenych beznych uctov',

                                   'activated_and_terminated_accounts_nr':'Pocet zrusenych beznych uctov, ktore uz boli zaktivovane',

                                   'existing_and_activated_accounts_nr':'Pocet existujucich zaktivovanych beznych uctov',

                                   'perc_plan_existing_accounts_nr':'Percento plnenia planu existujucich beznych uctov',

                                   'perc_plan_zostatky_accounts':'Percento plnenia planu zostatkov na beznych uctoch',

                                   'perc_plan_new_accounts_nr':'Percento plnenia planu novych beznych uctov',

                                   'avg_zostatok':'Priemerny zostatok na beznych uctoch',

                                   'plan_avg_zostatok':'Planovany priemerny zostatok na beznych uctoch',

                                   'avg_zostatok_only_activated':'Priemerny zostatok len na zaktivnenych beznych uctoch',

                                   'perc_avg_zostatok':'Percento plnenia planovaneho priemerneho zostatku na beznych uctoch',

                                   'perc_avg_zostatok_only_activated':'Percento plnenia planovaneho priemerneho zostatku na zaktivnenych beznych uctoch',

                                   'perc_terminated_accounts_nr':'Percento zrusenych beznych uctov',

                                   'perc_activated_from_existing':'Percento zaktivnenych beznych uctov z existujucich beznych uctov',

                                   'perc_activated_and_new_accounts_nr_n':'Percento zaktivovanych a zaroven novych uctov, zo zaktivovanych uctov',

                                   'perc_existing_and_activated_accounts_nr':'Percento existujucich a zaktivovanych beznych uctov z existujucich uctov',

                                   'assumption_existing_accounts_nr':'Predpoklad existujucich beznych uctov',

                                   'assumption_new_accounts_nr':'Predpoklad novych beznych uctov',

                                   'assumption_zostatok':'Predpokad zostatkov na beznych uctoch'})

    elif tab == 'tab3':

        df1 = tab3_1_data(period, start, end)

        df1 = df1.reset_index().drop(columns = ['id_typuct'])

       

        df2, df3 = tab3_2_data(period, start, end)

        df2 = df2.reset_index().drop(columns = ['id_typuct'])

       

        df3.reset_index(inplace = True)

        

        df = df1.merge(df2, on = 'date')\

            .merge(df3, on = 'date')\

            .rename(columns = {'existing_accounts_nr_x':'Pocet existujucich sporiacich uctov',

                               'new_accounts_nr':'Pocet novych sporiacich uctov',

                               'zostatok':'Zostatkok na sporiacich uctoch',

                               'activated_accounts_nr':'Pocet zaktivovanych sporiacich uctov',

                               'activated_and_new_accounts_nr':'Pocet zaktivovanych a zaroven novych sporiacich uctov',

                               'terminated_accounts_nr':'Pocet zrusenych sporiacich uctov',

                               'activated_and_terminated_accounts_nr':'Pocet zrusenych sporiacich uctov, ktore uz boli zaktivovane',

                               'existing_and_activated_accounts_nr':'Pocet existujucich a zaroven zaktivovanych sporiacich uctov',

                               '72_new_clientsnr':'Pocet novych sporiacich klientov',

                               '72_clientsnr_activ_atleast1spu':'Pocet klientov, ktori si zaktivnili aspon 1 sporiaci ucet',

                               '72_clientsnr_with_atleast_1termin_spu':'Pocet klientov, ktori zrusili aspon 1 sporiaci ucet',

                               'clients_with_1up_72active':'Pocet klientov s aspon 1 zaktivnenym sporenim',

                               '72_clientsnr_terminated_all':'Pocet klientov co zrusili vsetky svoje sporiace ucty',

                               'avg_zostatok':'Priemerny zostatok na sporiacich uctoch',

                               'avg_zostatok_only_activated':'Priemerny zostatok na zaktivnenych sporiacich uctoch',

                               'perc_72clients_atleast1':'Percento klientov s aspon 1 sporiacim uctom',

                               'perc_72_clientsnr_activ_atleast1spu':'Percento klientov s aspon 1 zaktivnenym sporiacim uctom',

                               'avg_72count_from_all_clients':'Priemerny pocet sporiacich uctov na klienta - vsetci klienti',

                               'avg_72count_from_1upclients':'Priemerny pocet sporiacich uctov na klienta - len sporiaci klienti',

                               'perc_72zostatky_fromall':'Percento zostatkov na sporiacich uctoch z celkovych zostatkov',

                               'avg_zostatok_all_clients':'Priemerny zostatok na sporiacich uctoch - vsetci klienti',

                               'avg_zostatok_1up_clients':'Priemerny zostatok na sporiacich uctoch - len sporiaci klienti',

                               'perc_72_term_from_exist':'Percento zrusenych sporiacich uctov',

                               'perc_72_term_clientsnr':'Percento zrusenych sporiacich klientov',

                               'perc_72_clientsnr_terminated_all':'Percento klientov co zrusili vstky svoje sporiace ucty z klientov s aspon 1 sporiacim uctom',

                               'perc_existing_and_activated_accounts_nr':'Percento zaktivnenych existujucich sporiacich uctov zo existujucich sporiacich uctov',

                               'perc_activated_from_existing':'Percento zaktivovanych sporiacich uctov z existujucich zaktivovanych sporiacich uctov',

                               'perc_activated_and_new_accounts_nr':'Percento zaktivnenych uctov a zaroven novych uctov zo zaktivnenych uctov',

                               'perc_activated_clients_from_exisiting':'% zaktivnenych sporiacich klientov z existujucich zaktivnenych sporiacich klientov',

                               'assumption_existing_accounts_nr':'Predpokad existujucich sporiacich uctov',

                               'assumption_new_accounts_nr':'Predpoklad novych sporiacich uctov',

                               'assumption_zostatok':'Predpoklad zostatkov na sporiacich uctoch',

                               '70to72tp_count':'Pocet realizovanych trvalych prikazov so svojho bezneho uctu na sporiaci',

                               '70to72tp_sum':'Suma realizovanych trvalych prikazov so svojho bezneho uctu na sporiaci',

                               '70to72tp_sporeni_count':'Pocet sporiacich uctov, na ktore sa trvale prikazy realizovali',

                               '70to72tp_clients_count':'Pocet klientov, ktori trvale prikazy na svoj sporiaci ucet realizovali',

                               '70to72_trans_count':'Pocet transakcii realizovanych zo svojho bezneho uctu na svoj sporiaci ucet',

                               '70to72_trans_sum':'Suma transakcii realizovanych zo svojho bezneho uctu na svoj sporiaci ucet',

                               '70to72_spu_count':'Pocet sporiacih uctov, na ktore sa transakcie zo svojho bezneho na sporiaci realizovali',

                               '70to72_clients_count':'Pocet klientov, ktori transakcie zo svojho bezneho na sporiaci realizovali',

                               '72paid_interest_clients_count':'Pocet klientov, ktorym boli vyplatene uroky zo sporenia',

                               '72paid_interest_sporeni_count':'Pocet sporeni, z ktorych boli vyplatene uroky zo sporenia',

                               '72paid_interest_sum':'Suma vyplatenych urokov zo sporenia',

                               '72withdraw_clients_count':'Pocet klientov, ktori uskutocnilo vyber zo sporenia',

                               '72withdraw_sporeni_count':'Pocet sporeni, z ktorych bol uskutocneny vyber',

                               '72withdraw_sum':'Suma vyberov zo sporenia',

                               'otherto72_trans_count':'Pocet transakcii z inych uctov na sporiaci ucet',

                               'otherto72_trans_sum':'Suma transakcii z inych uctov na sporiaci ucet',

                               'otherto72_spu_count':'Pocet sporiacich uctov na ktore sa transakcie z inych uctov realizovali',

                               'otherto72_clients_count':'Pocet klientov, ktorym sa transakcie z inych uctov na ich sporiaci realizovali',

                               'perc_70to72tp_sporeni_count':'% sporiacich uctov, na ktore boli realizovane trvale prikazy zo vsetkych sporiacich uctov',

                               'perc_70to72tp_clients_count':'% klientov, na ktorych sporiace ucty boli realizovane trvale prikazy zo vsetkych sporiacich klientov',

                               'avg_70to72_trans_count_spu':'Priemerny pocet transakcii z bezneho uctu na sporiaci ucet',

                               'avg_70to72_trans_sum_spu':'Priemerna suma transakcii z bezneho uctu na sporiaci ucet',

                               'avg_70to72_trans_count_client':'Priemerny pocet transakcii z bezneho uctu na sporiaci ucet, na klienta',

                               'avg_70to72_trans_sum_client':'Priemerna suma transakcii z bezneho uctu na sporiaci ucet, na klienta',

                               'avg_otherto72_trans_count_spu':'Priemerny pocet transakcii z ineho ako  BU na SPu, na sporiaci ucet',

                               'avg_otherto72_trans_sum_spu':'Priemerna suma transakcii z ineho ako  BU na SPu, na sporiaci ucet',

                               'avg_otherto72_trans_count_client':'Priemerny pocet transakcii z ineho ako  BU na SPu, na klienta',

                               'avg_otherto72_trans_sum_client':'Priemerna suma transakcii z ineho ako  BU na SPu, na klienta',

                               'perc_72paid_interest_spu':'Vyplatene uroky z SpU - % z celkoveho poctu SpU',

                               'perc_72paid_interest_clients':'Vyplatene uroky z SpU - % z celkoveho sporiacich klientov',

                               'avg_72paid_interest_spu':'Vyplatene uroky z SpU - priemer na SpU kde boli uroky vyplatene',

                               'avg_72paid_interest_client':'Vyplatene uroky z SpU - klienta, ktorym boli uroky vyplatene',

                               'perc_72withdraw_spu':'Vybery z SpU - % z celkoveho poctu SpU',

                               'perc_72withdraw_clients':'Vybery z SpU - %  sporiacich klientov',

                               'avg_72withdraw_spu':'Vybery s SpU - priemer na SpU, kde sa vybery vykonali',

                               'avg_72withdraw_client':'Vybery s SpU - priemer na klientov, ktori vybery vykonali'

                              

                               

                               })\

            .drop(columns = ['72_clientsnr_with_atleast_1spu_x', '70_existing_accounts_nr', 'zostatok_all',

                             'existing_accounts_nr_y', '72_clientsnr_with_atleast_1spu_y'])\

            .sort_values(by = ['date'], ascending = False)

    elif tab == 'tab4':

        df1 = tab4_1_data(period, start, end)

        df2 = tab4_2_data(period, start, end)

        df = df1.join(df2, lsuffix = '_l', rsuffix = '_r')\

            .rename(columns = {'existing_accounts_nr_l':'Pocet existujucich sysliacich uctov',

                               'new_accounts_nr':'Pocet novych sysliacich uctov',

                               'zostatok':'Zostatok na sysliacich uctoch',

                               'activated_accounts_nr_l':'Pocet zaktivovanych sysliacich uctov',

                               'activated_and_new_accounts_nr':'Pocet zaktivovanych a zarovenych novych sysliacich uctov',

                               'terminated_accounts_nr':'Pocet zrusenych sysliacich uctov',

                               'activated_and_terminated_accounts_nr':'Pocet zrusenych sysliacich uctov, ktore boli uz zaktivovane',

                               'existing_and_activated_accounts_nr':'Pocet existujucich zaktivovanych sysliacich uctov',

                               'clients_with_1up_71active_l':'Pocet klientov so zaktivnenym sysliacim uctom',

                               'avg_zostatok':'Priemerny zostatok na sysliacich uctoch',

                               'avg_zostatok_only_activated':'Priemerny zostatok na zaktivnenych sysliacich uctoch',

                               'perc_existing_accounts_nr':'Percento klientov so sysliacimi uctami',

                               'perc_zostatok':'Percento zostatkov na sysliacich uctoch z celkovych zostatkov',

                               'perc_terminated_accounts_nr':'Percento zrusenych sysliacich uctov',

                               'perc_activated_from_existing':'Percento zaktivovanych sysliacich uctov',

                               'perc_activated_and_new_accounts_nr':'% zaktivnenych sysliacich uctov a zaroven novych uctov zo zaktivnenych sysliacich uctov',

                               'perc_existing_and_activated_accounts_nr':'% zaktivnenych uctov zo vsetkych uctov',

                               'assumption_existing_accounts_nr':'Predpoklad existujucich sysliacich uctov',

                               'assumption_new_accounts_nr':'Predpoklad novych sysliacich uctov',

                               'assumption_zostatok':'Predpoklad zostatkov na sysliacich uctoch',

                               '71paid_interest_sysleni_count':'Pocet sysleni, z ktorych boli vyplatene uroky zo syslenia',

                               '71paid_interest_sum':'Suma vyplatenych urokov zo syslenia',

                               '71_1eur_accounts_count':'Pocet existujucich sysliacich uctov s pravidlom 1 EUR',

                               '71_5eur_accounts_count':'Pocet existujucich sysliacich uctov s pravidlom 5 EUR',

                               '71_10eur_accounts_count':'Pocet existujucich sysliacich uctov s pravidlom 01 EUR',

                               '71_bezcentovy_accounts_count':'pocet existujucich sysliacich uctov s pravidlom bezcentovy ucet',

                               '71_10eur_zaktiv_accounts_count':'Pocet zaktivovanych sysliacich uctov s pravidlom 10 EUR',

                               '71_1eur_zaktiv_accounts_count':'Pocet zaktivovanych sysliacich uctov s pravidlom 1 EUR',

                               '71_5eur_zaktiv_accounts_count':'Pocet zaktivovanych sysliacich uctov s pravidlom 5 EUR',

                               '71_bezcentovy_zaktiv_accounts_count':'Pocet zaktivovanych sysliacich uctov s pravidlom bezcentovy ucet',

                               '70to71_trans_count':'Pocet prichadzajucich transakcii na sysliaci ucet',

                               '70to71_trans_sum':'Suma prichadzajucich transakcii na sysliaci ucet',

                               '70to71_spu_count':'Pocet sysliacich uctov na ktore sa prichadzajue transakcie realizovali',

                               '71_without_rule_accounts_count':'Pocet existujucich sysliacich uctov bez pravidla',

                               'perc_1eur_accounts_count':'Percento sysliacich uctov s pravidlom 1 EUR',

                               'perc_5eur_accounts_count':'Percento sysliacich uctov s pravidlom 5 EUR',

                               'perc_10eur_accounts_count':'Percento sysliacich uctov s pravidlom 10 EUR',

                               'perc_bezcentovy_accounts_count':'Percento sysliacich uctov s pravidlom bezcentovy ucet',

                               'perc_without_rule_accounts_count':'Percento sysliacich uctov bez pravidla',

                               'perc_71paid_interest_sysleni_count':'Percento sysliacich uctov, ktorym boli vyplatene uroky',

                               'avg_71paid_interest_sum':'Priemerna vyplatena suma na urokoch na sysliacich uctoch',

                               'avg_71paid_interest_sum_allspu':'Priemerna vyplatena suma na urokoch, na vsetkych klientov',

                               '71_without_rule_zaktiv_accounts_count':'Pocet zaktivnenych sysliacich uctov bez pravidla',

                               'perc_1eur_zaktiv_accounts_count':'Percento zaktivnenych sysliacich uctov s pravidlom 1 EUR zo vsetkych sysliacich uctov',

                               'perc_5eur_zaktiv_accounts_count':'Percento zaktivnenych sysliacich uctov s pravidlom 5 EUR zo vsetkych sysliacich uctov',

                               'perc_10eur_zaktiv_accounts_count':'Percento zaktivnenych sysliacich uctov s pravidlom 10 EUR zo vsetkych sysliacich uctov',

                               'perc_bezcentovy_zaktiv_accounts_count':'Percento zaktivnenych sysliacich uctov s pravidlom bezcentovy ucet zo vsetkych sysliacich uctov',

                               'perc_without_rule_zaktiv_accounts_count':'Percento zaktivnenych sysliacich uctov bez pravidla zo vsetkych sysliacich uctov',

                               'avg_70to71_trans_count':'Priemerny pocet transakcii na sysliaci ucet',

                               'avg_70to71_trans_sum':'Priemerna suma transakcii na sysliaci ucet',

                               '71_withdraw_trans_count':'Pocet vyberov zo sysleni',

                               '71_withdraw_trans_sum':'Suma vyberov zo sysleni',

                               '71_withdraw_ucet_count':'Pocet sysliacich uctov, z ktorych boli uskutocnene vybery',

                               'avg_71_withdraw_trans_count':'Priemerny pocet vyberov zo syslenia',

                               'avg_71_withdraw_trans_sum':'Priemerna suma vyberov zo syslenia',

                               'perc_71_withdraw_ucet_count':'Percento sysliacich uctov, z ktorych boli urobene vybery'

                              

                               

                               })\

            .drop(columns = ['70_existing_accounts_nr', 'zostatok_all','clients_with_1up_71active_r',

                             'existing_accounts_nr_r', 'activated_accounts_nr_r', '1500more_all_syu_count',

                             '1500more_trans_count', '1500more_trans_sum', '1500more_ucet_count',

                             'less1500_all_syu_count', 'less1500_trans_count', 'less1500_trans_sum',

                             'less1500_ucet_count', 'avg_1500more_trans_count', 'avg_1500more_trans_sum',

                             'avg_less1500_trans_count', 'avg_less1500_trans_sum', 'perc_1500more_ucet_count',

                             'perc_less1500_ucet_count'])

    elif tab == 'tab5':

        df = tab5_data(period, start, end, logins, trans)\

                .rename(columns = {'active_clients_count':'Pocet aktivnych klientov',

                                   'existing_accounts_nr_without_zal':'Pocet existujucich klientov bez novych',

                                   'perc_active_clients_count':'Percento aktivnych klientov ' +

                                   str(logins) + ' a viac loginov a ' + str(trans) + ' a viac odchadzajucich transakcii'})\

                .drop(columns = ['existing_accounts_nr', 'new_accounts_nr'])

    elif tab == 'tab6':

        # produktovy mix

        df = tab6_data(period, start, end, operator, product)\

                .rename(columns = {'pmix_clients_count':'Pocet klientov so zvolenymi produktmi',

                                   'existing_accounts_nr':'Pocet existujucich klientov',

                                   'perc_pmix_clients_count':'Percento klientov so zvolenymi produktmi'})

    elif tab == 'tab7':

        df1, df2 = tab7_data(period, start, end, ucet, typ_trans, kat_trans)

        df = df1.join(df2)\

                .rename(columns = {'trans_count':'Pocet transakcii vo zvolenych kategoriach',

                                   'trans_sum':'Suma transakcii vo zvolenych kategoriach',

                                   'all_trans_count':'Pocet transakcii vo vsetkych kategoriach v ramci typu uctu a typu transakcie',

                                   'all_trans_sum':'Suma transakcii vo vsetkych kategoriach v ramci typu uctu a typu transakcie',

                                   'perc_trans_sum':'Percento sumy transakcii vo zvolenych kategoriach v ramci typu uctu a typu transakcie',

                                   'perc_trans_count':'Percento poctu transakcii vo zvolenych kategoriach v ramci typu uctu a typu transakcie'})

    elif tab == 'tab8':

        df1 = tab8_1_data(period, start, end)

        df2, df3 = tab8_2_data(period, start, end)

        df = df1.join(df2).join(df3)

    else:

        df = pd.DataFrame({})

   

    xlsx_io = io.BytesIO()

    writer = pd.ExcelWriter(xlsx_io, engine='xlsxwriter')

    df.to_excel(writer, sheet_name='one')

    writer.save()

    xlsx_io.seek(0)

    media_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    data = base64.b64encode(xlsx_io.read()).decode("utf-8")

    href_data_downloadable = f'data:{media_type};base64,{data}'

    return href_data_downloadable 

 

################################################################ PROMPTS CALLBACKS ################################

 

@app.callback(

    Output('slider_logins_output', 'children'),

    [Input('slider_logins', 'value')])

def slider_logins_output_children(value):

    return 'Zvolene {} a viac'.format(value)

 

@app.callback(

    Output('slider_trans_output', 'children'),

    [Input('slider_trans', 'value')])

def slider_trans_output_children(value):

    return 'Zvolene {} a viac'.format(value)

 

@app.callback(

    Output('login_prompts', 'style'),

    [Input('tabs', 'value')])

def login_prompts_style(tab):

    if tab == 'tab5':

        to_return = {'display':'inline'}

    else:

        to_return = {'display':'none'}

           

    return to_return

 

@app.callback(

    Output('pmix_prompts', 'style'),

    [Input('tabs', 'value')])

def pmix_prompts_style(tab):

    if tab == 'tab6':

        to_return = {'display':'inline'}

    else:

        to_return = {'display':'none'}

           

    return to_return

 

@app.callback(

    Output('trans_prompts', 'style'),

    [Input('tabs', 'value')])

def trans_prompts_style(tab):

    if tab == 'tab7':

        to_return = {'display':'inline'}

    else:

        to_return = {'display':'none'}

           

    return to_return

 

@app.callback(

    Output('checklist_trans', 'options'),

    [Input('dropdown_trans_ucet', 'value'),

     Input('radio_trans_vklad', 'value')])

def checklist_trans_options(ucet, vklad):

    df = read_trans('Y')

    options = df.loc[(df['id_typuct'] == ucet) & (df['pri_vklad'] == vklad), 'kat_txn'].unique()

 

    to_return = [{'label': option, 'value': option} for option in options]

           

    return to_return

 

@app.callback(

    Output('checklist_trans', 'values'),

    [Input('dropdown_trans_ucet', 'value'),

     Input('radio_trans_vklad', 'value')])

def checklist_trans_values(ucet, vklad):

    df = read_trans('Y')

    options = df.loc[(df['id_typuct'] == ucet) & (df['pri_vklad'] == vklad), 'kat_txn'].unique()

 

    to_return = [options[0]]

           

    return to_return

 

################################################################ tab1 - VYBRANE METRIKY ###########################

 

@app.callback(Output('content1', 'children'),

              [Input('tabs', 'value'),

               Input('dropdown_period', 'value'),

               Input('datepicker_range', 'start_date'),

               Input('datepicker_range', 'end_date')])

def content1_children(tab_level1, period, start, end):

    if tab_level1 == 'tab1':

        df = tab1_data(period, start, end)

  

        

        return html.Div([

                    html.Div([

                        html.Div(id = 'tab1_chart1_div', children = [dcc.Graph(id = 'tab1_chart1', figure = tab1_chart1(df))], className = 'six columns'),

                        html.Div(id = 'tab1_chart2_div', children = [dcc.Graph(id = 'tab1_chart2', figure = tab1_chart2(df))], className = 'six columns')

                           

                    ], className = 'row'),

                    html.Div([

                        html.Div(id = 'tab1_chart3_div', children = [dcc.Graph(id = 'tab1_chart3', figure = tab1_chart3(df))], className = 'six columns'),

                        html.Div(id = 'tab1_chart4_div', children = [dcc.Graph(id = 'tab1_chart4', figure = tab1_chart4(df))], className = 'six columns')

                           

                    ], className = 'row'),

   

                    html.Div([

                        html.Div(id = 'tab1_chart5_div', children = [dcc.Graph(id = 'tab1_chart5', figure = tab1_chart5(df))], className = 'six columns'),

                        html.Div(id = 'tab1_chart6_div', children = [dcc.Graph(id = 'tab1_chart6', figure = tab1_chart6(df))], className = 'six columns')

                           

                    ], className = 'row')

                   

                

        ])

 

def tab1_data(period, start, end):

    metrics = ['existing_accounts_nr',

              'new_accounts_nr', 'zostatok',

              'plan_zostatky_accounts', 'plan_zostatky_all', 'plan_zostatky_71_72',

              '72_clientsnr_with_atleast_1spu', '72_new_clientsnr', 'plan_existing_accounts_nr',

              '70_trans_count_mean_0', '70_trans_count_mean_1', '70_trans_count_median_0',

              '70_trans_count_median_1', '70_trans_count_q25_0','70_trans_count_q25_1',

              '70_trans_count_q75_0', '70_trans_count_q75_1',

              '70_trans_sum_mean_0', '70_trans_sum_mean_1', '70_trans_sum_median_0',

              '70_trans_sum_median_1', '70_trans_sum_q25_0','70_trans_sum_q25_1',

              '70_trans_sum_q75_0', '70_trans_sum_q75_1']

   

    start = pd.to_datetime(start).normalize()

    end = pd.to_datetime(end).to_period(period).end_time.normalize()

   

    df = read_df(period)

    df = df.loc[:,metrics]

   

    df = df.loc[df.index.get_level_values('id_typuct') != 75,:]

   

    # existujuce ucty, nove ucty, zostatky, plany - 70, plany - 71 a 72, plany all, existujuci sporiaci klienti, novi sporiaci klienti

    df1 = df.loc[:, ['existing_accounts_nr', 'new_accounts_nr', 'zostatok']].unstack()

    df1.columns = ['_'.join((col[0], str(col[1]))).strip() for col in df1.columns.values] # flattening multiindex

    df2 = df.loc[df.index.get_level_values('id_typuct') == 70,

                 ['plan_zostatky_accounts', 'plan_zostatky_all', 'plan_existing_accounts_nr',

              '70_trans_count_mean_0', '70_trans_count_mean_1', '70_trans_count_median_0',

              '70_trans_count_median_1', '70_trans_count_q25_0','70_trans_count_q25_1',

              '70_trans_count_q75_0', '70_trans_count_q75_1',

              '70_trans_sum_mean_0', '70_trans_sum_mean_1', '70_trans_sum_median_0',

              '70_trans_sum_median_1', '70_trans_sum_q25_0','70_trans_sum_q25_1',

              '70_trans_sum_q75_0', '70_trans_sum_q75_1']].unstack().droplevel(1, axis = 1)

    df3 = df.loc[df.index.get_level_values('id_typuct') == 71, 'plan_zostatky_71_72']

    df3.index = [i[0] for i in df3.index]

    df3_1 = df.loc[df.index.get_level_values('id_typuct') == 72, ['72_clientsnr_with_atleast_1spu', '72_new_clientsnr']].unstack().droplevel(1, axis = 1)

   

    # onboarding completion rate (approved, rejected, ocr)

    df4 = read_ocr(period)

       

    df = df1.join(df2, how = 'outer')\

            .join(df3, how = 'outer')\

            .join(df3_1, how = 'outer')\

            .join(df4, how = 'outer')

   

    df = df.loc[(df.index >= start) &

                (df.index <= end), :]

                           

    # calculate new metrics

   

    # celkovy zostatok a zostatok pre 71 + 72 ucty

   

    df['zostatok_all'] = df['zostatok_70'] + df['zostatok_71'] + df['zostatok_72']

    df['zostatok_71_72'] = df['zostatok_71'] + df['zostatok_72']

   

    # % plnenia planu zostatokov - celkove, BU, 71 + 72

   

    df['perc_zostatok_all'] = df['zostatok_all']/df['plan_zostatky_all']

    df['perc_zostatok_70'] = df['zostatok_70']/df['plan_zostatky_accounts']

    df['perc_zostatok_71_72'] = df['zostatok_71_72']/df['plan_zostatky_71_72']

   

    # priemerne zostatky - celkove, BU, 71 + 72

   

    df['avg_zostatok_all'] = df['zostatok_all'] / df['existing_accounts_nr_70']

    df['avg_zostatok_70'] = df['zostatok_70'] / df['existing_accounts_nr_70']

    df['avg_zostatok_71_72'] = df['zostatok_71_72'] / df['existing_accounts_nr_70']

   

    # planovane priemerne zostatky - celkove, BU, 71 +72

   

    df['avg_plan_zostatok_all'] = df['plan_zostatky_all'] / df['plan_existing_accounts_nr']

    df['avg_plan_zostatok_70'] = df['plan_zostatky_accounts'] / df['plan_existing_accounts_nr']

    df['avg_plan_zostatok_71_72'] = df['plan_zostatky_71_72'] / df['plan_existing_accounts_nr']

   

    # % plnenia priemernych zostatkov

   

    df['perc_avg_zostatok_all'] = df['avg_zostatok_all'] / df['avg_plan_zostatok_all']

    df['perc_avg_zostatok_70'] = df['avg_zostatok_70'] / df['avg_plan_zostatok_70']

    df['perc_avg_zostatok_71_72'] = df['avg_zostatok_71_72'] / df['avg_plan_zostatok_71_72']

   

    # % existujucich sysliacich uctov, sporiacich uctov a sporiacich klientov

   

    df['perc_71_existing_accounts_nr'] = df['existing_accounts_nr_71']/df['existing_accounts_nr_70']

    df['perc_72_existing_accounts_nr'] = df['existing_accounts_nr_72']/df['existing_accounts_nr_70']

    df['perc_72_clients_nr'] = df['72_clientsnr_with_atleast_1spu']/df['existing_accounts_nr_70']

   

    # % novych sysliacich uctov, sporiacich uctov a sporiacich klientov

   

    df['perc_71_new_accounts_nr'] = df['new_accounts_nr_71']/df['existing_accounts_nr_70']

    df['perc_72_new_accounts_nr'] = df['new_accounts_nr_72']/df['existing_accounts_nr_70']

    df['perc_72_new_clients_nr'] = df['72_new_clientsnr']/df['existing_accounts_nr_70']  

    

    return df

 

def tab1_chart1(df):

    x = df.index

   

    trace0 = Scatter(x = x, y = df['existing_accounts_nr_70'],name = 'Bezne ucty')

    trace1 = Scatter(x = x, y = df['existing_accounts_nr_72'], name = 'Sporiace ucty', visible = 'legendonly')

    trace1_1 = Scatter(x = x, y = df['72_clientsnr_with_atleast_1spu'] , name = 'Sporiaci klienti')

    trace2 = Scatter(x = x, y = df['existing_accounts_nr_71'], name = 'Sysliace ucty')

   

    trace3 = Scatter(x = x, y = df['perc_71_existing_accounts_nr'], name = 'Sysliace ucty %', yaxis = 'y2', visible = False)

    trace4 = Scatter(x = x, y = df['perc_72_existing_accounts_nr'], name = 'Sporiace ucty %', yaxis = 'y2', visible = False)

    trace5 = Scatter(x = x, y = df['perc_72_clients_nr'], name = 'Sporiaci klienti %', yaxis = 'y2', visible = False)

   

    data = [trace0, trace1, trace1_1, trace2, trace3, trace4, trace5]

   

    updatemenus = list([

            dict(type = 'buttons',

                 active = -1,

                 direction="right",

                x=0.01, y = 1.23,

                xanchor="left",

                yanchor="top",

                 buttons = list([

                         dict(label = 'Ucty',

                              method = 'update',

                              args = [dict(visible = [True, 'legendonly', True, True, False, False, False])]),

                        dict(label = '%',

                             method = 'update',

                             args = [dict(visible = [False, False, False, False, True, True, True])])

                       

                    ]))])

   

    layout = dict(title = 'Existujuce ucty',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]', hoverformat = ',.0', rangemode = 'tozero'),

                       updatemenus = updatemenus,

                       yaxis2 = dict(title = '%', side = 'right', overlaying = 'y', rangemode = 'tozero',

                                     tickformat = ',.0%', hoverformat = ',.1%'),

                    legend = dict(x = 1.08))

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab1_chart2(df):

    x = df.index

   

    trace0 = Scatter(x = x, y = df['new_accounts_nr_70'],name = 'Bezne ucty')

    trace1 = Scatter(x = x, y = df['new_accounts_nr_72'], name = 'Sporiace ucty', visible = 'legendonly')

    trace1_1 = Scatter(x = x, y = df['72_new_clientsnr'], name = 'Sporiaci klienti')

    trace2 = Scatter(x = x, y = df['new_accounts_nr_71'], name = 'Sysliace ucty')

   

    trace3 = Scatter(x = x, y = df['perc_71_new_accounts_nr'], name = 'Sysliace ucty %', yaxis = 'y2', visible = False)

    trace4 = Scatter(x = x, y = df['perc_72_new_accounts_nr'], name = 'Sporiace ucty %', yaxis = 'y2', visible = False)

    trace5 = Scatter(x = x, y = df['perc_72_new_clients_nr'], name = 'Sporiaci klienti %', yaxis = 'y2', visible = False)

   

    data = [trace0, trace1, trace1_1, trace2, trace3, trace4, trace5]

   

    updatemenus = list([

            dict(type = 'buttons',

                 active = -1,

                 direction="right",

                x=0.01, y = 1.23,

                xanchor="left",

                yanchor="top",

                 buttons = list([

                         dict(label = 'Ucty',

                             method = 'update',

                              args = [dict(visible = [True, True, True, 'legendonly', False, False, False])]),

                        dict(label = '%',

                             method = 'update',

                             args = [dict(visible = [False, False, False, False, True, True, True])])

                       

                    ]))])

   

    layout = dict(title = 'Nove ucty',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]', hoverformat = ',.0', rangemode = 'tozero'),

                       updatemenus = updatemenus,

                       yaxis2 = dict(title = '%', side = 'right', overlaying = 'y', rangemode = 'tozero',

                                     tickformat = ',.0%', hoverformat = ',.1%'),

                    legend = dict(x = 1.08))

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab1_chart3(df):

    x = df.index

   

    trace0 = Scatter(x = x, y = df['zostatok_all'],name = 'Celkove')

    trace1 = Scatter(x = x, y = df['plan_zostatky_all'], name = 'Celkove - plan', visible = 'legendonly')

    trace1_1 = Scatter(x = x ,y = df['perc_zostatok_all'], name = 'Celkove - % plnenia', yaxis = 'y2')

    trace2 = Scatter(x = x, y = df['zostatok_70'], name = 'BU', visible = False)

    trace3 = Scatter(x = x, y = df['plan_zostatky_accounts'], name = 'BU - plan', visible = False)

    trace3_1 = Scatter(x = x ,y = df['perc_zostatok_70'], name = 'BU - % plnenia', yaxis = 'y2', visible = False)

    trace4 = Scatter(x = x, y = df['zostatok_71_72'], name = 'SpU + SyU', visible = False)

    trace5 = Scatter(x = x, y = df['plan_zostatky_71_72'], name = 'SpU + SyU - plan', visible = False)

    trace5_1 = Scatter(x = x ,y = df['perc_zostatok_71_72'], name = 'SpU + SyU - % plnenia', yaxis = 'y2', visible = False)

   

    data = [trace0, trace1, trace1_1, trace2, trace3, trace3_1, trace4, trace5, trace5_1]

   

    updatemenus = list([

            dict(type = 'buttons',

                 active = -1,

                 direction="right",

                x=0.01, y = 1.23,

                xanchor="left",

                yanchor="top",

                 buttons = list([

                         dict(label = 'Celkovo',

                              method = 'update',

                              args = [dict(visible = [True, 'legendonly', True, False, False, False, False, False, False])]),

                        dict(label = 'BU',

                             method = 'update',

                             args = [dict(visible = [False, False, False, True, 'legendonly', True, False, False, False])]),

                        dict(label = 'SpU + SyU',

                             method = 'update',

                             args = [dict(visible = [False, False, False, False, False, False, True, 'legendonly', True])])

                       

                    ]))])   

    

    layout = dict(title = 'Zostatky',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Suma [EUR]', hoverformat = ',.2f'),

                       updatemenus = updatemenus,

                       yaxis2 = dict(title = '%', side = 'right', overlaying = 'y', rangemode = 'tozero',

                                     tickformat = ',.0%', hoverformat = ',.1%'),

                    legend = dict(x = 1.08)

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab1_chart4(df):

    x = df.index

   

    trace0 = Scatter(x = x, y = df['avg_zostatok_all'],name = 'Celkove')

    trace1 = Scatter(x = x, y = df['avg_plan_zostatok_all'], name = 'Celkove - plan', visible = 'legendonly')

    trace1_1 = Scatter(x = x ,y = df['perc_avg_zostatok_all'], name = 'Celkove - % plnenia', yaxis = 'y2')

    trace2 = Scatter(x = x, y = df['avg_zostatok_70'], name = 'BU', visible = False)

    trace3 = Scatter(x = x, y = df['avg_plan_zostatok_70'], name = 'BU - plan', visible = False)

    trace3_1 = Scatter(x = x ,y = df['perc_avg_zostatok_70'], name = 'BU - % plnenia', yaxis = 'y2', visible = False)

    trace4 = Scatter(x = x, y = df['avg_zostatok_71_72'], name = 'SpU + SyU', visible = False)

    trace5 = Scatter(x = x, y = df['avg_plan_zostatok_71_72'], name = 'SpU + SyU - plan', visible = False)

    trace5_1 = Scatter(x = x ,y = df['perc_avg_zostatok_71_72'], name = 'SpU + SyU - % plnenia', yaxis = 'y2', visible = False)

   

    data = [trace0, trace1, trace1_1, trace2, trace3, trace3_1, trace4, trace5, trace5_1]

   

    updatemenus = list([

            dict(type = 'buttons',

                 active = -1,

                 direction="right",

                x=0.01, y = 1.23,

                xanchor="left",

                yanchor="top",

                 buttons = list([

                         dict(label = 'Celkovo',

                              method = 'update',

                              args = [dict(visible = [True, 'legendonly', True, False, False, False, False, False, False])]),

                        dict(label = 'BU',

                             method = 'update',

                             args = [dict(visible = [False, False, False, True, 'legendonly', True, False, False, False])]),

                        dict(label = 'SpU + SyU',

                             method = 'update',

                             args = [dict(visible = [False, False, False, False, False, False, True, 'legendonly', True])])

                       

                    ]))])   

    

    layout = dict(title = 'Priemerne zostatky',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Suma [EUR]', hoverformat = ',.2f'),

                       updatemenus = updatemenus,

                       yaxis2 = dict(title = '%', side = 'right', overlaying = 'y', rangemode = 'tozero',

                                     tickformat = ',.0%', hoverformat = ',.1%'),

                    legend = dict(x = 1.08)

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab1_chart5(df):

    x = df.index

   

    trace0 = Scatter(x = x, y = df['approved'],name = 'Approved', visible = 'legendonly')

    trace1 = Scatter(x = x, y = df['rejected'], name = 'Rejected', visible = 'legendonly')

    trace2 = Scatter(x = x ,y = df['onb_compl_rate'], name = 'OCR', yaxis = 'y2')

 

   

    data = [trace0, trace1, trace2]

   

    layout = dict(title = 'Onboarding completion rate',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Suma [EUR]', hoverformat = ',.2f', rangemode = 'tozero'),

                       yaxis2 = dict(title = '%', side = 'right', overlaying = 'y', rangemode = 'tozero',

                                     tickformat = ',.0%', hoverformat = ',.1%'),

                    legend = dict(x = 1.08)

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab1_chart6(df):

    x = df.index

   

    trace0 = Scatter(x = x, y = df['70_trans_count_mean_0'],name = 'Priemerny pocet')

    trace1 = Scatter(x = x, y = df['70_trans_sum_mean_0'], name = 'Priemerna suma', yaxis = 'y2')

    trace2 = Scatter(x = x ,y = df['70_trans_count_mean_1'], name = 'Priemerny pocet', visible = False)

    trace3 = Scatter(x = x, y = df['70_trans_sum_mean_1'], name = 'Priemerna suma', visible = False, yaxis = 'y2')

   

    trace5 = Scatter(x = x, y = df['70_trans_count_median_0'],name = 'Median pocet', visible = 'legendonly')

    trace6 = Scatter(x = x, y = df['70_trans_sum_median_0'], name = 'Median suma', visible = 'legendonly', yaxis = 'y2')

    trace7 = Scatter(x = x ,y = df['70_trans_count_median_1'], name = 'Median pocet', visible = False)

    trace8 = Scatter(x = x, y = df['70_trans_sum_median_1'], name = 'Median suma', visible = False, yaxis = 'y2')

   

    trace9 = Scatter(x = x, y = df['70_trans_count_q25_0'],name = '25 kvanil pocet', visible = 'legendonly')

    trace10 = Scatter(x = x, y = df['70_trans_sum_q25_0'], name = '25 kvanil suma', yaxis = 'y2', visible = 'legendonly')

    trace11 = Scatter(x = x ,y = df['70_trans_count_q25_1'], name = '25 kvanil pocet', visible = False)

    trace12 = Scatter(x = x, y = df['70_trans_sum_q25_1'], name = '25 kvanil suma', visible = False, yaxis = 'y2')

   

    trace13 = Scatter(x = x, y = df['70_trans_count_q75_0'],name = '75 kvanil pocet', visible = 'legendonly')

    trace14 = Scatter(x = x, y = df['70_trans_sum_q75_0'], name = '75 kvanil suma', yaxis = 'y2', visible = 'legendonly')

    trace15 = Scatter(x = x ,y = df['70_trans_count_q75_1'], name = '75 kvanil pocet', visible = False)

    trace16 = Scatter(x = x, y = df['70_trans_sum_q75_1'], name = '75 kvanil suma', visible = False, yaxis = 'y2')

 

   

    data = [trace0, trace1, trace2, trace3, trace5, trace6, trace7, trace8, trace9,

            trace10, trace11, trace12, trace13, trace14, trace15, trace16]

   

    updatemenus = list([

            dict(type = 'buttons',

                 active = -1,

                 direction="right",

                x=0.01, y = 1.23,

                xanchor="left",

                yanchor="top",

                 buttons = list([

                         dict(label = 'Odchadzajuce',

                              method = 'update',

                              args = [dict(visible = [True, True, False, False, 'legendonly', 'legendonly', False, False, 'legendonly',

            'legendonly', False, False, 'legendonly', 'legendonly', False, False])]),

                        dict(label = 'Prichadzajuce',

                             method = 'update',

                             args = [dict(visible = [False, False, True, True, False, False, 'legendonly', 'legendonly', False,

            False, 'legendonly', 'legendonly', False, False, 'legendonly', 'legendonly'])])

                        

                    ]))])   

    

    layout = dict(title = 'Priemer a kvantily transakcii na BU',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet', hoverformat = ',.1f'),

                       updatemenus = updatemenus,

                       yaxis2 = dict(title = 'Suma [EUR]', side = 'right', overlaying = 'y', rangemode = 'tozero',

                                      hoverformat = ',.1f'),

                    legend = dict(x = 1.08)

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

################################################################ tab2 - UCTY ####################################

 

@app.callback(Output('content2', 'children'),

              [Input('tabs', 'value'),

               Input('dropdown_period', 'value'),

               Input('datepicker_range', 'start_date'),

               Input('datepicker_range', 'end_date')])

def content2_children(tab_level1, period, start, end):

    if tab_level1 == 'tab2':

        df = tab2_data(period, start, end)       

        

        return html.Div([

                    html.Div([

                        html.Div(id = 'tab2_chart1_div', children = [dcc.Graph(id = 'tab2_chart1', figure = tab2_chart1(df))], className = 'six columns'),

                        html.Div(id = 'tab2_chart2_div', children = [dcc.Graph(id = 'tab2_chart2', figure = tab2_chart2(df))], className = 'six columns')

                           

                    ], className = 'row'),

                    html.Div([

                        html.Div(id = 'tab2_chart3_div', children = [dcc.Graph(id = 'tab2_chart3', figure = tab2_chart3(df))], className = 'six columns'),

                        html.Div(id = 'tab2_chart4_div', children = [dcc.Graph(id = 'tab2_chart4', figure = tab2_chart4(df))], className = 'six columns')

                           

                    ], className = 'row'),

   

                    html.Div([

                        html.Div(id = 'tab2_chart5_div', children = [dcc.Graph(id = 'tab2_chart5', figure = tab2_chart5(df))], className = 'six columns'),

                        html.Div(id = 'tab2_chart6_div', children = [dcc.Graph(id = 'tab2_chart6', figure = tab2_chart6(df))], className = 'six columns')

                           

                    ], className = 'row')

                   

                

        ])

 

def tab2_data(period, start, end):

    metrics = ['existing_accounts_nr', 'plan_existing_accounts_nr',

              'new_accounts_nr', 'plan_new_accounts_nr', 'zostatok',

              'plan_zostatky_accounts', 'activated_accounts_nr', 'activated_and_new_accounts_nr',

              'terminated_accounts_nr',

              'activated_and_terminated_accounts_nr', 'existing_and_activated_accounts_nr']

   

    start = pd.to_datetime(start).normalize()

    end = pd.to_datetime(end).to_period(period).end_time.normalize()

   

    df = read_df(period)

    df = df.loc[(df.index.get_level_values('date') >= start) &

                (df.index.get_level_values('date') <= end),metrics]

    df = df.loc[df.index.get_level_values('id_typuct') == 70,:]

   

    last_date = pd.to_datetime(datetime.now())

           

    # calculate new metrics

   

    # % plnenia planu - existujucie ucty       

    df['perc_plan_existing_accounts_nr'] = df['existing_accounts_nr']/df['plan_existing_accounts_nr']

   

    # % plnenia planu - zostatky

    df['perc_plan_zostatky_accounts'] = df['zostatok']/df['plan_zostatky_accounts']

   

    # % plnenia planu - nove ucty

    df['perc_plan_new_accounts_nr'] = df['new_accounts_nr']/df['plan_new_accounts_nr']

   

    # priemerne zostatky na vsetkych existujucich beznych uctoch

    df['avg_zostatok'] = df['zostatok']/df['existing_accounts_nr']

   

    # planovane priemerne zostatky na vsetkych existujucich beznych uctoch

    df['plan_avg_zostatok'] = df['plan_zostatky_accounts']/df['plan_existing_accounts_nr']

   

    # priemerne zostatky na zaktivovanych uctoch

    df['avg_zostatok_only_activated'] = df['zostatok']/df['existing_and_activated_accounts_nr']

   

    # % plnenia planu - priemerne zostatky (vsetky BU a zaktivnene) (toto moc zmysel nema, ale jana to tak chcela)

    df['perc_avg_zostatok'] = df['avg_zostatok']/df['plan_avg_zostatok']

    df['perc_avg_zostatok_only_activated'] = df['avg_zostatok_only_activated']/df['plan_avg_zostatok']

   

    # % zrusenych uctov

    df['perc_terminated_accounts_nr'] = df['terminated_accounts_nr']/df['existing_accounts_nr']

   

    # % zaktivovanych uctov z existujucich zaktivovanych uctov

    df['perc_activated_from_existing'] = df['activated_accounts_nr']/df['existing_and_activated_accounts_nr']

   

    # % zaktivovanych a zaroven novych uctov - zo zaktivovanych uctov (tj tolkoto % uctov je novych zo vsetkych zaktivovanych)

    df['perc_activated_and_new_accounts_nr_n'] = df['activated_and_new_accounts_nr']/df['activated_accounts_nr']

   

    # % zaktivnenych uctov zo vsetkych uctov   

    df['perc_existing_and_activated_accounts_nr'] = df['existing_and_activated_accounts_nr']/df['existing_accounts_nr']

   

    # predpoklad v aktualnej periode (okrem dennej) - eistujuce ucty, nove ucty, zostatky

    df['assumption_existing_accounts_nr'] = np.nan

    df['assumption_new_accounts_nr'] = np.nan

    df['assumption_zostatok'] = np.nan

   

    if period != 'D':

        last_date_period_end = last_date.to_period(period).end_time.normalize()

 

        if period == 'W':

            last_date_period_end_1 = last_date_period_end - pd.DateOffset(weeks = 1)

        elif period == 'M':

            last_date_period_end_1 = (last_date_period_end - pd.DateOffset(months = 1)).to_period(period).end_time.normalize() # problem to robilo

            # iba pri mesiacoch, ked posledny den minuleho mesiac dalo na 30.8.2019 - namiesto 31.8.2019

        elif period == 'Q':

            last_date_period_end_1 = last_date_period_end - pd.DateOffset(months = 3)

        elif period == 'Y':

            last_date_period_end_1 = last_date_period_end - pd.DateOffset(years = 1)

       

        # predpoklad - nove ucty

        x1 = df.loc[df.index.get_level_values('date') == last_date_period_end,

               'new_accounts_nr'] # kolko novych uctov pribudlo tuto periodu

 

       

        try:

            df.loc[df.index.get_level_values('date') == last_date_period_end,

                   'assumption_new_accounts_nr'] = calculate_assumption(last_date, period, x1)

 

            # predpoklad - existujuce ucty

            df.loc[df.index.get_level_values('date') == last_date_period_end, 'assumption_existing_accounts_nr'] = df['existing_accounts_nr'] - df['new_accounts_nr'] + df['assumption_new_accounts_nr']

            # predpoklad - zostatky - ratane cez prirastok zostatkov

 

            x3_1 = df.loc[df.index.get_level_values('date') == last_date_period_end, 'zostatok'] # zostatok aktualnu periodu

                       

            x3_2 = df.loc[df.index.get_level_values('date') == last_date_period_end_1, 'zostatok'] # zostatok periodu pred

            

            x3_2.index = [(last_date_period_end, i[1]) for i in x3_2.index]

           

            x3 = x3_1 - x3_2

           

            df.loc[df.index.get_level_values('date') == last_date_period_end,

                   'assumption_zostatok'] = df['zostatok'] - x3 + calculate_assumption(last_date, period, x3)

        except:

            df.loc[df.index.get_level_values('date') == last_date_period_end, 'assumption_zostatok'] = np.nan

            df.loc[df.index.get_level_values('date') == last_date_period_end, 'assumption_new_accounts_nr'] = np.nan

            df.loc[df.index.get_level_values('date') == last_date_period_end, 'assumption_existing_accounts_nr'] = np.nan

   

    return df

 

def tab2_chart1(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['existing_accounts_nr'],name = 'Existujuce ucty')

    trace1 = Scatter(x = x, y = df['plan_existing_accounts_nr'], name = 'Plan', visible = 'legendonly')

    trace2 = Scatter(x = x, y = df['perc_plan_existing_accounts_nr'], name = '% plnenia planu', yaxis = 'y2')

    trace3 = Scatter(x = x, y = df['assumption_existing_accounts_nr'].round(0), marker = dict(size = 10, color = '#B8001A'), mode = 'markers', name = 'Predpoklad')

    trace4 = Scatter(x = x, y = df['existing_and_activated_accounts_nr'], name = 'Zaktivnene ucty', visible = 'legendonly')

    trace5 = Scatter(x = x, y = df['perc_existing_and_activated_accounts_nr'], name = 'Zaktivnene ucty %', visible = 'legendonly', yaxis = 'y2')

    data = [trace0, trace1, trace2, trace3, trace4, trace5]

   

    layout = dict(title = 'Existujuce ucty',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]', hoverformat = ',.0'),

                      yaxis2 = dict(title = '%', side = 'right', overlaying = 'y', rangemode = 'tozero',

                                     tickformat = ',.0%', hoverformat = ',.2%'),

                    legend = dict(x = 1.08))

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab2_chart2(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['new_accounts_nr'],name = 'Nove ucty')

    trace1 = Scatter(x = x, y = df['plan_new_accounts_nr'], name = 'Plan', visible = 'legendonly')

    trace2 = Scatter(x = x, y = df['perc_plan_new_accounts_nr'], name = '% plnenia planu', yaxis = 'y2')

    trace3 = Scatter(x = x, y = df['assumption_new_accounts_nr'].round(0), marker = dict(size = 10, color = '#B8001A'), mode = 'markers', name = 'Predpoklad')

   

    data = [trace0, trace1, trace2, trace3]

   

    layout = dict(title = 'Nove ucty',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]', rangemode = 'tozero'),

                       yaxis2 = dict(title = '%', side = 'right', overlaying = 'y', rangemode = 'tozero',

                                     tickformat = ',.0%', hoverformat = ',.2%'),

                    legend = dict(x = 1.08))

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab2_chart3(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['zostatok'],name = 'Zostatky')

    trace1 = Scatter(x = x, y = df['plan_zostatky_accounts'], name = 'Plan', visible = 'legendonly')

    trace2 = Scatter(x = x, y = df['perc_plan_zostatky_accounts'], name = '% plnenia planu', yaxis = 'y2')

    trace3 = Scatter(x = x, y = df['assumption_zostatok'].round(0), marker = dict(size = 10, color = '#B8001A'), mode = 'markers', name = 'Predpoklad')

   

    data = [trace0, trace1, trace2, trace3]

   

    layout = dict(title = 'Zostatky',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = '[EUR]', hoverformat = ',.0f'),

                       yaxis2 = dict(title = '%', side = 'right', overlaying = 'y', rangemode = 'tozero',

                                     tickformat = ',.0%', hoverformat = ',.2%'),

                    legend = dict(x = 1.08))

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab2_chart4(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['avg_zostatok'],name = 'Vsetky BU')

    trace1 = Scatter(x = x, y = df['plan_avg_zostatok'], name = 'Plan', visible = 'legendonly')

    trace2 = Scatter(x = x, y = df['avg_zostatok_only_activated'], name = 'Zaktivnene', visible = False)

    trace3 = Scatter(x = x, y = df['perc_avg_zostatok'], name = 'Vsetky BU - % plnenia', yaxis = 'y2')

    trace4 = Scatter(x = x, y = df['perc_avg_zostatok_only_activated'], name = 'Zaktivnene - % plnenia', yaxis = 'y2', visible = False)

   

    data = [trace0, trace1, trace2, trace3, trace4]

   

    updatemenus = list([

            dict(type = 'buttons',

                 active = -1,

                 direction="right",

                x=0.01, y = 1.23,

                xanchor="left",

                yanchor="top",

                 buttons = list([

                         dict(label = 'Vsetky BU',

                              method = 'update',

                              args = [dict(visible = [True, 'legendonly', False, True, False])]),

                        dict(label = 'Zaktivnene BU',

                             method = 'update',

                             args = [dict(visible = [False, False, True, False, True])])

                       

                    ]))])   

    

    layout = dict(title = 'Priemerne zostatky',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Suma [EUR]', tickformat = ',.0', hoverformat = ',.2f', rangemode = 'tozero'),

                       yaxis2 = dict(title = '%', side = 'right', overlaying = 'y', rangemode = 'tozero',

                                     tickformat = ',.0%', hoverformat = ',.2%'),

                       updatemenus = updatemenus,

                    legend = dict(x = 1.08)

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab2_chart5(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['activated_accounts_nr'],name = 'Zaktivnene')

    trace1 = Scatter(x = x, y = df['activated_and_new_accounts_nr'], name = 'Nove', visible = False)

    trace2 = Scatter(x = x, y = df['perc_activated_from_existing'], name = 'Zaktivnene % z existujucich', yaxis = 'y2')

    trace3 = Scatter(x = x, y = df['perc_activated_and_new_accounts_nr_n'], name = 'Nove % zo zaktivnenych', yaxis = 'y2', visible = False)

 

    data = [trace0, trace1, trace2, trace3]

   

    updatemenus = list([

            dict(type = 'buttons',

                 active = -1,

                 direction="right",

                x=0.01, y = 1.23,

                xanchor="left",

                yanchor="top",

                 buttons = list([

                         dict(label = 'Zaktivnene',

                              method = 'update',

                              args = [dict(visible = [True, False, True, False])]),

                        dict(label = 'Nove',

                             method = 'update',

                             args = [dict(visible = [False, True, False, True])])

                       

                    ]))])   

    

    layout = dict(title = 'Zaktivnene ucty',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]', rangemode = 'tozero'),

                       updatemenus = updatemenus,

                       yaxis2 = dict(title = '%', side = 'right', overlaying = 'y', rangemode = 'tozero',

                                     tickformat = ',.0%', hoverformat = ',.2%'),

                    legend = dict(x = 1.08)

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab2_chart6(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['terminated_accounts_nr'],name = 'Zrusene')

    trace1 = Scatter(x = x, y = df['activated_and_terminated_accounts_nr'], name = 'Zaktivnene a zrusene', visible = 'legendonly')

    trace2 = Scatter(x = x, y = df['perc_terminated_accounts_nr'], name = 'Zrusene %', yaxis = 'y2')

    data = [trace0, trace1, trace2]

   

    layout = dict(title = 'Zrusene ucty',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]', rangemode = 'tozero'),

                       yaxis2 = dict(title = '%', side = 'right', overlaying = 'y', rangemode = 'tozero',

                                     tickformat = ',.2%', hoverformat = ',.2%'),

                    legend = dict(x = 1.08)

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

##################################################### tab3_1 - SPORENIA - VSEOBECNE METRIKY TAB #########################################

 

@app.callback(Output('content3_1', 'children'),

              [Input('tabs', 'value'),

               Input('tabs_sporenie', 'value'),

               Input('dropdown_period', 'value'),

               Input('datepicker_range', 'start_date'),

               Input('datepicker_range', 'end_date')])

def content3_1_children(tab_level1, tab_level2, period, start, end):

    if tab_level1 == 'tab3' and tab_level2 == 'tab1':

       

        df = tab3_1_data(period, start, end)       

        

        return html.Div([

                    html.Div([

                        html.Div(id = 'tab3_1_chart1_div', children = [dcc.Graph(id = 'tab3_1_chart1', figure = tab3_1_chart1(df))], className = 'six columns'),

                        html.Div(id = 'tab3_1_chart2_div', children = [dcc.Graph(id = 'tab3_1_chart2', figure = tab3_1_chart2(df))], className = 'six columns')

                           

                    ], className = 'row'),

   

                    html.Div([

                        html.Div(id = 'tab3_1_chart3_div', children = [dcc.Graph(id = 'tab3_1_chart3', figure = tab3_1_chart3(df))], className = 'six columns'),

                        html.Div(id = 'tab3_1_chart4_div', children = [dcc.Graph(id = 'tab3_1_chart4', figure = tab3_1_chart4(df))], className = 'six columns')

                            

                    ], className = 'row'),

   

                    html.Div([

                        html.Div(id = 'tab3_1_chart5_div', children = [dcc.Graph(id = 'tab3_1_chart5', figure = tab3_1_chart5(df))], className = 'six columns'),

                        html.Div(id = 'tab3_1_chart6_div', children = [dcc.Graph(id = 'tab3_1_chart6', figure = tab3_1_chart6(df))], className = 'six columns')

                           

                    ], className = 'row')

                   

                

        ])

 

def tab3_1_data(period, start, end):

    metrics = ['existing_accounts_nr', '72_clientsnr_with_atleast_1spu', 'new_accounts_nr', 'zostatok',

               'activated_accounts_nr','activated_and_new_accounts_nr',

               'terminated_accounts_nr', 'activated_and_terminated_accounts_nr',                  

               'existing_and_activated_accounts_nr', '72_new_clientsnr', '72_clientsnr_activ_atleast1spu',

               '72_clientsnr_with_atleast_1termin_spu', 'clients_with_1up_72active', '72_clientsnr_terminated_all'

               ]

   

    start = pd.to_datetime(start).normalize()

    end = pd.to_datetime(end).to_period(period).end_time.normalize()

 

    df = read_df(period)

    df = df.loc[(df.index.get_level_values('date') >= start) &

                (df.index.get_level_values('date') <= end), metrics]

   

    # dataframe containing metrics from other types of accounts

    # existing BU number (to calculate % of 72 accounts/clients from number of clients)

    df_oa = df.loc[df.index.get_level_values('id_typuct') == 70, ['existing_accounts_nr']]

    df_oa = df_oa.groupby(by = [pd.Grouper(level = 0, freq = period), pd.Grouper(level = 1)])\

        .agg({'existing_accounts_nr':'last'})\

        .rename(columns = {'existing_accounts_nr':'70_existing_accounts_nr'})

    df_oa.index = pd.MultiIndex.from_tuples([(i[0], 72) for i in df_oa.index], names = ('date', 'id_typuct'))

   

    # zosatky of all accounts, except 75 (to calculate % of 72 from all zostatky)

    df_oa1 = df.loc[~(df.index.get_level_values('id_typuct') == 75), ['zostatok']]\

        .groupby(pd.Grouper(level = 0, freq = 'D'))\

        .agg({'zostatok':'sum'})\

        .groupby(pd.Grouper(level = 0, freq = period))\

        .agg({'zostatok':'last'})\

        .rename(columns = {'zostatok':'zostatok_all'})

    df_oa1.index = pd.MultiIndex.from_tuples([(i, 72) for i in df_oa1.index], names = ('date', 'id_typuct'))

 

   

    df = df.loc[df.index.get_level_values('id_typuct') == 72,:]

   

    last_date = pd.to_datetime(datetime.now())

   

    df = df.join(df_oa)\

        .join(df_oa1) # joined with dataframe containing other id_typuct metrics   

 

    # calculate new metrics

   

    # priemerne zostatky na vsetkych existujucich sporiacich uctoch

    df['avg_zostatok'] = df['zostatok']/df['existing_accounts_nr']

         

    # priemerne zostatky na zaktivovanych sporiacich uctoch uctoch

    df['avg_zostatok_only_activated'] = df['zostatok']/df['existing_and_activated_accounts_nr']

   

    # % klientov, ktori maju aspon 1 sporenie z celkoveho poctu klientov

    df['perc_72clients_atleast1'] = df['72_clientsnr_with_atleast_1spu']/df['70_existing_accounts_nr']

   

    # % klientov, ktori maju aspon 1 zaktivnene sporenie z celkoveho poctu klientov

    df['perc_72_clientsnr_activ_atleast1spu'] = df['clients_with_1up_72active']/df['70_existing_accounts_nr']

   

    # priemerny pocet sporiacich uctov na klienta (cela baza a z len tych co maju aspon 1 SpU)

    df['avg_72count_from_all_clients'] = df['existing_accounts_nr']/df['70_existing_accounts_nr']

    df['avg_72count_from_1upclients'] = df['existing_accounts_nr']/df['72_clientsnr_with_atleast_1spu']

   

    # % 72 zostatkov z celkovych zostatkov

    df['perc_72zostatky_fromall'] = df['zostatok']/df['zostatok_all']

   

    # priemerny zostatok na klienta a na klienta s aspon 1 SpU

    df['avg_zostatok_all_clients'] = df['zostatok']/df['70_existing_accounts_nr']

    df['avg_zostatok_1up_clients'] = df['zostatok']/df['72_clientsnr_with_atleast_1spu']

   

    # % zrusenych uctov z existujucich uctov

    df['perc_72_term_from_exist'] = df['terminated_accounts_nr']/df['existing_accounts_nr']

   

    # % klientov co zrusili aspon 1 spu z klientov s aspon 1 spu

    df['perc_72_term_clientsnr'] = df['72_clientsnr_with_atleast_1termin_spu']/df['72_clientsnr_with_atleast_1spu']

   

    # % klientov co zrusili vstky svoje sporiace ucty z klientov s aspon 1 sporiacim uctom   

    df['perc_72_clientsnr_terminated_all'] = df['72_clientsnr_terminated_all']/df['72_clientsnr_with_atleast_1spu']

   

    # % existujucich zaktivnenych uctov zo vsetkych sporiacich uctov   

    df['perc_existing_and_activated_accounts_nr'] = df['existing_and_activated_accounts_nr']/df['existing_accounts_nr']

   

    # % zaktivnenych uctov z existujucich zaktivnenych uctov   

    df['perc_activated_from_existing'] = df['activated_accounts_nr']/df['existing_and_activated_accounts_nr']

   

    # % zaktivnenych uctov a zaroven novych uctov zo zaktivnenych uctov

    df['perc_activated_and_new_accounts_nr'] = df['activated_and_new_accounts_nr']/df['activated_accounts_nr']

   

    # % zaktivnenych klientov z existujucich zaktivnenych klientov

    df['perc_activated_clients_from_exisiting'] = df['72_clientsnr_activ_atleast1spu']/df['clients_with_1up_72active']

   

    

    # predpoklad v aktualnej periode (okrem dennej) - eistujuce ucty, nove ucty, zostatky

    df['assumption_existing_accounts_nr'] = np.nan

    df['assumption_new_accounts_nr'] = np.nan

    df['assumption_zostatok'] = np.nan

   

    if period != 'D':

        last_date_period_end = last_date.to_period(period).end_time.normalize()

        if period == 'W':

            last_date_period_end_1 = last_date_period_end - pd.DateOffset(weeks = 1)

        elif period == 'M':

            last_date_period_end_1 = (last_date_period_end - pd.DateOffset(months = 1)).to_period(period).end_time.normalize()

        elif period == 'Q':

            last_date_period_end_1 = last_date_period_end - pd.DateOffset(months = 3)

        elif period == 'Y':

            last_date_period_end_1 = last_date_period_end - pd.DateOffset(years = 1)

       

        try:

            # predpoklad - nove ucty

            x1 = df.loc[df.index.get_level_values('date') == last_date_period_end,

                   'new_accounts_nr']

            df.loc[df.index.get_level_values('date') == last_date_period_end,

                   'assumption_new_accounts_nr'] = calculate_assumption(last_date, period, x1)

           

            # predpoklad - existujuce ucty

            df.loc[df.index.get_level_values('date') == last_date_period_end,

                   'assumption_existing_accounts_nr'] = df['existing_accounts_nr'] - df['new_accounts_nr'] + df['assumption_new_accounts_nr']

 

       

            # predpoklad - zostatky - ratane cez prirastok zostatkov

            x3_1 = df.loc[df.index.get_level_values('date') == last_date_period_end, 'zostatok']

        

            x3_2 = df.loc[df.index.get_level_values('date') == last_date_period_end_1, 'zostatok']

           

            x3_2.index = [(last_date_period_end, i[1]) for i in x3_2.index]

            x3 = x3_1 - x3_2

           

            df.loc[df.index.get_level_values('date') == last_date_period_end,

                   'assumption_zostatok'] = df['zostatok'] - x3 + calculate_assumption(last_date, period, x3)

        except:

            df.loc[df.index.get_level_values('date') == last_date_period_end, 'assumption_zostatok'] = np.nan

            df.loc[df.index.get_level_values('date') == last_date_period_end, 'assumption_new_accounts_nr'] = np.nan 

            df.loc[df.index.get_level_values('date') == last_date_period_end, 'assumption_existing_accounts_nr'] = np.nan

    return df

   

def tab3_1_chart1(df):

    x = df.index.get_level_values('date')

   

    trace1 = Scatter(x = x, y = df['existing_accounts_nr'],name = 'Existujuce ucty')

    trace1_1 = Scatter(x = x, y = df['72_clientsnr_with_atleast_1spu'], name = 'Klienti s aspon 1 SpU', visible = False)

    trace1_2 = Scatter(x = x, y = df['clients_with_1up_72active'], name = 'Klienti s aspon 1 zaktiv. SpU', visible = False)

    trace1_3 = Scatter(x = x, y = df['existing_and_activated_accounts_nr'], name = 'Zaktivnene ucty', visible = 'legendonly')

    trace1_4 = Scatter(x = x, y = df['perc_existing_and_activated_accounts_nr'], name = 'Zaktivnene ucty %', visible = 'legendonly', yaxis = 'y2')

    trace2 = Scatter(x = x, y = df['assumption_existing_accounts_nr'].round(0), marker = dict(size = 10, color = '#B8001A'), mode = 'markers', name = 'Predpoklad')

    trace3 = Scatter(x = x, y = df['perc_72clients_atleast1'], name = 'Klienti s aspon 1 SpU %', yaxis = 'y2', visible = False)

    trace3_1 = Scatter(x = x, y = df['perc_72_clientsnr_activ_atleast1spu'], name = 'Klienti s aspon 1 zaktiv. SpU %', visible = False, yaxis = 'y2')

    trace4 = Scatter(x = x, y = df['avg_72count_from_all_clients'].round(2), name = 'Zo vsetkych klientov', visible = False)

    trace5 = Scatter(x = x, y = df['avg_72count_from_1upclients'].round(2), name = 'Z klientov s aspon 1 Spu', visible = False)

   

    data = [trace1, trace1_1, trace1_2, trace1_3, trace1_4, trace2, trace3, trace3_1, trace4, trace5]

   

    updatemenus = list([

            dict(type = 'buttons',

                 active = -1,

                 direction="right",

                x=-0.1, y = 1.23,

                xanchor="left",

                yanchor="top",

                 buttons = list([

                         dict(label = 'Ucty',

                              method = 'update',

                              args = [dict(visible = [True, False, False, 'legendonly', 'legendonly', True, False, False, False, False])]),

                        dict(label = 'Klienti',

                             method = 'update',

                             args = [dict(visible = [False, True, 'legendonly', False, False, False, True, 'legendonly', False, False])]),

                        dict(label = 'Priemerny pocet SpU',

                             method = 'update',

                             args = [dict(visible = [False, False, False, False, False, False, False, False, True, True])])

                       

                    ]))]) # nejde zmena title

   

    layout = dict(title = 'Existujuce ucty',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]'),

                       yaxis2 = dict(title = '%', side = 'right', overlaying = 'y', rangemode = 'tozero',

                                     tickformat = ',.0%', hoverformat = ',.2%'),

                        updatemenus = updatemenus,

                    legend = dict(x = 1.08))

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab3_1_chart2(df):

    x = df.index.get_level_values('date')

   

    trace1 = Scatter(x = x, y = df['new_accounts_nr'],name = 'Nove ucty')

    trace2 = Scatter(x = x, y = df['assumption_new_accounts_nr'].round(0), marker = dict(size = 10, color = '#B8001A'), mode = 'markers', name = 'Predpoklad')

    trace3 = Scatter(x = x, y = df['72_new_clientsnr'], name = 'Novi klienti')

   

    data = [trace1, trace2, trace3]

   

    layout = dict(title = 'Nove ucty',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]'),

                       yaxis2 = dict(title = '%', side = 'right', overlaying = 'y', rangemode = 'tozero',

                                     tickformat = ',.0%', hoverformat = ',.2%'))

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab3_1_chart3(df):

    x = df.index.get_level_values('date')

   

    trace1 = Scatter(x = x, y = df['zostatok'],name = 'Zostatky')

    trace2 = Scatter(x = x, y = df['assumption_zostatok'].round(0), marker = dict(size = 10, color = '#B8001A'), mode = 'markers', name = 'Predpoklad')

    trace3 = Scatter(x = x, y = df['perc_72zostatky_fromall'], name = 'Zostatky %', yaxis = 'y2')

   

    data = [trace1, trace2, trace3]

   

    layout = dict(title = 'Zostatky',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = '[EUR]', hoverformat = ',.0f'),

                       yaxis2 = dict(title = '%', side = 'right', overlaying = 'y', rangemode = 'tozero',

                                     tickformat = ',.0%', hoverformat = ',.2%'),

                    legend = dict(x = 1.08))

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab3_1_chart4(df):

    x = df.index.get_level_values('date')

   

    trace1 = Scatter(x = x, y = df['avg_zostatok'].round(2),name = 'Vsetky SpU')

    trace2 = Scatter(x = x, y = df['avg_zostatok_only_activated'].round(2), name = 'Zaktivnene')

    trace3 = Scatter(x = x, y = df['avg_zostatok_all_clients'].round(2), name = 'Vsetci klienti', visible = False)

    trace4 = Scatter(x = x, y = df['avg_zostatok_1up_clients'].round(2), name = 'Klienti s aspon 1 SpU', visible = False)

   

    data = [trace1, trace2, trace3, trace4]

   

    updatemenus = list([

            dict(type = 'buttons',

                 active = -1,

                 direction="right",

                x=0.01, y = 1.23,

               xanchor="left",

                yanchor="top",

                 buttons = list([

                         dict(label = 'Ucty',

                              method = 'update',

                              args = [dict(visible = [True, True, False, False],

                                           title = 'Priemerne zostatky - ucty')]),

                        dict(label = 'Klienti',

                             method = 'update',

                             args = [dict(visible = [False, False, True, True],

                                          title = 'Priemerne zostatky - klienti')])]))])

   

    layout = dict(title = 'Priemerne zostatky',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = '[EUR]', tickformat = ',.0', hoverformat = ',.2'),

                       updatemenus = updatemenus

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab3_1_chart5(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['activated_accounts_nr'],name = 'Zaktivnene')

    trace1 = Scatter(x = x, y = df['activated_and_new_accounts_nr'], name = 'Nove', visible = 'legendonly')

    trace2 = Scatter(x = x, y = df['perc_activated_from_existing'], name = 'Zaktivnene % z existujucich', yaxis = 'y2')

    trace3 = Scatter(x = x, y = df['perc_activated_and_new_accounts_nr'], name = 'Nove % zo zaktivnenych', yaxis = 'y2', visible = 'legendonly')

   

    trace4 = Scatter(x = x, y = df['72_clientsnr_activ_atleast1spu'], name = 'Zaktivneni klienti', visible = False)

    trace5 = Scatter(x = x, y = df['perc_activated_clients_from_exisiting'], name = 'Zaktivneni klienti % z exist.', visible = False, yaxis = 'y2')

 

 

    data = [trace0, trace1, trace2, trace3, trace4, trace5]

   

    updatemenus = list([

            dict(type = 'buttons',

                 active = -1,

                 direction="right",

                x=0.01, y = 1.23,

                xanchor="left",

                yanchor="top",

                 buttons = list([

                         dict(label = 'Ucty',

                              method = 'update',

                              args = [dict(visible = [True, 'legendonly', True, 'legendonly', False, False])]),

                        dict(label = 'Klienti',

                             method = 'update',

                             args = [dict(visible = [False, False, False, False, True, True])])]))])   

    

    layout = dict(title = 'Zaktivnene ucty',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]'),

                       updatemenus = updatemenus,

                       yaxis2 = dict(title = '%', side = 'right', overlaying = 'y', rangemode = 'tozero',

                                     tickformat = ',.0%', hoverformat = ',.2%')

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab3_1_chart6(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['terminated_accounts_nr'],name = 'Zrusene')

    trace1 = Scatter(x = x, y = df['activated_and_terminated_accounts_nr'], name = 'Zaktivnene a zrusene', visible = 'legendonly')

    trace2 = Scatter(x = x, y = df['72_clientsnr_with_atleast_1termin_spu'], name = 'Klienti s min 1 zru. SpU', visible = False)

    trace3 = Scatter(x = x, y = df['perc_72_term_from_exist'], name = 'Zrusene %', yaxis = 'y2')

    trace4 = Scatter(x = x, y = df['perc_72_term_clientsnr'], name = 'Klienti s min 1 zru. SpU %', visible = False, yaxis = 'y2')

    trace5 = Scatter(x = x, y = df['72_clientsnr_terminated_all'], name = 'Zruseni klienti', visible = False)

    trace6 = Scatter(x = x, y = df['perc_72_clientsnr_terminated_all'], name = 'Zruseni klienti %', visible = False, yaxis = 'y2')

   

    data = [trace0, trace1, trace2, trace3, trace4, trace5, trace6]

   

    updatemenus = list([

            dict(type = 'buttons',

                 active = -1,

                 direction="right",

                x=0.01, y = 1.23,

                xanchor="left",

                yanchor="top",

                 buttons = list([

                         dict(label = 'Ucty',

                              method = 'update',

                              args = [dict(visible = [True, 'legendonly', False, True, False, False, False])]),

                        dict(label = 'Klienti',

                             method = 'update',

                             args = [dict(visible = [False, False, 'legendonly', False, 'legendonly', True, True])])]))])

   

    layout = dict(title = 'Zrusene ucty',

                       xaxis = dict(title = 'Datum', rangemode = 'tozero'),

                       yaxis = dict(title = 'Pocet [ks]'),

                       updatemenus = updatemenus,

                       yaxis2 = dict(title = '%', side = 'right', overlaying = 'y', rangemode = 'tozero',

                                     tickformat = ',.0%', hoverformat = ',.2%'),

                    legend = dict(x = 1.08)

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

##################################################### tab3_2 SPORENIA - SPECIFICKE METRIKY ################################

   

@app.callback(Output('content3_2', 'children'),

              [Input('tabs', 'value'),

               Input('tabs_sporenie', 'value'),

               Input('dropdown_period', 'value'),

               Input('datepicker_range', 'start_date'),

               Input('datepicker_range', 'end_date')])

def content3_2_children(tab_level1, tab_level2, period, start, end):

    if tab_level1 == 'tab3' and tab_level2 == 'tab2':

       

        df, df_banks72 = tab3_2_data(period, start, end)

 

       

        return html.Div([

                    html.Div([

                        html.Div(id = 'tab3_2_chart1_div', children = [dcc.Graph(id = 'tab3_2_chart1', figure = tab3_2_chart1(df))], className = 'six columns'),

                        html.Div(id = 'tab3_2_chart2_div', children = [dcc.Graph(id = 'tab3_2_chart2', figure = tab3_2_chart2(df))], className = 'six columns')

                            

                    ], className = 'row'),

   

                    html.Div([

                        html.Div(id = 'tab3_2_chart3_div', children = [dcc.Graph(id = 'tab3_2_chart3', figure = tab3_2_chart3(df))], className = 'six columns'),

                        html.Div(id = 'tab3_2_chart4_div', children = [dcc.Graph(id = 'tab3_2_chart4', figure = tab3_2_chart4(df))], className = 'six columns')

                           

                    ], className = 'row'),

   

                    html.Div([

                        html.Div(id = 'tab3_2_chart5_div', children = [dcc.Graph(id = 'tab3_2_chart5', figure = tab3_2_chart5(df_banks72))], className = 'six columns'),

                        html.Div(id = 'tab3_2_chart6_div', children = [dcc.Graph(id = 'tab3_2_chart6', figure = tab3_2_chart6(df))], className = 'six columns')

                           

                    ], className = 'row'),

   

                    html.Div([

                        html.Div(id = 'tab3_2_chart7_div', children = [dcc.Graph(id = 'tab3_2_chart7', figure = tab3_2_chart7(df))], className = 'six columns'),

                        html.Div(id = 'tab3_2_chart8_div', children = [dcc.Graph(id = 'tab3_2_chart8', figure = tab3_2_chart8(df))], className = 'six columns')

                           

                    ], className = 'row'),

   

                    html.Div([

                        html.Div(id = 'tab3_2_chart9_div', children = [dcc.Graph(id = 'tab3_2_chart9', figure = tab3_2_chart9(df))], className = 'six columns'),

                        html.Div(id = 'tab3_2_chart10_div', children = [dcc.Graph(id = 'tab3_2_chart10', figure = None)], className = 'six columns')

                           

                    ], className = 'row')

                    

                

        ])

                           

def tab3_2_data(period, start, end):

    metrics = [

                'existing_accounts_nr', '72_clientsnr_with_atleast_1spu',

               '70to72tp_count', '70to72tp_sum',

               '70to72tp_sporeni_count', '70to72tp_clients_count', '70to72_trans_count',

               '70to72_trans_sum', '70to72_spu_count', '70to72_clients_count', '72paid_interest_clients_count',

               '72paid_interest_sporeni_count', '72paid_interest_sum', '72withdraw_clients_count',

               '72withdraw_sporeni_count', '72withdraw_sum', 'otherto72_trans_count', 'otherto72_trans_sum',

               'otherto72_spu_count', 'otherto72_clients_count'

               ]

   

    start = pd.to_datetime(start).normalize()

    end = pd.to_datetime(end).to_period(period).end_time.normalize()

   

    df = read_df(period)

    df = df.loc[(df.index.get_level_values('date') >= start) &

                (df.index.get_level_values('date') <= end), metrics]

    df = df.loc[df.index.get_level_values('id_typuct') == 72,:]

   

    df_banks72 = read_banks72(period)

    df_banks72 = df_banks72.loc[(df_banks72.index.get_level_values('date') >= start) &

                (df_banks72.index.get_level_values('date') <= end),:] # dataframe going into only 1 chart

    df_banks72 = df_banks72.groupby(by = pd.Grouper(level = 0, freq = period)).sum()

 

    # calculate new metrics

   

    # % sporiacich uctov, na ktore boli realizovane trvale prikazy zo vsetkych sporiacich uctov

    df['perc_70to72tp_sporeni_count'] = df['70to72tp_sporeni_count']/df['existing_accounts_nr']

    df['perc_70to72tp_clients_count'] = df['70to72tp_clients_count']/df['72_clientsnr_with_atleast_1spu']

   

    # priemerny pocet a priemerna suma transakcii z BU na SPu na klienta a na ucet

   

    df['avg_70to72_trans_count_spu'] = df['70to72_trans_count']/df['70to72_spu_count']

    df['avg_70to72_trans_sum_spu'] = df['70to72_trans_sum']/df['70to72_spu_count']

    df['avg_70to72_trans_count_client'] = df['70to72_trans_count']/df['70to72_clients_count']

    df['avg_70to72_trans_sum_client'] = df['70to72_trans_sum']/df['70to72_clients_count']

   

    # priemerny pocet a priemerna suma transakcii z ineho ako  BU na SPu na klienta a na ucet

   

    df['avg_otherto72_trans_count_spu'] = df['otherto72_trans_count']/df['otherto72_spu_count']

    df['avg_otherto72_trans_sum_spu'] = df['otherto72_trans_sum']/df['otherto72_spu_count']

    df['avg_otherto72_trans_count_client'] = df['otherto72_trans_count']/df['otherto72_clients_count']

    df['avg_otherto72_trans_sum_client'] = df['otherto72_trans_sum']/df['otherto72_clients_count']

   

    # vyplatene uroky z SpU - % z celkoveho poctu SpU a klientov s aspon 1 SpU

   

    df['perc_72paid_interest_spu'] = df['72paid_interest_sporeni_count']/df['existing_accounts_nr']

    df['perc_72paid_interest_clients'] = df['72paid_interest_clients_count']/df['72_clientsnr_with_atleast_1spu']

   

    # vyplatene uroky z SpU - priemer na SpU a klienta, ktorim boli uroky vyplatene

   

    df['avg_72paid_interest_spu'] = df['72paid_interest_sum']/df['72paid_interest_sporeni_count']

    df['avg_72paid_interest_client'] = df['72paid_interest_sum']/df['72paid_interest_clients_count']

   

    # vybery z SpU - % z celkoveho poctu SpU a klientov s aspon 1 SpU

   

    df['perc_72withdraw_spu'] = df['72withdraw_sporeni_count']/df['existing_accounts_nr']

    df['perc_72withdraw_clients'] = df['72withdraw_clients_count']/df['72_clientsnr_with_atleast_1spu']

   

    # vybery s SpU- priemer na - priemer na SpU a klienta, ktori vyberi vykonali

   

    df['avg_72withdraw_spu'] = df['72withdraw_sum']/df['72withdraw_sporeni_count']

    df['avg_72withdraw_client'] = df['72withdraw_sum']/df['72withdraw_clients_count']

       

    return df, df_banks72

 

def tab3_2_chart1(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['70to72tp_count'],name = 'Pocet TP')

    trace1 = Scatter(x = x, y = df['70to72tp_sum'], name = 'Suma TP', yaxis = 'y2')

    data = [trace0, trace1]

   

    layout = dict(title = 'Zrealizovane trvale prikazy z vlastneho BU na SpU - celkovo',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]', rangemode = 'tozero'),

                       yaxis2 = dict(title = 'Suma [EUR]', side = 'right', overlaying = 'y', rangemode = 'tozero', hoverformat = ',.0f'),

                    legend = dict(x = 1.08)

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab3_2_chart2(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['70to72tp_sporeni_count'],name = 'Pocet SpU')

    trace1 = Scatter(x = x, y = df['70to72tp_clients_count'], name = 'Pocet klientov', visible = False)

    trace2 = Scatter(x = x, y = df['perc_70to72tp_sporeni_count'], name = 'Pocet SpU %', yaxis = 'y2')

    trace3 = Scatter(x = x, y = df['perc_70to72tp_clients_count'], name = 'Pocet klientov %', visible = False, yaxis = 'y2')

   

    data = [trace0, trace1, trace2, trace3]

   

    updatemenus = list([

            dict(type = 'buttons',

                 active = -1,

                 direction="right",

                x=0.01, y = 1.23,

                xanchor="left",

                yanchor="top",

                 buttons = list([

                         dict(label = 'Ucty',

                              method = 'update',

                              args = [dict(visible = [True, False, True, False])]),

                        dict(label = 'Klienti',

                             method = 'update',

                             args = [dict(visible = [False, True, False, True])])]))])

   

    layout = dict(title = 'SpU a klienti s realizovanym TP z vlastneho BU',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]', rangemode = 'tozero'),

                       updatemenus = updatemenus,

                       yaxis2 = dict(title = '%', side = 'right', overlaying = 'y', rangemode = 'tozero',

                                     tickformat = ',.0%', hoverformat = ',.2%'),

                    legend = dict(x = 1.08)

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab3_2_chart3(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['70to72_trans_count'],name = 'Pocet')

    trace1 = Scatter(x = x, y = df['70to72_trans_sum'], name = 'Suma', yaxis = 'y2')

    trace2 = Scatter(x = x, y = df['avg_70to72_trans_count_spu'].round(2), name = 'Priemerny pocet', visible = False)

    trace3 = Scatter(x = x, y = df['avg_70to72_trans_sum_spu'].round(2), name = 'Priemerna suma', visible = False, yaxis = 'y2')

    trace4 = Scatter(x = x, y = df['avg_70to72_trans_count_client'].round(2), name = 'Priemerny pocet', visible = False)

    trace5 = Scatter(x = x, y = df['avg_70to72_trans_sum_client'].round(2), name = 'Priemerna suma', visible = False, yaxis = 'y2')

   

    data = [trace0, trace1, trace2, trace3, trace4, trace5]

   

    updatemenus = list([

            dict(type = 'buttons',

                 active = -1,

                 direction="right",

                x=0.01, y = 1.23,

                xanchor="left",

                yanchor="top",

                 buttons = list([

                         dict(label = 'Celkovo',

                              method = 'update',

                              args = [dict(visible = [True, True, False, False, False, False])]),

                        dict(label = 'Ucty',

                             method = 'update',

                             args = [dict(visible = [False, False, True, True, False, False])]),

                        dict(label = 'Klienti',

                             method = 'update',

                             args = [dict(visible = [False, False, False, False, True, True])])]))])

   

    layout = dict(title = 'Transakcie z vl. BU na SpU',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]', rangemode = 'tozero'),

                       yaxis2 = dict(title = 'Suma [EUR]', side = 'right', overlaying = 'y', rangemode = 'tozero', hoverformat = ',.2f'),

                       updatemenus = updatemenus,

                    legend = dict(x = 1.08)

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab3_2_chart4(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['otherto72_trans_count'],name = 'Pocet')

    trace1 = Scatter(x = x, y = df['otherto72_trans_sum'], name = 'Suma', yaxis = 'y2')

    trace2 = Scatter(x = x, y = df['avg_otherto72_trans_count_spu'].round(2), name = 'Priemerny pocet', visible = False)

    trace3 = Scatter(x = x, y = df['avg_otherto72_trans_sum_spu'].round(2), name = 'Priemerna suma', visible = False, yaxis = 'y2')

    trace4 = Scatter(x = x, y = df['avg_otherto72_trans_count_client'].round(2), name = 'Priemerny pocet', visible = False)

    trace5 = Scatter(x = x, y = df['avg_otherto72_trans_sum_client'].round(2), name = 'Priemerna suma', visible = False, yaxis = 'y2')

   

    data = [trace0, trace1, trace2, trace3, trace4, trace5]

   

    updatemenus = list([

            dict(type = 'buttons',

                 active = -1,

                 direction="right",

                x=0.01, y = 1.23,

                xanchor="left",

                yanchor="top",

                 buttons = list([

                         dict(label = 'Celkovo',

                              method = 'update',

                              args = [dict(visible = [True, True, False, False, False, False])]),

                        dict(label = 'Ucty',

                             method = 'update',

                             args = [dict(visible = [False, False, True, True, False, False])]),

                        dict(label = 'Klienti',

                             method = 'update',

                             args = [dict(visible = [False, False, False, False, True, True])])]))])

   

    layout = dict(title = 'Transakcie z ineho U na SpU',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]', rangemode = 'tozero'),

                       yaxis2 = dict(title = 'Suma [EUR]', side = 'right', overlaying = 'y', rangemode = 'tozero', hoverformat = ',.2f'),

                       updatemenus = updatemenus,

                    legend = dict(x = 1.08)

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab3_2_chart5(df):

    x = df.index.get_level_values('date')

       

    data = [Scatter(x = x, y = df[i], name = i, visible = 'legendonly' if i not in ['TATRA', 'PABK', 'UNICREDIT', 'CSOB'] else True) for i in df.columns]

   

    layout = dict(title = 'Transakcie z ineho U na SpU - banky',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]')

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab3_2_chart6(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['72paid_interest_sporeni_count'],name = 'Pocet SpU', visible = 'legendonly')

    trace1 = Scatter(x = x, y = df['72paid_interest_clients_count'], name = 'Pocet klientov')

    trace2 = Scatter(x = x, y = df['72paid_interest_sum'], name = 'Suma', yaxis = 'y2')

   

    data = [trace0, trace1, trace2]

   

    layout = dict(title = 'Vyplatene uroky z SpU - celkovo',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]', rangemode = 'tozero'),

                       yaxis2 = dict(title = 'Suma [EUR]', side = 'right', overlaying = 'y', rangemode = 'tozero'),

                    legend = dict(x = 1.08)

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab3_2_chart7(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['avg_72paid_interest_spu'], name = 'Priemer na SpU')

    trace1 = Scatter(x = x, y = df['perc_72paid_interest_spu'], name = 'SpU %', yaxis = 'y2')

    trace2 = Scatter(x = x, y = df['avg_72paid_interest_client'], name = 'Priemer na klienta', visible = False)

    trace3 = Scatter(x = x, y = df['perc_72paid_interest_clients'], name = 'Klienti %', visible = False, yaxis = 'y2')

   

    data = [trace0, trace1, trace2, trace3]

   

    updatemenus = list([

            dict(type = 'buttons',

                 active = -1,

                 direction="right",

                x=0.01, y = 1.23,

                xanchor="left",

                yanchor="top",

                 buttons = list([

                         dict(label = 'Ucty',

                              method = 'update',

                              args = [dict(visible = [True, True, False, False])]),

                        dict(label = 'Klienti',

                             method = 'update',

                             args = [dict(visible = [False, False, True, True])])]))])

   

    layout = dict(title = 'Vyplatene uroky z SpU - priemery a %',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Suma [EUR]', hoverformat = ',.2f'),

                       updatemenus = updatemenus,

                       yaxis2 = dict(title = '%', side = 'right', overlaying = 'y', rangemode = 'tozero',

                                     tickformat = ',.0%', hoverformat = ',.2%'),

                    legend = dict(x = 1.08)

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab3_2_chart8(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['72withdraw_sporeni_count'],name = 'Pocet SpU', visible = 'legendonly')

    trace1 = Scatter(x = x, y = df['72withdraw_clients_count'], name = 'Pocet klientov')

    trace2 = Scatter(x = x, y = df['72withdraw_sum'], name = 'Suma', yaxis = 'y2')

   

    data = [trace0, trace1, trace2]

   

    layout = dict(title = 'Vybery z SpU - celkovo',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]', rangemode = 'tozero'),

                       yaxis2 = dict(title = 'Suma [EUR]', side = 'right', overlaying = 'y', rangemode = 'tozero', hoverformat = ',.2f'),

                    legend = dict(x = 1.08)

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab3_2_chart9(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['avg_72withdraw_spu'], name = 'Priemer na SpU')

    trace1 = Scatter(x = x, y = df['perc_72withdraw_spu'], name = 'SpU %', yaxis = 'y2')

    trace2 = Scatter(x = x, y = df['avg_72withdraw_client'], name = 'Priemer na klienta', visible = False)

    trace3 = Scatter(x = x, y = df['perc_72withdraw_clients'], name = 'Klienti %', visible = False, yaxis = 'y2')

   

    data = [trace0, trace1, trace2, trace3]

   

    updatemenus = list([

            dict(type = 'buttons',

                 active = -1,

                 direction="right",

                x=0.01, y = 1.23,

                xanchor="left",

                yanchor="top",

                 buttons = list([

                         dict(label = 'Ucty',

                              method = 'update',

                              args = [dict(visible = [True, True, False, False])]),

                        dict(label = 'Klienti',

                             method = 'update',

                             args = [dict(visible = [False, False, True, True])])]))])

   

    layout = dict(title = 'Vybery z SpU - priemery a %',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Suma [EUR]', hoverformat = ',.2f'),

                       updatemenus = updatemenus,

                       yaxis2 = dict(title = '%', side = 'right', overlaying = 'y', rangemode = 'tozero',

                                     tickformat = ',.0%', hoverformat = ',.2%'),

                    legend = dict(x = 1.08)

            )

   fig = Figure(data = data, layout = layout)

   

    return fig

 

                           

##################################################### tab4_1 - SYSLENIA - VSEOBECNE METRIKY TAB #########################################

 

@app.callback(Output('content4_1', 'children'),

              [Input('tabs', 'value'),

               Input('tabs_syslenie', 'value'),

               Input('dropdown_period', 'value'),

               Input('datepicker_range', 'start_date'),

               Input('datepicker_range', 'end_date')])

def content4_1_children(tab_level1, tab_level2, period, start, end):

    if tab_level1 == 'tab4' and tab_level2 == 'tab1':

 

        df = tab4_1_data(period, start, end)

       

        return html.Div([

                    html.Div([

                        html.Div(id = 'tab4_1_chart1_div', children = [dcc.Graph(id = 'tab4_1_chart1', figure = tab4_1_chart1(df))], className = 'six columns'),

                        html.Div(id = 'tab4_1_chart2_div', children = [dcc.Graph(id = 'tab4_1_chart2', figure = tab4_1_chart2(df))], className = 'six columns')

                           

                    ], className = 'row'),

   

                    html.Div([

                        html.Div(id = 'tab4_1_chart3_div', children = [dcc.Graph(id = 'tab4_1_chart3', figure = tab4_1_chart3(df))], className = 'six columns'),

                        html.Div(id = 'tab4_1_chart4_div', children = [dcc.Graph(id = 'tab4_1_chart4', figure = tab4_1_chart4(df))], className = 'six columns')

                           

                    ], className = 'row'),

   

                    html.Div([

                        html.Div(id = 'tab4_1_chart5_div', children = [dcc.Graph(id = 'tab4_1_chart5', figure = tab4_1_chart5(df))], className = 'six columns'),

                        html.Div(id = 'tab4_1_chart6_div', children = [dcc.Graph(id = 'tab4_1_chart6', figure = tab4_1_chart6(df))], className = 'six columns')

                           

                    ], className = 'row')

                   

                

        ])

 

def tab4_1_data(period, start, end):

    metrics = ['existing_accounts_nr', 'new_accounts_nr', 'zostatok',

               'activated_accounts_nr','activated_and_new_accounts_nr',

               'terminated_accounts_nr', 'activated_and_terminated_accounts_nr',                  

               'existing_and_activated_accounts_nr', 'clients_with_1up_71active'

               ]

   

    start = pd.to_datetime(start).normalize()

    end = pd.to_datetime(end).to_period(period).end_time.normalize()

   

    df = read_df(period)

    df = df.loc[(df.index.get_level_values('date') >= start) &

                (df.index.get_level_values('date') <= end), metrics]

   

    # dataframe containing metrics from other types of accounts

    # existing BU number (to calculate % of 72 accounts/clients from number of clients)

    df_oa = df.loc[df.index.get_level_values('id_typuct') == 70, ['existing_accounts_nr']]

    df_oa = df_oa.groupby(by = [pd.Grouper(level = 0, freq = period), pd.Grouper(level = 1)])\

        .agg({'existing_accounts_nr':'last'})\

        .rename(columns = {'existing_accounts_nr':'70_existing_accounts_nr'})

    df_oa.index = pd.MultiIndex.from_tuples([(i[0], 71) for i in df_oa.index], names = ('date', 'id_typuct'))

   

    # zosatky of all accounts, except 75 (to calculate % of 72 from all zostatky)

    df_oa1 = df.loc[~(df.index.get_level_values('id_typuct') == 75), ['zostatok']]\

        .groupby(pd.Grouper(level = 0, freq = 'D'))\

        .agg({'zostatok':'sum'})\

        .groupby(pd.Grouper(level = 0, freq = period))\

        .agg({'zostatok':'last'})\

        .rename(columns = {'zostatok':'zostatok_all'})

    df_oa1.index = pd.MultiIndex.from_tuples([(i, 71) for i in df_oa1.index], names = ('date', 'id_typuct'))

   

    df = df.loc[df.index.get_level_values('id_typuct') == 71,:]

   

    last_date = pd.to_datetime(datetime.now())

 

 

    df = df.join(df_oa)\

        .join(df_oa1) # joined with dataframe containing other id_typuct metrics 

            

    # calculate new metrics

   

    # priemerne zostatky na vsetkych existujucich sporiacich uctoch

    df['avg_zostatok'] = df['zostatok']/df['existing_accounts_nr']

         

    # priemerne zostatky na zaktivovanych sporiacich uctoch uctoch

    df['avg_zostatok_only_activated'] = df['zostatok']/df['existing_and_activated_accounts_nr']

   

    # existujuce ucty - ako % z celkoveho poctu klientov (resp. BU)

    df['perc_existing_accounts_nr'] = df['existing_accounts_nr']/df['70_existing_accounts_nr']

   

    # zostatky - ako % z celkovych zostatkov

    df['perc_zostatok'] = df['zostatok']/df['zostatok_all']

       

    # zrusene ucty - ako % zo vsetkych sysliaich uctov

    df['perc_terminated_accounts_nr'] = df['terminated_accounts_nr']/df['existing_accounts_nr']

   

    # % zaktivovanych uctov z existujucich zaktivovanych uctov

    df['perc_activated_from_existing'] = df['activated_accounts_nr']/df['existing_and_activated_accounts_nr']

   

    # % zaktivovanych a zaroven novych uctov - zo zaktivovanych uctov

    df['perc_activated_and_new_accounts_nr'] = df['activated_and_new_accounts_nr']/df['activated_accounts_nr']

   

    # % zaktivnenych uctov zo vsetkych uctov

    df['perc_existing_and_activated_accounts_nr'] = df['existing_and_activated_accounts_nr']/df['existing_accounts_nr']

   

    # predpoklad v aktualnej periode (okrem dennej) - eistujuce ucty, nove ucty, zostatky

    df['assumption_existing_accounts_nr'] = np.nan

    df['assumption_new_accounts_nr'] = np.nan

    df['assumption_zostatok'] = np.nan

   

    if period != 'D':

        last_date_period_end = last_date.to_period(period).end_time.normalize()

        if period == 'W':

            last_date_period_end_1 = last_date_period_end - pd.DateOffset(weeks = 1)

        elif period == 'M':

            last_date_period_end_1 = (last_date_period_end - pd.DateOffset(months = 1)).to_period(period).end_time.normalize()

        elif period == 'Q':

            last_date_period_end_1 = last_date_period_end - pd.DateOffset(months = 3)

        elif period == 'Y':

            last_date_period_end_1 = last_date_period_end - pd.DateOffset(years = 1)

       

        try:

            # predpoklad - nove ucty

            x1 = df.loc[df.index.get_level_values('date') == last_date_period_end,

                   'new_accounts_nr']

            df.loc[df.index.get_level_values('date') == last_date_period_end,

                   'assumption_new_accounts_nr'] = calculate_assumption(last_date, period, x1)

           

            # predpoklad - existujuce ucty

            df.loc[df.index.get_level_values('date') == last_date_period_end,

                   'assumption_existing_accounts_nr'] = df['existing_accounts_nr'] - df['new_accounts_nr'] + df['assumption_new_accounts_nr']

       

            # predpoklad - zostatky - ratane cez prirastok zostatkov

            x3_1 = df.loc[df.index.get_level_values('date') == last_date_period_end, 'zostatok']

       

            x3_2 = df.loc[df.index.get_level_values('date') == last_date_period_end_1, 'zostatok']

           

            x3_2.index = [(last_date_period_end, i[1]) for i in x3_2.index]

            x3 = x3_1 - x3_2

           

            df.loc[df.index.get_level_values('date') == last_date_period_end,

                   'assumption_zostatok'] = df['zostatok'] - x3 + calculate_assumption(last_date, period, x3)

        except:

            df.loc[df.index.get_level_values('date') == last_date_period_end, 'assumption_zostatok'] = np.nan

            df.loc[df.index.get_level_values('date') == last_date_period_end, 'assumption_new_accounts_nr'] = np.nan

            df.loc[df.index.get_level_values('date') == last_date_period_end, 'assumption_existing_accounts_nr'] = np.nan

   

    return df

                  

 

def tab4_1_chart1(df):

    x = df.index.get_level_values('date')

   

    trace1 = Scatter(x = x, y = df['existing_accounts_nr'],name = 'Existujuce SyU')

    trace1_1 = Scatter(x = x, y = df['perc_existing_accounts_nr'], name = 'Existujuce SyU %', yaxis = 'y2')

    trace1_2 = Scatter(x = x, y = df['clients_with_1up_71active'], name = 'Zaktivnene SyU', visible = 'legendonly')

    trace2 = Scatter(x = x, y = df['assumption_existing_accounts_nr'].round(0), marker = dict(size = 10, color = '#B8001A'), mode = 'markers', name = 'Predpoklad')

    trace3 = Scatter(x = x, y = df['perc_existing_and_activated_accounts_nr'], name = 'Zaktivnene SyU %', yaxis = 'y2', visible = 'legendonly')

   

    data = [trace1, trace1_1, trace2, trace1_2, trace3]

   

    layout = dict(title = 'Existujuce ucty',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]'),

                       yaxis2 = dict(title = '%', side = 'right', overlaying = 'y', rangemode = 'tozero',

                                     tickformat = ',.0%', hoverformat = ',.2%'),

                    legend = dict(x = 1.08))

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab4_1_chart2(df):

    x = df.index.get_level_values('date')

   

    trace1 = Scatter(x = x, y = df['new_accounts_nr'],name = 'Nove ucty')

    trace2 = Scatter(x = x, y = df['assumption_new_accounts_nr'].round(0), marker = dict(size = 10, color = '#B8001A'), mode = 'markers', name = 'Predpoklad')

   

    data = [trace1, trace2]

   

    layout = dict(title = 'Nove ucty',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]'),

                       yaxis2 = dict(title = '%', side = 'right', overlaying = 'y', rangemode = 'tozero',

                                     tickformat = ',.0%', hoverformat = ',.2%'))

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab4_1_chart3(df):

    x = df.index.get_level_values('date')

   

    trace1 = Scatter(x = x, y = df['zostatok'],name = 'Zostatky')

    trace1_1 = Scatter(x = x, y = df['perc_zostatok'], name = 'Zostatky %', yaxis = 'y2')

    trace2 = Scatter(x = x, y = df['assumption_zostatok'].round(0), marker = dict(size = 10, color = '#B8001A'), mode = 'markers', name = 'Predpoklad')

   

    data = [trace1, trace1_1, trace2]

   

    layout = dict(title = 'Zostatky',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = '[EUR]', hoverformat = ',.0f'),

                       yaxis2 = dict(title = '%', side = 'right', overlaying = 'y', rangemode = 'tozero',

                                     tickformat = ',.0%', hoverformat = ',.2%'),

                    legend = dict(x = 1.08))

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab4_1_chart4(df):

    x = df.index.get_level_values('date')

   

    trace1 = Scatter(x = x, y = df['avg_zostatok'],name = 'Vsetky SyU')

    trace2 = Scatter(x = x, y = df['avg_zostatok_only_activated'], name = 'Zaktivnene')

    data = [trace1, trace2]

   

    layout = dict(title = 'Priemerne zostatky',

                       xaxis = dict(title = 'Datum', hoverformat = ',.0f'),

                       yaxis = dict(title = '[EUR]', tickformat = ',.0f', hoverformat = ',.0f')

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab4_1_chart5(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['activated_accounts_nr'],name = 'Zaktivnene')

    trace1 = Scatter(x = x, y = df['perc_activated_from_existing'], name = 'Zaktivnene % z existujucich', yaxis = 'y2')

    trace2 = Scatter(x = x, y = df['activated_and_new_accounts_nr'],name = 'Nove', visible = False)

    trace3 = Scatter(x = x, y = df['perc_activated_and_new_accounts_nr'], name = 'Nove % zo zaktivnenych', yaxis = 'y2', visible = False)

 

    data = [trace0, trace1, trace2, trace3]

   

    updatemenus = list([

            dict(type = 'buttons',

                 active = -1,

                 direction="right",

                x=0.01, y = 1.23,

                xanchor="left",

                yanchor="top",

                 buttons = list([

                         dict(label = 'Zaktivnene',

                              method = 'update',

                              args = [dict(visible = [True, True, False, False])]),

                        dict(label = 'Nove',

                             method = 'update',

                             args = [dict(visible = [False, False, True, True])])]))])

   

    layout = dict(title = 'Zaktivnene ucty',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]', rangemode = 'tozero'),

                       updatemenus = updatemenus,

                       yaxis2 = dict(title = '%', side = 'right', overlaying = 'y', rangemode = 'tozero',

                                     tickformat = ',.0%', hoverformat = ',.2%'),

                    legend = dict(x = 1.08)

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab4_1_chart6(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['terminated_accounts_nr'],name = 'Zrusene')

    trace1 = Scatter(x = x, y = df['activated_and_terminated_accounts_nr'], name = 'Zaktivnene a zrusene', visible = 'legendonly')

    trace2 = Scatter(x = x, y = df['perc_terminated_accounts_nr'], name = 'Zrusene %', yaxis = 'y2')

    data = [trace0, trace1, trace2]

   

    layout = dict(title = 'Zrusene ucty',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]', rangemode = 'tozero'),

                       yaxis2 = dict(title = '%', side = 'right', overlaying = 'y', rangemode = 'tozero',

                                     tickformat = ',.2%', hoverformat = ',.2%'),

                    legend = dict(x = 1.08)

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

##################################################### tab4_2 SYSLENIA - SPECIFICKE METRIKY ################################

   

@app.callback(Output('content4_2', 'children'),

              [Input('tabs', 'value'),

               Input('tabs_syslenie', 'value'),

               Input('dropdown_period', 'value'),

               Input('datepicker_range', 'start_date'),

               Input('datepicker_range', 'end_date')])

def content4_2_children(tab_level1, tab_level2, period, start, end):

    if tab_level1 == 'tab4' and tab_level2 == 'tab2':

       

        df = tab4_2_data(period, start, end)

 

       

        return html.Div([

                    html.Div([

                        html.Div(id = 'tab4_2_chart1_div', children = [dcc.Graph(id = 'tab4_2_chart1', figure = tab4_2_chart1(df))], className = 'six columns'),

                        html.Div(id = 'tab4_2_chart2_div', children = [dcc.Graph(id = 'tab4_2_chart2', figure = tab4_2_chart2(df))], className = 'six columns')

                           

                    ], className = 'row'),

   

                    html.Div([

                        html.Div(id = 'tab4_2_chart3_div', children = [dcc.Graph(id = 'tab4_2_chart3', figure = tab4_2_chart3(df))], className = 'six columns'),

                        html.Div(id = 'tab4_2_chart4_div', children = [dcc.Graph(id = 'tab4_2_chart4', figure = tab4_2_chart4(df))], className = 'six columns')

                            

                    ], className = 'row'),

   

                    html.Div([

                        html.Div(id = 'tab4_2_chart5_div', children = [dcc.Graph(id = 'tab4_2_chart5', figure = tab4_2_chart5(df))], className = 'six columns'),

                        html.Div(id = 'tab4_2_chart6_div', children = [dcc.Graph(id = 'tab4_2_chart6', figure = tab4_2_chart6(df))], className = 'six columns')

                           

                    ], className = 'row'),

   

                    html.Div([

                        html.Div(id = 'tab4_2_chart7_div', children = [dcc.Graph(id = 'tab4_2_chart7', figure = tab4_2_chart7(df))], className = 'six columns'),

                        html.Div(id = 'tab4_2_chart8_div', children = [dcc.Graph(id = 'tab4_2_chart8', figure = None)], className = 'six columns')

                           

                    ], className = 'row')

                   

                

        ])

 

def tab4_2_data(period, start, end):

   

    metrics = ['clients_with_1up_71active',

              '71paid_interest_sysleni_count', '71paid_interest_sum',

              '71_1eur_accounts_count', '71_5eur_accounts_count',

              '71_10eur_accounts_count', '71_bezcentovy_accounts_count',

              'existing_accounts_nr',

              '71_10eur_zaktiv_accounts_count', '71_1eur_zaktiv_accounts_count',

              '71_5eur_zaktiv_accounts_count', '71_bezcentovy_zaktiv_accounts_count',

              'activated_accounts_nr', '70to71_trans_count', '70to71_trans_sum',

              '70to71_spu_count',

              '1500more_all_syu_count', '1500more_trans_count', '1500more_trans_sum', '1500more_ucet_count',

              'less1500_all_syu_count', 'less1500_trans_count', 'less1500_trans_sum', 'less1500_ucet_count'                   ]

   

    start = pd.to_datetime(start).normalize()

    end = pd.to_datetime(end).to_period(period).end_time.normalize()

   

    df = read_df(period)

    df = df.loc[(df.index.get_level_values('date') >= start) &

                (df.index.get_level_values('date') <= end),metrics]

    df = df.loc[df.index.get_level_values('id_typuct') == 71,:]

   

    # calculate new metrics

   

    # pocet sysliacich uctov bez pravidla

   

    df['71_without_rule_accounts_count'] = df['existing_accounts_nr'] - df['71_1eur_accounts_count'] - \

        df['71_5eur_accounts_count'] - df['71_10eur_accounts_count'] - df['71_bezcentovy_accounts_count']

       

    # % z celkoveho poctu sysliacich uctov - podla pravidiel

    df['perc_1eur_accounts_count'] =  df['71_1eur_accounts_count']/df['existing_accounts_nr']

    df['perc_5eur_accounts_count'] = df['71_5eur_accounts_count']/df['existing_accounts_nr']

    df['perc_10eur_accounts_count'] = df['71_10eur_accounts_count']/df['existing_accounts_nr']

    df['perc_bezcentovy_accounts_count'] = df['71_bezcentovy_accounts_count']/df['existing_accounts_nr']

    df['perc_without_rule_accounts_count'] = df['71_without_rule_accounts_count']/df['existing_accounts_nr']

   

    # vyplatene uroky - % sysliacich uctov a priemer vyplatenych urokov na SyU (priemer tych co im boli uroky vyplatene)

    df['perc_71paid_interest_sysleni_count'] = df['71paid_interest_sysleni_count']/df['existing_accounts_nr']

    df['avg_71paid_interest_sum'] = df['71paid_interest_sum']/df['71paid_interest_sysleni_count']

    df['avg_71paid_interest_sum_allspu'] = df['71paid_interest_sum']/df['existing_accounts_nr']

   

    # pocet zaktivnenych sysliacich uctov bez pravidla

    df['71_without_rule_zaktiv_accounts_count'] = df['activated_accounts_nr'] - df['71_1eur_zaktiv_accounts_count'] - \

        df['71_5eur_zaktiv_accounts_count'] - df['71_10eur_zaktiv_accounts_count'] - df['71_bezcentovy_zaktiv_accounts_count']

   

    # % zaktivnenych uctov podla pravidla zo vsetkych zaktivnenych uctov

    df['perc_1eur_zaktiv_accounts_count'] =  df['71_1eur_zaktiv_accounts_count']/df['activated_accounts_nr']

    df['perc_5eur_zaktiv_accounts_count'] = df['71_5eur_zaktiv_accounts_count']/df['activated_accounts_nr']

    df['perc_10eur_zaktiv_accounts_count'] = df['71_10eur_zaktiv_accounts_count']/df['activated_accounts_nr']

    df['perc_bezcentovy_zaktiv_accounts_count'] = df['71_bezcentovy_zaktiv_accounts_count']/df['activated_accounts_nr']

    df['perc_without_rule_zaktiv_accounts_count'] = df['71_without_rule_zaktiv_accounts_count']/df['activated_accounts_nr']

   

    # transakcie na syslace ucty - priemerny pocet a priemerna suma na sysliaci ucet

   

    df['avg_70to71_trans_count'] = df['70to71_trans_count']/df['70to71_spu_count']

    df['avg_70to71_trans_sum'] = df['70to71_trans_sum']/df['70to71_spu_count']

   

    # vybery zo sysleni - celk. pocet transakcii, suma transakcii, a pocet uctov (v input datasete je to rozdelene podla hranice zostatku 1500)

   

    df['71_withdraw_trans_count'] = df['1500more_trans_count'] + df['less1500_trans_count']

    df['71_withdraw_trans_sum'] = df['1500more_trans_sum'] + df['less1500_trans_sum']

    df['71_withdraw_ucet_count'] = df['1500more_ucet_count'] + df['less1500_ucet_count']

   

    # vybery zo sysleni - celkovy priemer poctu transakcii, sumy transakcii, a podla < 1500, > 1500

    

    df['avg_71_withdraw_trans_count'] = df['71_withdraw_trans_count']/(df['1500more_ucet_count'] +df['less1500_ucet_count'])

    df['avg_71_withdraw_trans_sum'] = df['71_withdraw_trans_sum']/(df['1500more_ucet_count'] +df['less1500_ucet_count'])

   

    df['avg_1500more_trans_count'] = df['1500more_trans_count']/df['1500more_ucet_count']

    df['avg_1500more_trans_sum'] = df['1500more_trans_sum']/df['1500more_ucet_count']

   

    df['avg_less1500_trans_count'] = df['less1500_trans_count']/df['less1500_ucet_count']

    df['avg_less1500_trans_sum'] = df['less1500_trans_sum']/df['less1500_ucet_count']

   

    # % uctov ktore urobili vybery zo vsetkych sysliacich uctov, z < 1500, > 1500

   

    df['perc_71_withdraw_ucet_count'] = df['71_withdraw_ucet_count']/df['existing_accounts_nr']

    df['perc_1500more_ucet_count'] = df['1500more_ucet_count']/df['1500more_all_syu_count']

    df['perc_less1500_ucet_count'] = df['less1500_ucet_count']/df['less1500_all_syu_count']

   

    df = df.fillna(0)

   

    return df

 

 

def tab4_2_chart1(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['71_1eur_accounts_count'],name = '1 EUR')

    trace1 = Scatter(x = x, y = df['71_5eur_accounts_count'],name = '5 EUR')

    trace2 = Scatter(x = x, y = df['71_10eur_accounts_count'],name = '10 EUR')

    trace3 = Scatter(x = x, y = df['71_bezcentovy_accounts_count'],name = 'Bezcentovy ucet')

    trace4 = Scatter(x = x, y = df['71_without_rule_accounts_count'], name = 'Bez pravidla')

    trace0_1 = Scatter(x = x, y = df['perc_1eur_accounts_count'],name = '1 EUR %', visible = False, yaxis = 'y2')

    trace1_1 = Scatter(x = x, y = df['perc_5eur_accounts_count'],name = '5 EUR %', visible = False, yaxis = 'y2')

    trace2_1 = Scatter(x = x, y = df['perc_10eur_accounts_count'],name = '10 EUR %', visible = False, yaxis = 'y2')

    trace3_1 = Scatter(x = x, y = df['perc_bezcentovy_accounts_count'],name = 'Bezcentovy ucet %', visible = False, yaxis = 'y2')

    trace4_1 = Scatter(x = x, y = df['perc_without_rule_accounts_count'], name = 'Bez pravidla %', visible = False, yaxis = 'y2')

   

    data = [trace0, trace1, trace2, trace3, trace4, trace0_1, trace1_1, trace2_1, trace3_1, trace4_1]

   

    updatemenus = list([

            dict(type = 'buttons',

                 active = -1,

                 direction="right",

                x=0.01, y = 1.23,

                xanchor="left",

                yanchor="top",

                 buttons = list([

                         dict(label = 'Pocty',

                              method = 'update',

                              args = [dict(visible = [True, True, True, True, True, False, False, False, False, False])]),

                        dict(label = 'Percenta',

                             method = 'update',

                             args = [dict(visible = [False, False, False, False, False, True, True, True, True, True])])]))])   

    

    layout = dict(title = 'Existujuce ucty - podla pravidiel',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]', rangemode = 'tozero'),

                       yaxis2 = dict(title = '%', side = 'right', overlaying = 'y', rangemode = 'tozero',

                                     tickformat = ',.0%', hoverformat = ',.2%', range = [0, 0.5]),

                    updatemenus = updatemenus,

                    legend = dict(x = 1.08)

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab4_2_chart2(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['71_1eur_zaktiv_accounts_count'],name = '1 EUR')

    trace1 = Scatter(x = x, y = df['71_5eur_zaktiv_accounts_count'],name = '5 EUR')

    trace2 = Scatter(x = x, y = df['71_10eur_zaktiv_accounts_count'],name = '10 EUR')

    trace3 = Scatter(x = x, y = df['71_bezcentovy_zaktiv_accounts_count'],name = 'Bezcentovy ucet')

    trace4 = Scatter(x = x, y = df['71_without_rule_zaktiv_accounts_count'], name = 'Bez pravidla')

    trace0_1 = Scatter(x = x, y = df['perc_1eur_zaktiv_accounts_count'],name = '1 EUR %', visible = False, yaxis = 'y2')

   trace1_1 = Scatter(x = x, y = df['perc_5eur_zaktiv_accounts_count'],name = '5 EUR %', visible = False, yaxis = 'y2')

    trace2_1 = Scatter(x = x, y = df['perc_10eur_zaktiv_accounts_count'],name = '10 EUR %', visible = False, yaxis = 'y2')

    trace3_1 = Scatter(x = x, y = df['perc_bezcentovy_zaktiv_accounts_count'],name = 'Bezcentovy ucet %', visible = False, yaxis = 'y2')

    trace4_1 = Scatter(x = x, y = df['perc_without_rule_zaktiv_accounts_count'], name = 'Bez pravidla %', visible = False, yaxis = 'y2')

   

    data = [trace0, trace1, trace2, trace3, trace4, trace0_1, trace1_1, trace2_1, trace3_1, trace4_1]

   

    updatemenus = list([

            dict(type = 'buttons',

                 active = -1,

                 direction="right",

                x=0.01, y = 1.23,

                xanchor="left",

                yanchor="top",

                 buttons = list([

                         dict(label = 'Pocty',

                              method = 'update',

                              args = [dict(visible = [True, True, True, True, True, False, False, False, False, False])]),

                        dict(label = 'Percenta',

                             method = 'update',

                             args = [dict(visible = [False, False, False, False, False, True, True, True, True, True])])]))])   

    

    layout = dict(title = 'Zaktivnene ucty - podla pravidiel',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]', rangemode = 'tozero'),

                       yaxis2 = dict(title = '%', side = 'right', overlaying = 'y', rangemode = 'tozero',

                                     tickformat = ',.0%', hoverformat = ',.2%'),

                    updatemenus = updatemenus,

                    legend = dict(x = 1.08)

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab4_2_chart3(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['71paid_interest_sum'],name = 'Suma')

    trace1 = Scatter(x = x, y = df['avg_71paid_interest_sum'], name = 'Vyplatene SpU', visible = False)

    trace2 = Scatter(x = x, y = df['avg_71paid_interest_sum_allspu'], name = 'Vsetky SpU', visible = False)

   

    data = [trace0, trace1, trace2]

   

    updatemenus = list([

            dict(type = 'buttons',

                 active = -1,

                 direction="right",

                x=0.01, y = 1.23,

                xanchor="left",

                yanchor="top",

                 buttons = list([

                         dict(label = 'Celkovo',

                              method = 'update',

                              args = [dict(visible = [True, False ,False])]),

                        dict(label = 'Priemery',

                             method = 'update',

                             args = [dict(visible = [False, True, True])])]))])

   

    layout = dict(title = 'Vyplatene uroky z SyU - Suma',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Suma [EUR]', rangemode = 'tozero', hoverformat = ',.2f'),

                       updatemenus = updatemenus

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab4_2_chart4(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['71paid_interest_sysleni_count'],name = 'Pocet SyU')

    trace1 = Scatter(x = x, y = df['perc_71paid_interest_sysleni_count'], name = 'Pocet SyU %', yaxis = 'y2')

   

    data = [trace0, trace1]

   

    layout = dict(title = 'Vyplatene uroky z SyU - Ucty',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]', rangemode = 'tozero'),

                       yaxis2 = dict(title = '%', side = 'right', overlaying = 'y', rangemode = 'tozero',

                                     tickformat = ',.0%', hoverformat = ',.2%'),

                    legend = dict(x = 1.08)

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab4_2_chart5(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['70to71_trans_count'],name = 'Pocet transakcii', visible = 'legendonly')

    trace0_1 = Scatter(x = x, y = df['70to71_spu_count'],name = 'Pocet SyU')

    trace1 = Scatter(x = x, y = df['70to71_trans_sum'], name = 'Suma', yaxis = 'y2')

    trace2 = Scatter(x = x, y = df['avg_70to71_trans_count'].round(2), name = 'Priemerny pocet', visible = False)

    trace3 = Scatter(x = x, y = df['avg_70to71_trans_sum'].round(2), name = 'Priemerna suma', visible = False, yaxis = 'y2')

 

   

    data = [trace0, trace0_1, trace1, trace2, trace3]

   

    updatemenus = list([

            dict(type = 'buttons',

                 active = -1,

                 direction="right",

                x=0.01, y = 1.23,

                xanchor="left",

                yanchor="top",

                 buttons = list([

                         dict(label = 'Celkovo',

                              method = 'update',

                              args = [dict(visible = ['legendonly', True, True, False, False])]),

                        dict(label = 'Priemery',

                             method = 'update',

                             args = [dict(visible = [False, False, False, True, True])])]))])

   

    layout = dict(title = 'Prichadzajuce transakcie na SyU',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]', rangemode = 'tozero'),

                       yaxis2 = dict(title = 'Suma [EUR]', side = 'right', overlaying = 'y', rangemode = 'tozero', hoverformat = ',.2f'),

                       updatemenus = updatemenus,

                    legend = dict(x = 1.08)

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab4_2_chart6(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['71_withdraw_trans_count'],name = 'Pocet transakcii', visible = 'legendonly')

    trace1 = Scatter(x = x, y = df['71_withdraw_trans_sum'],name = 'Suma transakcii', yaxis = 'y2')

    trace2 = Scatter(x = x, y = df['71_withdraw_ucet_count'], name = 'Pocet uctov')

    trace3 = Scatter(x = x, y = df['avg_71_withdraw_trans_count'],name = 'Priemer poctu transakcii', visible = False)

    trace4 = Scatter(x = x, y = df['avg_71_withdraw_trans_sum'],name = 'Priemer sumy transakcii', yaxis = 'y2', visible = False)   

    

    data = [trace0, trace1, trace2, trace3, trace4]

   

    updatemenus = list([

            dict(type = 'buttons',

                 active = -1,

                 direction="right",

                x=0.01, y = 1.23,

                xanchor="left",

                yanchor="top",

                 buttons = list([

                         dict(label = 'Celkovo',

                              method = 'update',

                              args = [dict(visible = ['legendonly', True, True, False, False])]),

                        dict(label = 'Priemer',

                             method = 'update',

                             args = [dict(visible = [False, False, False, True, True])])]))])

   

    layout = dict(title = 'Vybery zo SyU',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]', rangemode = 'tozero'),

                       yaxis2 = dict(title = 'Suma [EUR]', side = 'right', overlaying = 'y', rangemode = 'tozero', hoverformat = ',.1f'),

                       updatemenus = updatemenus,

                    legend = dict(x = 1.08)

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab4_2_chart7(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['perc_71_withdraw_ucet_count'], name = 'Zo vsetkych SyU')

   

    data = [trace0]

   

    

    layout = dict(title = 'Vybery zo SyU - % uctov',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = '%', tickformat = ',.0%', hoverformat = ',.2%')

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

##################################################### tab5 AKTIVITA  #############################################

   

@app.callback(Output('content5', 'children'),

              [Input('tabs', 'value'),

               Input('dropdown_period', 'value'),

               Input('datepicker_range', 'start_date'),

               Input('datepicker_range', 'end_date'),

               Input('slider_logins', 'value'),

               Input('slider_trans', 'value')])

def content5_children(tab_level1, period, start, end, logins, trans):

    if tab_level1 == 'tab5':

        df = tab5_data(period, start, end, logins, trans)       

        return html.Div([

                    html.Div([

                        html.Div(id = 'tab5_chart1_div', children = [dcc.Graph(id = 'tab5_chart1', figure = tab5_chart1(df))], className = 'eight columns'),

                        html.Div(id = 'tab5_chart2_div', children = [dcc.Graph(id = 'tab5_chart2', figure = None)], className = 'four columns')

                           

                    ], className = 'row')

                   

                

        ])

 

def tab5_data(period, start, end, logins, trans):

    # logins dataset

    start = pd.to_datetime(start).normalize()

    end = pd.to_datetime(end).to_period(period).end_time.normalize()

   

    df = read_logins(period)

    df = df.loc[(df.index >= start) &

                (df.index <= end),:]

    df = df.loc[(df['logins_count'] >= logins) & (df['odch_trans_sum'] >= trans), :]

   

    df = df.groupby(df.index).agg({'id_klient':'count'}).rename(columns = {'id_klient':'active_clients_count'})

   

    # dataset with existing_accounts_nr

   

    df_oa = read_df(period)

    df_oa = df_oa.loc[(df_oa.index.get_level_values('date') >= start) &

                (df_oa.index.get_level_values('date') <= end) &

                (df_oa.index.get_level_values('id_typuct') == 70), ['existing_accounts_nr', 'new_accounts_nr']]

    df_oa.index = df_oa.index.get_level_values('date')

   

    df = df.join(df_oa)       

    

    # calculate new metrics

   

    df['existing_accounts_nr_without_zal'] = df['existing_accounts_nr'] - df['new_accounts_nr'] # od existujucich uctov odpocitane pocet novozalozenych

    df['perc_active_clients_count'] = df['active_clients_count']/df['existing_accounts_nr_without_zal']

 

   

    df = df.fillna(0)

   

    return df

 

def tab5_chart1(df):

    x = df.index

       

    trace0 = Scatter(x = x, y = df['active_clients_count'], name = 'Pocet aktivnych klientov')

    trace1 = Scatter(x = x, y = df['existing_accounts_nr_without_zal'], name = 'Pocet klientov - baza', visible = 'legendonly')

    trace2 = Scatter(x = x, y = df['perc_active_clients_count'], name = '% aktivnych klientov', yaxis = 'y2')

   

    data = [trace0, trace1, trace2]

   

    layout = dict(title = 'Aktivita klientov',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]'),

                       yaxis2 = dict(title = '%', side = 'right', overlaying = 'y', rangemode = 'tozero',

                                     tickformat = ',.0%', hoverformat = ',.2%'),

                    legend = dict(x = 1.08)

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

##################################################### tab6 PRODUKTOVY MIX  #############################################

   

@app.callback(Output('content6', 'children'),

              [Input('tabs', 'value'),

               Input('dropdown_period', 'value'),

               Input('datepicker_range', 'start_date'),

               Input('datepicker_range', 'end_date'),

               Input('radio_pmix', 'value'),

               Input('checklist_pmix', 'values')])

def content6_children(tab_level1, period, start, end, operator, product):

    if tab_level1 == 'tab6':

        df = tab6_data(period, start, end, operator, product)       

        return html.Div([

                    html.Div([

                        html.Div(id = 'tab6_chart1_div', children = [dcc.Graph(id = 'tab6_chart1', figure = tab6_chart1(df))], className = 'eight columns'),

                        html.Div(id = 'tab6_chart2_div', children = [dcc.Graph(id = 'tab6_chart2', figure = None)], className = 'four columns')

                           

                    ], className = 'row')

                   

                

        ])

       

def tab6_data(period, start, end, operator, product):

    # pmix dataset

    start = pd.to_datetime(start).normalize()

    end = pd.to_datetime(end).to_period(period).end_time.normalize()

   

    df = read_pmix(period)

    df = df.loc[(df.index >= start) &

                (df.index <= end),:]

   

    for i, p in enumerate(product):

        if i == 0:

            f = df[p] == 1

        else:

            if operator == 'and':

                f = f & df[p] == 1

            else:

                f = f | df[p] == 1

   

    # ked nie je zvoleny ziaden produkt, tak je to % klientov, ktori nemali v danej periode zaktivovany BU

    try:

       

        df = df[f]

    except:

        df = df[df['70_account'] == 0]

   

    df = df.groupby(df.index).agg({'id_klient':'count'}).rename(columns = {'id_klient':'pmix_clients_count'})

   

    # dataset with existing_accounts_nr

   

    df_oa = read_df(period)

    df_oa = df_oa.loc[(df_oa.index.get_level_values('date') >= start) &

                (df_oa.index.get_level_values('date') <= end) &

                (df_oa.index.get_level_values('id_typuct') == 70), ['existing_accounts_nr']]

    df_oa.index = df_oa.index.get_level_values('date')

   

    df = df.join(df_oa, how = 'outer')       

    

    # calculate new metrics

   

    # % odfiltrovanych klientov z celkoveho poctu klientov

    df['perc_pmix_clients_count'] = df['pmix_clients_count']/df['existing_accounts_nr']

 

   

    df = df.fillna(0)

   

    return df

 

def tab6_chart1(df):

    x = df.index

   

    trace0 = Scatter(x = x, y = df['pmix_clients_count'], name = 'Pocet klientov')

    trace1 = Scatter(x = x, y = df['existing_accounts_nr'], name = 'Pocet vsetkych klientov', visible = 'legendonly')

    trace2 = Scatter(x = x, y = df['perc_pmix_clients_count'], name = 'Pocet klientov %', yaxis = 'y2')

   

    data = [trace0, trace1, trace2]

   

    

    layout = dict(title = 'Produktovy mix klientov (zaktivnene produkty)',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet'),

                       yaxis2 = dict(title = '%', tickformat = ',.0%', hoverformat = ',.1%', side = 'right', overlaying = 'y')

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

##################################################### tab7 TRANSAKCIE  #############################################

   

@app.callback(Output('content7', 'children'),

              [Input('tabs', 'value'),

               Input('dropdown_period', 'value'),

               Input('datepicker_range', 'start_date'),

               Input('datepicker_range', 'end_date'),

               Input('dropdown_trans_ucet', 'value'),

               Input('radio_trans_vklad', 'value'),

               Input('checklist_trans', 'values')])

def content7_children(tab_level1, period, start, end, ucet, typ_trans, kat_trans):

    if tab_level1 == 'tab7':

        df, df4 = tab7_data(period, start, end, ucet, typ_trans, kat_trans)       

        return html.Div([

                    html.Div([

                        html.Div(id = 'tab7_chart1_div', children = [dcc.Graph(id = 'tab7_chart1', figure = tab7_chart1(df))], className = 'six columns'),

                        html.Div(id = 'tab7_chart2_div', children = [dcc.Graph(id = 'tab7_chart2', figure = tab7_chart2(df))], className = 'six columns')

                           

                    ], className = 'row'),

                    html.Div([

                        html.Div(id = 'tab7_chart3_div', children = [dcc.Graph(id = 'tab7_chart3', figure = tab7_chart3(df4) if len(df4) > 0 else None)], className = 'six columns'),

                        html.Div(id = 'tab7_chart4_div', children = [dcc.Graph(id = 'tab7_chart4', figure = tab7_chart4(df4) if len(df4) > 0 else None)], className = 'six columns')

                           

                    ], className = 'row')

                   

                

        ])

       

def tab7_data(period, start, end, ucet, typ_trans, kat_trans):

    # pmix dataset

    start = pd.to_datetime(start).normalize()

    end = pd.to_datetime(end).to_period(period).end_time.normalize()

   

    df = read_trans(period)

    df = df.loc[(df['date'] >= start) &

                (df['date'] <= end) &

                (df['id_typuct'] == ucet) &

                (df['pri_vklad'] == typ_trans),:]

       

    df1 = df.loc[df['kat_txn'].isin(kat_trans), ['date', 'trans_count', 'trans_sum']]\

        .groupby('date')\

        .agg({'trans_count':'sum', 'trans_sum':'sum'}) # selectnute kategorie dokopy

    df2 = df.groupby(by = 'date')\

        .agg({'trans_count':'sum', 'trans_sum':'sum'})\

        .rename(columns = {'trans_count':'all_trans_count', 'trans_sum':'all_trans_sum'}) # celkovo v ramci typu uctu a typu transakcie

 

    df4 = df.loc[df['kat_txn'].isin(kat_trans), ['date', 'kat_txn', 'trans_count', 'trans_sum']]\

        .rename(columns = {'trans_count':'Pocet transakcii', 'trans_sum':'Suma transakcii'})\

        .groupby(by = ['date', 'kat_txn'])\

        .agg({'Pocet transakcii':'sum', 'Suma transakcii':'sum'})\

        .unstack()

    df = df1.join(df2, how = 'outer')

      

    # calculate new metrics

   

    # % odfiltrovanych kategorii transakcii z zo vsetkych v ramci typu uctu a typut operacie - suma

    df['perc_trans_sum'] = df['trans_sum']/df['all_trans_sum']

    df['perc_trans_count'] = df['trans_count']/df['all_trans_count']

   

    df = df.fillna(0)

   

    return df, df4

 

def tab7_chart1(df):

    x = df.index

   

    trace0 = Scatter(x = x, y = df['trans_sum'], name = 'Suma transakcii')

    trace1 = Scatter(x = x, y = df['perc_trans_sum'], name = 'Suma transakcii %', yaxis = 'y2')

   

    data = [trace0, trace1]

   

    

    layout = dict(title = 'Suma transakcii a ich %',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Suma [EUR]', rangemode = 'tozero'),

                       yaxis2 = dict(title = '%', tickformat = ',.0%', hoverformat = ',.1%', side = 'right', overlaying = 'y',

                                     rangemode = 'tozero')

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab7_chart2(df):

    x = df.index

   

    trace0 = Scatter(x = x, y = df['trans_count'], name = 'Pocet transakcii')

    trace1 = Scatter(x = x, y = df['perc_trans_count'], name = 'Pocet transakcii %', yaxis = 'y2')

   

    data = [trace0, trace1]

   

    

    layout = dict(title = 'Pocet transakcii a ich %',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Suma [EUR]', rangemode = 'tozero'),

                       yaxis2 = dict(title = '%', tickformat = ',.0%', hoverformat = ',.1%', side = 'right', overlaying = 'y',

                                     rangemode = 'tozero')

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab7_chart3(df):

    x = df.index

    df = df['Suma transakcii']

    data = [Scatter(x = x, y = df[col], name = col) for col in df.columns]   

    

    layout = dict(title = 'Suma transakcii a ich % - jednotlivo',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Suma [EUR]', rangemode = 'tozero')

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab7_chart4(df):

    x = df.index

    df = df['Pocet transakcii']

    data = [Scatter(x = x, y = df[col], name = col) for col in df.columns]   

    

    layout = dict(title = 'Pocet transakcii a ich % - jednotlivo',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Suma [EUR]', rangemode = 'tozero')

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

##################################################### tab8_1 - JIRA - Prijate vs. uzavrete ziadosti TAB #########################################

 

@app.callback(Output('content8_1', 'children'),

              [Input('tabs', 'value'),

               Input('tabs_jira', 'value'),

               Input('dropdown_period', 'value'),

               Input('datepicker_range', 'start_date'),

               Input('datepicker_range', 'end_date')])

def content8_1_children(tab_level1, tab_level2, period, start, end):

    if tab_level1 == 'tab8' and tab_level2 == 'tab1':

       

        df = tab8_1_data(period, start, end)

 

       

        return html.Div([

                    html.Div([

                        html.Div(id = 'tab8_1_chart1_div', children = [dcc.Graph(id = 'tab8_1_chart1', figure = tab8_1_chart1(df))], className = 'six columns'),

                        html.Div(id = 'tab8_1_chart2_div', children = [dcc.Graph(id = 'tab8_1_chart2', figure = tab8_1_chart2(df))], className = 'six columns')

                           

                    ], className = 'row'),

   

                    html.Div([

                        html.Div(id = 'tab8_1_chart3_div', children = [dcc.Graph(id = 'tab8_1_chart3', figure = tab8_1_chart3(df))], className = 'six columns'),

                        html.Div(id = 'tab8_1_chart4_div', children = [dcc.Graph(id = 'tab8_1_chart4', figure = tab8_1_chart4(df))], className = 'six columns')

                           

                    ], className = 'row'),

   

                    html.Div([

                        html.Div(id = 'tab8_1_chart5_div', children = [dcc.Graph(id = 'tab8_1_chart5', figure = None)], className = 'six columns'),

                        html.Div(id = 'tab8_1_chart6_div', children = [dcc.Graph(id = 'tab8_1_chart6', figure = None)], className = 'six columns')

                           

                    ], className = 'row')

                    

                

        ])

       

def tab8_1_data(period, start, end):

    metrics = [ 'otvorene_count', 'otvorene_max', 'otvorene_min',

   'otvorene_sum', 'zavrete_count', 'zavrete_max',

   'zavrete_min', 'zavrete_sum']

   

    start = pd.to_datetime(start).normalize()

    end = pd.to_datetime(end).to_period(period).end_time.normalize()

   

    df = read_jira(period)

    df = df.loc[(df.index.get_level_values('date') >= start) &

                (df.index.get_level_values('date') <= end), metrics]

   

    

    df = df.groupby(by = [pd.Grouper(level = 0, freq = period), pd.Grouper(level = 1)])\

        .agg({'otvorene_count':'sum', 'otvorene_max':'max', 'otvorene_min':'min',

              'otvorene_sum':'sum', 'zavrete_count':'sum' ,'zavrete_max':'max',

              'zavrete_min':'min', 'zavrete_sum':'sum'

              })

           

    # calculate new metrics

   

    # priemer for otvorene a uzavrete

    df['otvorene_mean'] = df.otvorene_sum/df.otvorene_count

    df['zavrete_mean'] = df.zavrete_sum/df.zavrete_count

   

    df = df.unstack() # otvorene, uzavrete je 1st level, project je 2nd level index

   

    df['zavrete_all_count'] = df['zavrete_count'].sum(axis = 1)

    df['otvorene_all_count'] = df['otvorene_count'].sum(axis = 1)

   

    return df

 

def tab8_1_chart1(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['otvorene_count']['BO'],name = 'BO')

    trace1 = Scatter(x = x, y = df['otvorene_count']['DIGI'],name = 'DIGI')

    trace2 = Scatter(x = x, y = df['otvorene_count']['PORE'],name = 'PORE')

    trace3 = Scatter(x = x, y = df['otvorene_count']['REK'],name = 'REK')

   

    data = [trace0, trace1, trace2, trace3]

   

    layout = dict(title = 'Prijate ziadosti',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]')

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab8_1_chart2(df):

    x = df.index.get_level_values('date')

    

    trace0 = Scatter(x = x, y = df['zavrete_count']['BO'],name = 'BO')

    trace1 = Scatter(x = x, y = df['zavrete_count']['DIGI'],name = 'DIGI')

    trace2 = Scatter(x = x, y = df['zavrete_count']['PORE'],name = 'PORE')

    trace3 = Scatter(x = x, y = df['zavrete_count']['REK'],name = 'REK')

   

    data = [trace0, trace1, trace2, trace3]

   

    layout = dict(title = 'Uzavrete ziadosti',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]')

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab8_1_chart3(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['zavrete_all_count'],name = 'Zavrete')

    trace1 = Scatter(x = x, y = df['otvorene_all_count'],name = 'Otvorene')

   

    data = [trace0, trace1]

   

    layout = dict(title = 'Zavrete vs. otvorene ziadosti',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]')

           )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab8_1_chart4(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['zavrete_mean']['BO'],name = 'BO')

    trace1 = Scatter(x = x, y = df['zavrete_mean']['DIGI'],name = 'DIGI')

    trace2 = Scatter(x = x, y = df['zavrete_mean']['PORE'],name = 'PORE')

    trace3 = Scatter(x = x, y = df['zavrete_mean']['REK'],name = 'REK')

   

    data = [trace0, trace1, trace2, trace3]

   

    layout = dict(title = 'Priemerny cas uzatvorenia ziadosti',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Cas [h]')

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

##################################################### tab8_2 - JIRA - Projekty a ich DIGI proces TAB #########################################

 

@app.callback(Output('content8_2', 'children'),

              [Input('tabs', 'value'),

               Input('tabs_jira', 'value'),

               Input('dropdown_period', 'value'),

               Input('datepicker_range', 'start_date'),

               Input('datepicker_range', 'end_date')])

def content8_2_children(tab_level1, tab_level2, period, start, end):

    if tab_level1 == 'tab8' and tab_level2 == 'tab2':

        df_stats, df_counts = tab8_2_data(period, start, end)       

        

        return html.Div([

                    html.Div([

                        html.Div(id = 'tab8_2_chart1_div', children = [dcc.Graph(id = 'tab8_2_chart1', figure = tab8_2_chart1(df_stats['DIGI']))], className = 'five columns'),

                        html.Div(id = 'tab8_2_chart2_div', children = [dcc.Graph(id = 'tab8_2_chart2', figure = tab8_2_chart2(df_counts['DIGI']))], className = 'seven columns')

                           

                    ], className = 'row'),

   

                    html.Div([

                        html.Div(id = 'tab8_2_chart3_div', children = [dcc.Graph(id = 'tab8_2_chart3', figure = tab8_2_chart3(df_stats['BO']))], className = 'five columns'),

                        html.Div(id = 'tab8_2_chart4_div', children = [dcc.Graph(id = 'tab8_2_chart4', figure = tab8_2_chart4(df_counts['BO']))], className = 'seven columns')

                           

                    ], className = 'row'),

   

                    html.Div([

                        html.Div(id = 'tab8_2_chart5_div', children = [dcc.Graph(id = 'tab8_2_chart5', figure = tab8_2_chart5(df_stats['REK']))], className = 'five columns'),

                        html.Div(id = 'tab8_2_chart6_div', children = [dcc.Graph(id = 'tab8_2_chart6', figure = tab8_2_chart6(df_counts['REK']))], className = 'seven columns')

                            

                    ], className = 'row')

                   

                

        ])

   

def tab8_2_data(period, start, end):

    start = pd.to_datetime(start).normalize()

    end = pd.to_datetime(end).normalize()

           

    df = read_jira(period)

    df = df.loc[(df.index.get_level_values('date') >= start) &

                (df.index.get_level_values('date') <= end), :]

   

    df = df.groupby(by = [pd.Grouper(level = 0, freq = period), pd.Grouper(level = 1), pd.Grouper(level = 2)])\

        .agg({'zavrete_count':'sum', 'zavrete_max':'max', 'zavrete_min':'min', 'zavrete_sum':'sum'

              }) # grupovane podla date, projekt, digi_proces

   

    # calculate new metrics - count potrebujem grupovane na datum - projekt - digi proces,

    # mean (kalkulovane zo sum a count), max, min, count na datum - projekt

   

    df_counts = df.loc[:, ['zavrete_count']]

    df_stats = df.groupby(by = [pd.Grouper(level = 0), pd.Grouper(level = 1)])\

        .agg({'zavrete_count':'sum', 'zavrete_max':'max', 'zavrete_min':'min', 'zavrete_sum':'sum'})

       

    df_stats['zavrete_mean'] = df_stats.zavrete_sum/df_stats.zavrete_count

   

    df_counts = df_counts.unstack(1).unstack().droplevel(0, axis = 1) # 1st column index project, 2nd level digi_proces

    df_stats = df_stats.unstack().swaplevel(axis = 1) # 1st column index project

   

    return df_stats, df_counts

 

def tab8_2_chart1(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['zavrete_count'],name = 'Pocet')

    trace1 = Scatter(x = x, y = df['zavrete_max'],name = 'Max', yaxis = 'y2')

    trace2 = Scatter(x = x, y = df['zavrete_min'],name = 'Min', yaxis = 'y2')

    trace3 = Scatter(x = x, y = df['zavrete_mean'],name = 'Priemer', yaxis = 'y2')

   

    data = [trace0, trace1, trace2, trace3]

   

    layout = dict(title = 'DIGI',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]', rangemode = 'tozero'),

                       yaxis2 = dict(title = 'Cas [h]', overlaying = 'y', rangemode = 'tozero', side = 'right')

            )

    fig = Figure(data = data, layout = layout)

    

    return fig

 

def tab8_2_chart2(df):

    x = df.index.get_level_values('date')

       

    data = [Scatter(x = x, y = df[i], name = i) for i in df.columns]

   

    layout = dict(title = 'DIGI - digi proces',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]'),

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab8_2_chart3(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['zavrete_count'],name = 'Pocet')

    trace1 = Scatter(x = x, y = df['zavrete_max'],name = 'Max', yaxis = 'y2')

    trace2 = Scatter(x = x, y = df['zavrete_min'],name = 'Min', yaxis = 'y2')

    trace3 = Scatter(x = x, y = df['zavrete_mean'],name = 'Priemer', yaxis = 'y2')

   

    data = [trace0, trace1, trace2, trace3]

   

    layout = dict(title = 'BackOffice',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]', rangemode = 'tozero'),

                       yaxis2 = dict(title = 'Cas [h]', overlaying = 'y', rangemode = 'tozero', side = 'right')

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab8_2_chart4(df):

    x = df.index.get_level_values('date')

       

    data = [Scatter(x = x, y = df[i], name = i) for i in df.columns]

   

    layout = dict(title = 'BackOffice - digi proces',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]'),

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab8_2_chart5(df):

    x = df.index.get_level_values('date')

   

    trace0 = Scatter(x = x, y = df['zavrete_count'],name = 'Pocet')

    trace1 = Scatter(x = x, y = df['zavrete_max'],name = 'Max', yaxis = 'y2')

    trace2 = Scatter(x = x, y = df['zavrete_min'],name = 'Min', yaxis = 'y2')

    trace3 = Scatter(x = x, y = df['zavrete_mean'],name = 'Priemer', yaxis = 'y2')

   

    data = [trace0, trace1, trace2, trace3]

   

    layout = dict(title = 'Reklamacie',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]', rangemode = 'tozero'),

                       yaxis2 = dict(title = 'Cas [h]', overlaying = 'y', rangemode = 'tozero', side = 'right')

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

def tab8_2_chart6(df):

    x = df.index.get_level_values('date')

       

    data = [Scatter(x = x, y = df[i], name = i) for i in df.columns]

   

    layout = dict(title = 'Reklamacie - digi proces',

                       xaxis = dict(title = 'Datum'),

                       yaxis = dict(title = 'Pocet [ks]'),

            )

    fig = Figure(data = data, layout = layout)

   

    return fig

 

##################################################### tab9 - INFO #########################################

 

@app.callback(Output('content9', 'children'),

              [Input('tabs', 'value')])

def content9_children(tab_level1):

    if tab_level1 == 'tab9':

       

        return html.Div([dcc.Markdown(

                '### Tab 1 - Vybrane metriky\n##### Graf 1 - Existujuce ucty\n'''

                '''**Bezne ucty** - pocet existujucich (vedenych) beznych uctov na konci daneho obdobia.\n'''+

                '''Kalkulovane ako pocet novych uctov kumulativne - pocet zrusenych uctov kumulativne\n\n''' +

                '''**Sporiace ucty** - pocet existujucich (vedenych) sporiacich uctov na konci daneho obdobia.\n\n'''+

                '''**Sporiaci klienti** - pocet klientov s aspon 1 sporiacim uctom.\n\n'''+

                '''**Sysliace ucty** - pocet sysliacich uctov.\n\n'''+

                '''**Sysliace ucty %** - sysliace ucty ako % z poctu existujucich beznych uctov (klientov).\n\n'''+

                '''**Sporiace ucty %** - sporiace ucty ako % z poctu existujucich beznych uctov (klientov).\n\n'''+

                '''**Sporiaci klienti %** - klienti s aspon 1 sporiacim uctom ako % z poctu existujucich beznych uctov (klientov).\n\n'''+

                '''##### Graf 2 - Nove ucty\n\n'''

                '''**Bezne ucty** - pocet zalozenych beznych uctov v danej periode\n\n'''+

                '''**Sporiace ucty** - pocet zalozenych sporiacich uctov\n\n'''+

                '''**Sporiaci klienti** - pocet klientov, ktori si prvy krat zalozili sporiaci ucet\n\n'''+

                '''**Sysliace ucty** - pocet zalozenych sysliacich uctov\n\n'''+

                '''**Sysliace ucty %** - pocet zalozenych sysliacich uctov ako % z existujucich beznych uctov (klientov)\n\n'''+

                '''**Sporiace ucty %** - poet zalozenych sporiacich uctov ako % z existujucich beznych uctov (klientov)\n\n'''+

                '''**Sporiaci klienti %** - pocet klientov, ktori si prvy krat zalozili sporiaci ucet ako % z existujucich beznych uctov (klientov)\n\n'''+

                '''##### Graf 3 - Zostatky\n\n'''

                '''**Celkove** - celkove zostatku ku koncu periody (tj bezne ucty + sporiace ucty + sysliace ucty)\n\n'''+

                '''**Celkove - plan** - Plan celkovych zostatkov\n\n'''+

                '''**Celkove - % plnenia** - percento naplnenia planu\n\n'''+

                '''**dalsie taby v grafe** - to iste ako v tabe 'Celkove', akurat rozdelene pre bezne ucty a sporenia + syslenia\n\n'''+

                '''##### Graf 4 - Priemerne zostatky\n\n'''

                '''**Celkove** - Priemerne zostatky celkovo. Priemer je ratany ako suma celkovych zostatkov / pocet existujucich beznych uctov\n\n'''+

                '''**Celkove - plan** - planovane priemerne celkove zostatky\n\n'''+

                '''**Celkove - % plnenia** - percento plnenia planu\n\n'''

                '''**dalsie taby v grafe** - to iste ako v tabe 'Celkovo', akurat rozdelene pre bezne ucty a sporenia + syslenia. Priemer\n'''

                '''sa tiez rata z poctu existujucich beznych uctov\n\n'''+

                '''##### Graf 5 - Onboarding completion rate\n\n'''

                '''**Approved** - pocet schvalenych ziadosti\n\n'''+

                '''**Rejected** - pocet zamietnutych ziadosti\n\n''' +

                '''**OCR** - onboarding completion rate. Ratane ako pocet schvalenych ziadosti / (pocet schvalenych + pocet zamietnutych)\n\n'''+

                '''##### Graf 6 - Priemer transakcii na BU\n\n'''

                '''**Priemerny pocet a suma** - priemerny pocet a suma prichadzajucich a odchadzajucich transakcii nad beznym uctom.\n'''+

                ''' V pripade odchadzajucich sa berie do uvahy: Nakup POS-terminal, Prikaz na uhradu elektronicky, Nakup platobny terminal, \n'''+

                ''' Cash Advnce platobny terminal a prikaz na uhradu (id_operac = 209, 210, 911, 1374, 1382, 3002). V pripade prichadzajucich sa berie do uvahy: Prvy vklad bezhotovostvny, \n'''+

               ''' prijata uhrada a prijata platba (id_operac = 11, 21, 120, 3030)\n\n'''

               

        ),

        dcc.Markdown(

                '### Tab 2 - Ucty\n##### Graf 1 - Existujuce ucty\n'''

                '''**Existujuce ucty** - pocet existujucich (vedenych) beznych uctov na konci daneho obdobia.\n\n'''+

                '''**Plan** - planovany pocet vedenych beznych uctov\n\n'''+

                '''**% plnenia planu** - percento plnenia planu\n\n'''+

                '''**Predpoklad** - Predpokladany pocet existujucich beznych uctov na konci danej periody. Ratany ako\n\n'''+

                ''' [(pocet existujucich beznych uctov k dnesnemu dnu - pocet existujucich beznych uctov na konci predchadzajucej periody)/pocet ubehnutych dni sucasnej periody]*celkovy pocet dni sucasnej periody\n\n'''

                '''**Zaktivnene ucty** - pocet existujucich zaktivnenych beznych uctov na konci periody\n\n'''+

                '''**Zaktivnene ucty %** - existujuce zaktivnene ucty ako % zo vsetkych existujucich beznych uctov\n\n'''+

                '''###### Graf 2 - Nove ucty\n\n'''+

                '''**Nove ucty** - pocet beznych uctov zalozenych v danej periode\n\n'''+

                '''**Plan** - planovany pocet novych uctov\n\n'''+

                '''**% plnenia planu** - percento plnenia planu novych beznych uctov\n\n'''+

                '''**Predpoklad** - predpokladany pocet novych beznych uctov na konci periody.\n\n'''+

                '''##### Graf 3 - Zostatky\n'''+

                '''**Zostatky** - zostatky na beznych uctov ku koncu periody\n\n'''+

                '''**Plan % planu a predpoklad** - rovnaky koncept ako predoslych grafoch\n\n'''+

                '''##### Graf 4 - Priemerne zostatky\n\n'''+

                '''**Vsetky BU** - priemerny zostatok ratany len na vsetkych beznych uctoch\n\n'''+

                '''**Plan** - planovany priemerny zostatok na beznych uctoch\n\n'''+

                '''**Vsetky BU - % plnenia** - percento naplnenia planu priemerneho zostatku rataneho na vsetkych beznych uctoch\n\n'''+

                '''**tab v grafe 'Zaktivnene BU'** - rovnake ako v pripade tabu 'Vsetky BU', akurat ratane len na zaktivnenych beznych uctoch\n\n'''

                '''##### Graf 5 - Zaktivnene ucty\n\n'''+

                '''**Zaktivnene** - pocet uctov, ktore boli v danu periodu zaktivnene\n\n'''+

                '''**Zaktivnene % z existujucich** - zaktivnene ucty ako % z existujucich uctov danu periodu\n\n'''+

                '''**Nove** - pocet novych uctov, ktore boli v rovnaku periodu zaroven aj zaktivnene\n\n'''+

                '''**Nove % zo zaktivnenych** - zo zaktivnenych uctov bolo taketo % novych\n\n'''+

                '''##### Graf6 - Zrusene ucty\n\n'''+

                '''**Zrusene** - pocet zrusenych uctov\n\n'''+

                '''**Zaktivnene a zrusene** - pocet zrusenych uctov, ktore boli uz zaktivnene\n\n'''+

                '''**Zrusene %** - zrusene ucty ako % z existujucich uctov (klientov)\n\n'''

        ),

        dcc.Markdown(

                '### Tab 3_1 - Sporenia - Vseobecne metriky\n\n'''

                '''Vo vacsine grafov su koncepty rovnake ako pri beznych uctoch, avsak klient moze mat viacero sporiacich uctov, \n'''+

                '''takze vo vybranych grafoch su aj pohlady na samotneho klienta\n\n'''+

                '''##### Graf 1 - Existujuce ucty\n\n'''+

                '''**Klienti s aspon 1 SpU** - pocet klientov, ktori mali ku koncu periody aspon 1 sporiaci ucet\n\n'''+

                '''**Klienti s aspon 1 zaktiv. SpU** - pocet klientov, ktori mali ku koncu periody aspon 1 zaktivneny sporiaci ucet\n\n'''+

                '''**Klienti s aspon 1 SpU %** - klienti s aspon 1 sporiacim uctom ako % z celk. poctu klientov\n\n'''+

                '''**Klienti s aspon 1 zaktiv. SpU %** - klienti s aspon 1 zaktivnenym sporiacim uctom ako % z celk. poctu klientov\n\n'''+

                '''plus este priemerny pocet sporiacich uctov na klienta (ratane zo vsetkych existujucich klientov a z klientov co maju aspon 1 sporiaci ucet)\n\n'''+

                '''##### Graf 4 - Priemerne zostatky\n\n'''+

                '''**Vsetky SpU** - priemerne zostatky ratane na vsetkych sporiacich uctoch\n\n'''+

                '''**Zaktivnene** - priemerne zostatky ratane len na zaktivnenych sporiacich uctoch\n\n'''+

                '''**Vsetci klienti** - priemerny zostatok  ratany na vsetkych existujucich klientov\n\n'''+

                '''**Klienti s aspon 1 SpU** - priemerny zostatok ratany na klientov, ktori maju aspon 1 sporiaci ucet\n\n'''+

                '''##### Graf 5 - Zaktivnene ucty\n\n'''+

                '''**Zaktivnene** - pocet sporiacich uctov, ktore boli zaktivnene danu periodu\n\n'''+

                '''**Nove** - pocet sporiacich uctov, ktore boli v rovnaku periodu zaktivnene aj zalozene\n\n'''+

                '''**Zaktivnene % z existujucich** - zaktivnene ucty ako % zo existujucich zaktivnenych sporiacich uctov\n\n'''+

                '''**Nove % zo zaktivnenych** - Zo zaktivnenych sporiacich uctov bolo taketo % novych\n\n'''+

                '''**Zaktivneni klienti** - pocet klientov, ktori si zaktivnili aspon 1 sporiaci ucet\n\n'''+

                '''**Zaktivneni klienti % z exist.** - % zaktivnenych klientov z existujucich zaktivnenych klientov\n\n'''+

                '''##### Graf 6 - Zrusene ucty\n\n'''+

                '''rovnaky koncept ako pri beznych uctoch +\n\n'''+

                '''**Klienti s min 1 zru. SpU** - pocet klientov, co zrusili aspon 1 sporiaci ucet a ich % z celk. poctu klientov\n\n'''+

                '''**Zruseni klienti** - klienti, co v danu periodu zrusili vsetky svoje sporiace ucty\n\n'''

        ),

        dcc.Markdown(

                '### Tab 3_2 - Sporenia - Specificke metriky\n\n'''

                '''##### Graf 1 - Zrealizovane trvale prikazy z vlastneho BU na SpU - celkovo\n\n'''+

                '''Celkovy pocet a suma realizovanych trvalych prikazov z vlastneho bezneho uctu na svoj sporiaci\n\n'''+

                '''##### Graf 2 - SpU a klienti s realizovanym TP z vlastneho BU\n\n'''+

                '''**PocetSpU** - pocet sporiacich uctov na ktore sa trvale prikazy zo svojich beznych uctov realizovali\n\n'''+

                '''**PocetSpU %** - percento sporiacich uctov na ktore sa tp realizovali\n\n'''+

                '''**Pocet klientov** - pocet klientov, ktori realizovali na svoje sporiace ucty aspon 1 trvaly prikaz\n\n'''+

                '''**Pocet klientov %** - ich percento, tj z poctu klientov co maju aspon 1 sporiaci ucet (sporiaci klient)\n\n'''+

                '''##### Graf3 - Transakcie z vlastneho bezneho uctu na sporiaci\n\n'''+

                '''Obsahuje informacie o celkovom pocte a sume transakcii klientov z vlastneho bezneho uctu na sporiaci, mimo trvalych\n'''+

                ''' prikazov, a priemerne pocty a sumy tychto transakcii na sporiaci ucet a sporiaceho klienta\n\n'''+

                '''##### Graf 4 - Transakcie z ineho uctu na sporiaci ucet\n\n'''+

                '''Obsahuje tie iste info ako predosly graf, akurat sa beru do uvahy iba transakcie z inych bank, alebo \n'''+

                ''' z PABK, kde nie je ten isty majitel bezneho uctu ako sporiaceho\n\n'''+

                '''##### Graf 5 - Transakcie z ineho uctu na sporiaci ucet - banky\n\n'''+

                '''Obsahuje informaciu o pocetnostiach prichadzajucich transakcii na sporiaci ucet z inych bank, podla bank\n\n'''+

                '''##### Graf 6 - Vyplatene uroky z SpU - celkovo\n\n'''+

                '''Info o tom, kolkym sporiacim uctom a klientom bol vyplateny urok, ich pocty a celkova vyplatena suma\n\n'''+

                '''##### Graf 7 - Vyplatene uroky z SpU - priemery a %\n\n'''+

                '''Graf osahuje info o tom kolkym percentam sporiacich uctov a sporiacich klientov bol vyplateny urok, aka bola \n'''+

                '''vyplatena priemerna suma na sporiaci ucet a na sporiaceho klienta\n\n'''+

                '''##### Graf 8 - Vybery zo sporiacich uctov\n\n'''+

                '''Info o tom z kolkych sporiacich uctov bol uskutocneny vyber, kolko klientov tieto vybery uskutocnilo a celkova vybrata suma\n\n'''+

                '''##### Graf 9 - Vybery zo sporiacich uctov - priemery a %\n\n'''+

                '''V grafe je info o tom ake ja priemerne vybrata suma na sporiaci ucet a sporiaceho klienta, percentualne z kolkych sporiacich\n'''+

                ''' uctov sa vybery uskutocnili (ratane z celkoveho poctu sporiacich uctov) a percento klientov  (ratane z poctu sporiacich klientov)\n\n'''

               

        ),

        dcc.Markdown(

                '''### Tab 4_1 - Syslenia - Vseobecne metriky\n\n'''

                '''Rovnaky koncept ako pri beznych uctoch a sporeniach\n\n'''

       

        ),

        dcc.Markdown(

                '''### Tab 4_2 - Syslenia - Specificke metriky\n\n'''+

                '''##### Graf 1 - Existujuce ucty - podla pravidiel\n\n'''+

                ''' Info o pocte existujucich sysliacich uctov, podla typov pravidiel, a ich percentualny podiel.\n'''+

                ''' Berie sa do uvahy posledne pravidlo a je priradene sysliacemu uctu od jeho zalozenia, tj. zmeny pravidla sa neberu do uvahy\n\n'''+

                '''##### Graf 2 - Zaktivnene ucty - podla pravidiel\n\n'''+

                '''Pocty zaktivnenych sysliacich uctov podla typov pravidiel, a ich percentualny podiel\n\n'''+

                '''##### Graf 3 - Vyplatene uroky zo sysliacich uctov - suma\n\n'''+

                '''Info o celkovej sume vyplatenych urokov na sysliacich uctoch, a jej priemer (ratany z uctov, ktorym boli urok vyplateny, ale\n'''+

                ''' aj na vsetky sysliace ucty)\n\n'''+

                '''##### Graf 4 - Vyplatene uroky zo sysliacich uctov\n\n'''+

                '''Kolkym sysliacim uctom boli vyplatene uroky a percentualne z celkoveho poctu sysliacich uctov\n\n'''+

                '''##### Graf 5 - Prichadzajuce transakcie na sysliace ucty\n\n'''+

                '''Celkovy pocet a suma prichadzajucich transakcii na sysliace ucty, pocet sysliacich uctov, na ktore prisli\n'''+

                ''' a ich priemerny pocet a suma (ratane na uctoch ktorych sa tykali)\n\n'''+

                ''' ##### Graf 6 - Vybery zo sysliacich uctov a Graf 7 - Vybery zo sisliacich uctov - % uctov\n\n'''+

                '''Graf obsahuje info o vyberoch zo sysleni, ich celkovom pocte, sume, poctu uctov, z ktorych bol uskutocneny vyber, \n'''+

                ''' priemernom pocte a sume tychto transakcii (ratane na uctoch, ktorych sa tykali), a kolko % sysliacich uctov uskutocnilo vyber\n\n'''

               

        ),

        dcc.Markdown(

                '''### Tab 5 - Aktivita\n\n'''+

                '''Pocet aktivnych klientov sa pocita na zaklade odfiltrovaneh min. poctu loginov a min. sumy odchadzajucich transakcii\n'''+

                '''pricom ich % sa pocita ako ich podiel z bazy, pricom od bazy (pocet existujucich klientov) je odpocitany pocet novozalozenych uctov\n\n'''

        ),

        dcc.Markdown(

                '''### Tab 6 - Produktovy mix\n\n'''+

                '''Graf zobrazuje pocet klientov, ktory maju zvolenene produkty (operator AND - klient musi mat vsetky zvolene produkty, \n'''+

                ''' operator OR - klient musi mat aspon jeden zo zvolenych produktov). V pripade, ze nie je zvoleny ziadny produkt, \n'''+

                ''' zobrazia sa klienti, co maju ku konci periody nezaktivneny bezny ucet. Ich percento sa rata zo vsetkych existujucich klientov\n\n'''

                

        ),

        dcc.Markdown(

                '''### Tab 6 - Transakcie\n\n'''+

                '''Podla odlfiltrovaneho typu uctu, typu transakcie a kategorie transakcie (moze byt zvolenych viacero),\n'''+

                ''' sa v hornych dvoch grafoch zobrasi celkova suma a pocet transakcii vo zvolenych kategoriach dohromady, a ich podiel z\n'''+

                ''' v ramci vsetkych kategorii, zvoleneho typu transakcie a typu uctu. V dolnych 2 grafoch sa pocty a sumy transakcii \n'''+

                ''' zobrazuju jednotlivo pre kazdu zvolenu kategoriu'''

        )

    ])

               

 

 

if __name__ == '__main__':

    app.run_server(debug = True, host = '0.0.0.0', port = 8051)


 
