import os, atexit
import psycopg2

DATABASE_URL = os.environ['DATABASE_URL']
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cursor = conn.cursor()

def reconnect(func):
    def wrapper(*args, **kwargs):
        global conn, cursor
        while True:
            try:
                return func(*args, **kwargs)
            except (psycopg2.errors.AdminShutdown, psycopg2.InterfaceError, psycopg2.OperationalError):
                print("Reconnecting to Database")
                conn = psycopg2.connect(DATABASE_URL, sslmode='require')
                cursor = conn.cursor()
            except:
                raise
    return wrapper

@reconnect
def eventExists(userID, eventName):
    cursor.execute("SELECT 1 FROM events WHERE organizerID = %s AND eventName = %s LIMIT 1", (userID, eventName,))
    return cursor.rowcount != 0

@reconnect
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

@reconnect
def getInviteMessageIDs():
    cursor.execute('''SELECT channelID, messageID FROM events''')
    return cursor.fetchall()

@reconnect
def addInvite(userID, eventID, attendeeList):
    numAdded = 0
    for attendeeID in attendeeList:    
        cursor.execute("SELECT 1 FROM acceptedEventInvites WHERE eventID = %s AND attendeeID = %s", (eventID, attendeeID,))
        if cursor.rowcount != 0:
            continue
        cursor.execute("SELECT 1 FROM pendingEventInvites WHERE eventID = %s AND attendeeID = %s", (eventID, attendeeID,))
        if cursor.rowcount != 0:
            continue
        cursor.execute("INSERT INTO pendingEventInvites (eventID, attendeeID) VALUES (%s, %s)", (eventID, attendeeID,))
        numAdded += 1
    return numAdded

@reconnect
def acceptInvite(eventID, attendeeID):
    cursor.execute("DELETE FROM pendingEventInvites WHERE eventID = %s AND attendeeID = %s RETURNING 1", (eventID, attendeeID,))
    if cursor.rowcount == 0:
        return False
    cursor.execute("INSERT INTO acceptedEventInvites (eventID, attendeeID) VALUES (%s, %s)", (eventID, attendeeID,))
    conn.commit()
    return True

@reconnect
def unacceptInvite(eventID, attendeeID):
    cursor.execute("DELETE FROM acceptedEventInvites WHERE eventID = %s AND attendeeID = %s RETURNING 1", (eventID, attendeeID,))
    if cursor.rowcount == 0:
        return False
    cursor.execute("INSERT INTO pendingEventInvites (eventID, attendeeID) VALUES (%s, %s)", (eventID, attendeeID,))
    conn.commit()
    return True

@reconnect
def deleteEvent(eventID):
    cursor.execute("DELETE FROM events WHERE eventID = %s RETURNING 1", (eventID,))
    conn.commit()
    return cursor.rowcount == 1

@reconnect
def cancelEvent(userID, eventName):
    cursor.execute("DELETE FROM events WHERE organizerID = %s AND eventName = %s RETURNING 1", (userID, eventName,))
    conn.commit()
    return cursor.rowcount == 1

@reconnect
def getEventFromName(userID, eventName):
    cursor.execute("SELECT * FROM events WHERE organizerID = %s AND eventName = %s LIMIT 1", (userID, eventName))
    return cursor.fetchall()

@reconnect
def getEventFromInvite(messageID):
    cursor.execute("SELECT * FROM events WHERE messageID = %s LIMIT 1", (messageID,))
    return cursor.fetchall()

@reconnect
def getUpcoming(userID):
    cursor.execute("SELECT * FROM events WHERE EXISTS (SELECT 1 FROM acceptedEventInvites WHERE events.eventID = acceptedEventInvites.eventID AND attendeeID = %s LIMIT 1)", (userID,))
    return cursor.fetchall()

@reconnect
def findEvents(eventDateTime):
    cursor.execute("SELECT * FROM events WHERE eventDateTime = %s", (eventDateTime,))
    return cursor.fetchall()

