import pdb
import logging
import logging.config
import json
import pandas as pd
import click
import yaml

with open('../portfolio_logging_config.json', 'r') as config_file:
    config_dict = json.load(config_file)

logging.config.dictConfig(config_dict)
logger = logging.getLogger(__name__)
logger.info("Logging is set up.")

@click.command() 
@click.option("-c", "--path_config", help="Path to config yml to use")
def main(path_config):
    config = yaml.safe_load(open(path_config, 'r'))
    
if __name__ == '__main__':
    main()