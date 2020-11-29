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
            score NUMERIC NOT NULL,
            numRaces NUMERIC NOT NULL
        )
        '''
    )
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS toConfirm(
            userID NUMERIC PRIMARY KEY,
            score NUMERIC NOT NULL,
            numRaces NUMERIC NOT NULL
        )
        '''
    )
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS events(
            eventID SERIAL PRIMARY KEY,
            organizerID NUMERIC NOT NULL,
            eventName TEXT NOT NULL,
            eventDateTime TIMESTAMP NOT NULL,
            channelID NUMERIC NOT NULL,
            messageID NUMERIC NOT NULL
        )
        '''
    )
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS pendingEventInvites(
            eventID INTEGER NOT NULL REFERENCES events(eventID) ON DELETE CASCADE,
            attendeeID NUMERIC NOT NULL
        )
        '''
    )
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS acceptedEventInvites(
            eventID INTEGER NOT NULL REFERENCES events(eventID) ON DELETE CASCADE,
            attendeeID NUMERIC NOT NULL
        )
        '''
    )

setup()
conn.commit()
cursor.close()