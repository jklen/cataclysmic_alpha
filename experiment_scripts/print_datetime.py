import datetime
import click

@click.command() 
@click.option("-c", "--path_config", help="Path to config yml to use")
def main(path_config):
    # Print the current date and time
    print(f"Current date and time: {datetime.datetime.now()}")
    print(path_config)
    from pathlib import Path

    Path('empty_file.txt').touch()

if __name__ == '__main__':
    main()


