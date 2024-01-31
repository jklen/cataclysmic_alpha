import click
import subprocess
import yaml
import sys
from utils import HigherHighStrategy, data_load
from datetime import datetime
from time import ctime
import pdb

@click.command() 
@click.option("-c", "--path_config", help="Path to config yml to use")
def main(path_config):
    config = yaml.safe_load(open(path_config, 'r'))
    for symbol in config['symbols']:
        
        # data load
        
        print(f"{ctime()} - {symbol}")
        df = data_load(symbol,
                       config['data_preference'],
                       datetime(2000, 1, 1), 
                       datetime(2024, 1, 25))
    # git
    # logging
    # data stats (grafy csv s grafmi a statistikami)
    #   close price plot + volume
    #   daily returns stats
    #   nr of days in period, min max
    # data rolling split
    # portfolio stats
    # eval
    #   read & filter stats df
    #   clustering eval
    #   final clustering
    
    
    
if __name__ == '__main__':
    main()