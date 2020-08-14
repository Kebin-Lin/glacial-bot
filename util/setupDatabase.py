import os
import psycopg2

DATABASE_URL = os.environ['DATABASE_URL']
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cursor = conn.cursor()

def setup():
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS scores(
            userID NUMERIC PRIMARY KEY,
            score NUMERIC NOT NULL
        )
        '''
    )
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS toConfirm(
            userID NUMERIC PRIMARY KEY,
            score NUMERIC NOT NULL
        )
        '''
    )

setup()
conn.commit()
cursor.close()