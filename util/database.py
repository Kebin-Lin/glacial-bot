import os, atexit
import psycopg2

DATABASE_URL = os.environ['DATABASE_URL']
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cursor = conn.cursor()

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