import click
import yaml
from calpha.utils_strategy import data_load, data_stats
from datetime import datetime
from time import ctime
import logging
import logging.config
import json

with open('select_symbols_logging_config.json', 'r') as config_file:
    config_dict = json.load(config_file)

logging.config.dictConfig(config_dict)
logger = logging.getLogger(__name__)
logger.info("Logging is set up.")

@click.command() 
@click.option("-c", "--path_config", help="Path to config yml to use")
def main(path_config):
    config = yaml.safe_load(open(path_config, 'r'))
    
    # Question: does selecting symbols with minimum pairwise correlation also ensure that
    # the daily returns of a single strategy across those symbols are uncorrelated?

    # Goal: produce a list of symbols that:
    #   - are minimally correlated with each other (price value or daily returns?)
    #   - have a minimum overall std (sufficient volatility)
    #   - have a minimum rolling std (volatility persists over time, not just historically)
    #   - have a minimum data period length
    #   - have overlapping data periods for at least N days
    # Additional parameters:
    #   - specific symbols (manually selected)
    #   - symbols to exclude (e.g. already have trained strategies for them)
    #   - sample fraction or count from all Alpaca symbols (e.g. 0.1 or 50)
    #   - diversify by sector: true/false
    #   - desired number of symbols in the output
    # Output: DataFrame/CSV with symbols, statistics, and correlations.
    # These symbols feed as input into run_strategy.py