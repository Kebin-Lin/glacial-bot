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
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS pendingScoreReports(
            messageID NUMERIC PRIMARY KEY,
            channelID NUMERIC NOT NULL
        )
        '''
    )
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS reminderSettings(
            userID NUMERIC NOT NULL,
            timeBefore INTERVAL NOT NULL,
            PRIMARY KEY (userID, timeBefore)
        )
        '''
    )

setup()
# cursor.execute("ALTER TABLE pendingEventInvites DROP CONSTRAINT constraint_fk")
# cursor.execute("ALTER TABLE pendingEventInvites ADD FOREIGN KEY (eventID) REFERENCES events(eventID) ON DELETE CASCADE")
# cursor.execute("ALTER TABLE acceptedEventInvites ADD FOREIGN KEY (eventID) REFERENCES events(eventID) ON DELETE CASCADE")
# cursor.execute("DELETE FROM pendingEventInvites WHERE NOT EXISTS(SELECT NULL FROM events WHERE events.eventID = pendingEventInvites.eventID)")
# cursor.execute("DELETE FROM acceptedEventInvites WHERE NOT EXISTS(SELECT NULL FROM events WHERE events.eventID = acceptedEventInvites.eventID)")
conn.commit()
cursor.close()