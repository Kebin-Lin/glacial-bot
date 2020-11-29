import os, atexit
import psycopg2

DATABASE_URL = os.environ['DATABASE_URL']
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cursor = conn.cursor()

def confirmConnection():
    global conn, cursor
    if conn.closed != 0:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()

def eventExists(userID, eventName):
    cursor.execute("SELECT 1 FROM events WHERE organizerID = %s AND eventName = %s LIMIT 1", (userID, eventName,))
    return cursor.rowcount != 0

def createEvent(userID, eventName, eventDateTime, attendeeList, channelID, messageID):
    cursor.execute('''
        INSERT INTO events (organizerID, eventName, eventDateTime, channelID, messageID)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING eventID
    ''', (userID, eventName, eventDateTime, channelID, messageID,))
    eventID = cursor.fetchone()[0]
    args = b",".join(cursor.mogrify("(%s, %s)", (eventID, x,)) for x in attendeeList)
    cursor.execute(b"INSERT INTO pendingEventInvites (eventID, attendeeID) VALUES " + args)
    conn.commit()
    return True

def acceptInvite(eventID, attendeeID):
    cursor.execute("DELETE FROM pendingEventInvites WHERE eventID = %s AND attendeeID = %s RETURNING 1", (eventID, attendeeID,))
    if cursor.rowcount == 0:
        return False
    cursor.execute("INSERT INTO acceptedEventInvites (eventID, attendeeID) VALUES (%s, %s)", (eventID, attendeeID,))
    conn.commit()
    return True

def deleteEvent(eventID):
    cursor.execute("DELETE FROM events WHERE eventID = %s RETURNING 1", (eventID,))
    conn.commit()
    return cursor.rowcount == 1

def cancelEvent(userID, eventName):
    cursor.execute("DELETE FROM events WHERE organizerID = %s AND eventName = %s RETURNING 1", (userID, eventName,))
    conn.commit()
    return cursor.rowcount == 1

def getEventFromInvite(messageID):
    cursor.execute("SELECT * FROM events WHERE messageID = %s LIMIT 1", (messageID,))
    return cursor.fetchall()

def findEvents(eventDateTime):
    cursor.execute("SELECT * FROM events WHERE eventDateTime = %s", (eventDateTime,))
    return cursor.fetchall()

def getAcceptedInvites(eventID):
    cursor.execute("SELECT attendeeID FROM acceptedEventInvites WHERE eventID = %s", (eventID,))
    return cursor.fetchall()

def getPendingInvites(eventID):
    cursor.execute("SELECT attendeeID FROM pendingEventInvites WHERE eventID = %s", (eventID,))
    return cursor.fetchall()

def reset():
    cursor.execute("DELETE FROM toConfirm")
    cursor.execute("DELETE FROM scores")
    conn.commit()

def setScore(userID, score, numRaces):
    cursor.execute('''
        INSERT INTO scores (userID, score, numRaces)
        VALUES (%s, %s, %s)
        ON CONFLICT (userID)
        DO
            UPDATE SET score = EXCLUDED.score, numRaces = EXCLUDED.numRaces
    ''', (userID, score, numRaces,))
    conn.commit()

def confirmScore(userID):
    cursor.execute("SELECT score, numRaces FROM toConfirm WHERE userID = %s LIMIT 1", (userID,))
    if cursor.rowcount == 0:
        return False
    toAdd = cursor.fetchall()[0]
    cursor.execute("DELETE FROM toConfirm WHERE userID = %s", (userID,))
    cursor.execute('''
        INSERT INTO scores (userID, score, numRaces)
        VALUES (%s, %s, %s)
        ON CONFLICT (userID)
        DO
            UPDATE SET score = EXCLUDED.score + scores.score, numRaces = EXCLUDED.numRaces + scores.numRaces
    ''', (userID, toAdd[0], toAdd[1],))
    conn.commit()

def denyScore(userID):
    cursor.execute("DELETE FROM toConfirm WHERE userID = %s", (userID,))
    conn.commit()

def getUnconfirmedScores():
    cursor.execute("SELECT * FROM toConfirm")
    return cursor.fetchall()

def getSortedScores():
    cursor.execute("SELECT * FROM scores ORDER BY score DESC")
    return cursor.fetchall()

def reportScore(userID, reportedScore):
    cursor.execute('''
        INSERT INTO toConfirm (userID, score, numRaces)
        VALUES (%s, %s, %s)
        ON CONFLICT (userID)
        DO
            UPDATE SET score = EXCLUDED.score + toConfirm.score, numRaces = EXCLUDED.numRaces + toConfirm.numRaces
    ''', (userID, reportedScore, 1,))
    conn.commit()

@atexit.register
def saveChanges():
    conn.commit()
    cursor.close()