import sqlite3
import os

con = sqlite3.connect('../db/calpha.db')
cur = con.cursor()