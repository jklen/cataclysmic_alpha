import click
import subprocess
import yaml
import sys
from utils_select_symbols import *
from utils_strategy import *
from datetime import datetime
from time import ctime
import pdb
import logging
import logging.config
import json

with open('../select_symbols_logging_config.json', 'r') as config_file:
    config_dict = json.load(config_file)

logging.config.dictConfig(config_dict)
logger = logging.getLogger(__name__)
logger.info("Logging is set up.")

@click.command() 
@click.option("-c", "--path_config", help="Path to config yml to use")
def main(path_config):
    config = yaml.safe_load(open(path_config, 'r'))
    
    # to ze zvolim symboly, ktore medzi sebou najmenej koreluju, znamena to ze daily returns jednej strategie medzi tymito symbolmi tiez nebude korelovat?
    
    # output scriptu bude:
    #  ciel je dostat list symbolov, ktore:
    #     - medzi sebou nekoreluju (korelacia samotnej hodnoty, alebo daily returns?)
    #     - maju urcitu celkovu std
    #     - maju urcitu klzavu std (tj chcem aby v cenach bola urcita variabilita neustale)
    #     - maju urcitu periodu
    #     - ich perioda sa urcity pocet dni prelina
    # dalsie parametre:
    #   - specificke symboly (tj zvolim ja manualne)
    #   - symboly, ktore chcem excludnut (napr. lebo uz mam pre nejake symboly zbehnute strategie)
    #   - sample %, resp. pocet symbolov co chcem samplovat zo vsetkych v alpace - 0.1, resp 50
    #   - diverzifikovat podla odvetvia - true/false
    #   - finalny pocet symbolov vo vystupe
    # vystup bude df/csv so symbolmi, statistikami a korelaciami. Symboly z toho fajlu pojdu ako vstup do run_strategy.py