@reconnect
def findEventsInMultiple(eventDateTime):
    cursor.execute('''
        SELECT *, (eventDateTime - %s) FROM events WHERE
        (eventDateTime - %s) <= INTERVAL '1 day' AND
        EXTRACT(MINUTE FROM (eventDateTime - %s) / .25) = 0
    ''', (eventDateTime, eventDateTime, eventDateTime,))
    return cursor.fetchall()

@reconnect
def getReminders(eventID, timeDiff):
    cursor.execute('''
        SELECT attendeeID FROM acceptedEventInvites WHERE
        eventID = %s AND
        CASE WHEN EXISTS (SELECT 1 FROM reminderSettings WHERE userID = attendeeID LIMIT 1) THEN (
            EXISTS (
                SELECT 1 FROM reminderSettings WHERE
                userID = attendeeID AND
                timeBefore = %s
                LIMIT 1
            )
        ) ELSE (EXISTS(SELECT 1 WHERE %s = INTERVAL '1 day' OR %s = INTERVAL '1 hour' LIMIT 1))
        END
    ''', (eventID, timeDiff, timeDiff, timeDiff,))
    return cursor.fetchall()

@reconnect
def updateReminderSettings(userID, times):
    cursor.execute("DELETE FROM reminderSettings WHERE userID = %s", (userID,))
    if len(times) != 0:
        args = b",".join(cursor.mogrify("(%s, %s)", (userID, x)) for x in times)
        cursor.execute(b"INSERT INTO reminderSettings (userID, timeBefore) VALUES " + args)
    conn.commit()
    return True

@reconnect
def findConflicts(userIDs, eventDateTime):
    subcommand = '''(
    SELECT attendeeID FROM acceptedEventInvites
    WHERE attendeeID = %s AND
    EXISTS (SELECT 1 FROM events WHERE events.eventID = acceptedEventInvites.eventID AND events.eventDateTime = %s LIMIT 1)
    LIMIT 1
    )'''
    cursor.execute(b"UNION".join(cursor.mogrify(subcommand, (x, eventDateTime,)) for x in userIDs))
    return cursor.fetchall()

@reconnect
def getAcceptedInvites(eventID):
    cursor.execute("SELECT attendeeID FROM acceptedEventInvites WHERE eventID = %s", (eventID,))
    return cursor.fetchall()

@reconnect
def getPendingInvites(eventID):
    cursor.execute("SELECT attendeeID FROM pendingEventInvites WHERE eventID = %s", (eventID,))
    return cursor.fetchall()

@reconnect
def reset():
    cursor.execute("DELETE FROM pendingScoreReports")
    cursor.execute("DELETE FROM scores")
    conn.commit()

@reconnect
def setScore(userID, score, numRaces):
    cursor.execute('''
        INSERT INTO scores (userID, score, numRaces)
        VALUES (%s, %s, %s)
        ON CONFLICT (userID)
        DO
            UPDATE SET score = EXCLUDED.score, numRaces = EXCLUDED.numRaces
    ''', (userID, score, numRaces,))
    conn.commit()

@reconnect
def isPendingReport(messageID):
    cursor.execute("SELECT 1 FROM pendingScoreReports WHERE messageID = %s", (messageID,))
    return cursor.rowcount == 1

@reconnect
def createReport(messageID, channelID):
    cursor.execute("INSERT INTO pendingScoreReports (messageID, channelID) VALUES (%s, %s)", (messageID, channelID,))
    conn.commit()

@reconnect
def removeReport(messageID):
    cursor.execute("DELETE FROM pendingScoreReports WHERE messageID = %s RETURNING 1", (messageID,))
    conn.commit()
    return cursor.rowcount == 1

@reconnect
def applyScore(userID, score):
    cursor.execute('''
        INSERT INTO scores (userID, score, numRaces)
        VALUES (%s, %s, %s)
        ON CONFLICT (userID)
        DO
            UPDATE SET score = EXCLUDED.score + scores.score, numRaces = EXCLUDED.numRaces + scores.numRaces
    ''', (userID, score, 1,))
    conn.commit()

@reconnect
def getSortedScores():
    cursor.execute("SELECT * FROM scores ORDER BY score DESC")
    return cursor.fetchall()

@atexit.register
@reconnect
def saveChanges():
    conn.commit()
    cursor.close()
