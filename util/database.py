import os, atexit
import psycopg2

DATABASE_URL = os.environ['DATABASE_URL']
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cursor = conn.cursor()

def confirmScore(userID):
    cursor.execute("SELECT score FROM toConfirm WHERE userID = %s LIMIT 1", (userID,))
    if cursor.rowcount == 0:
        return False
    toAdd = cursor.fetchall()[0][0]
    cursor.execute("UPDATE scores SET score = score + %s WHERE userID = %s", (toAdd, userID))
    conn.commit()

def getUnconfirmedScores():
    cursor.execute("SELECT userID, score FROM toConfirm")
    return cursor.fetchall()

def getSortedScores():
    cursor.execute("SELECT userID, score FROM scores ORDER BY score DESC")
    return cursor.fetchall()

def reportScore(userID, reportedScore):
    cursor.execute("SELECT score FROM toConfirm WHERE userID = %s LIMIT 1", (userID,))
    if cursor.rowcount == 0:
        cursor.execute("INSERT INTO toConfirm (userID, score) VALUES (%s, %s)", (userID, reportedScore,))
    else:
        cursor.execute("UPDATE toConfirm SET score = score + %s WHERE userID = %s", (reportedScore, userID))
    conn.commit()

@atexit.register
def saveChanges():
    conn.commit()
    cursor.close()