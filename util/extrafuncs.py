import math, socket, time, aiohttp, asyncio, heapq, datetime

CHANNEL_LIST = [
    "35.155.204.207",
    "52.26.82.74",
    "34.217.205.66",
    "35.161.183.101",
    "54.218.157.183",
    "52.25.78.39",
    "54.68.160.34",
    "34.218.141.142",
    "52.33.249.126",
    "54.148.170.23",
    "54.201.184.26",
    "54.191.142.56",
    "52.13.185.207",
    "34.215.228.37",
    "54.187.177.143",
    "54.203.83.148",
    "54.148.188.235",
    "52.43.83.76",
    "54.69.114.137",
    "54.148.137.49",
    "54.212.109.33",
    "44.230.255.51",
    "100.20.116.83",
    "54.188.84.22",
    "34.215.170.50",
    "54.184.162.28",
    "54.185.209.29",
    "52.12.53.225",
    "54.189.33.238",
    "54.188.84.238"
]
TIMEOUT_DURATION = 2
ABBREVIATIONS = ['', 'K', 'M', 'B', 'T']
ABBREVIATION_DICT = {
    '' : 1,
    'k' : 1000,
    'm' : 1000000,
    'mil' : 1000000,
    'b' : 1000000000,
    'bil' : 1000000000,
    't' : 1000000000000,
    'tril' : 1000000000000
}
WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

def utcToResetDelta(utcdatetime):
    resetDelta = utcdatetime.hour + (utcdatetime.minute / 60)
    dayOffset = -1
    if resetDelta > 12:
        dayOffset = 0
        resetDelta = resetDelta - 24
    return f"{WEEKDAYS[utcdatetime.weekday() + dayOffset]} Reset {'+' if resetDelta > 0 else ''}{resetDelta}"


def roundSig(n):
    if n == 0:
        return 0, 0
    power = int(math.floor(math.log10(abs(n))))
    if power < 1:
        power = 0
        return round(n, 2), power
    return round(n, 4 - int(math.floor(math.log10(abs(n)))) - 1), power

def shortenNum(n):
    n, power = roundSig(n)
    if power // 3 == 0:
        return str(n)
    if power > 14:
        return "{:.3e}".format(n)
    return str(n / (10 ** (power // 3 * 3))) + ABBREVIATIONS[power // 3]

def serverStatusSummary(pingHistory):
    averages = []
    timeouts = []
    stddevs = []
    for i in pingHistory:
        numTimeouts = 0
        subt = 0
        for j in i:
            if j >= TIMEOUT_DURATION * 1000:
                numTimeouts += 1
            else:
                subt += j
        averages.append(subt / (len(i) - numTimeouts) if (len(i) - numTimeouts) != 0 else 0)
        timeouts.append(numTimeouts)
    for i in range(len(pingHistory)):
        subt = 0
        for j in pingHistory[i]:
            if j < TIMEOUT_DURATION * 1000:
                subt += (j - averages[i]) ** 2
        stddevs.append((subt / (len(pingHistory[i]) - timeouts[i])) ** .5 if (len(pingHistory[i]) - timeouts[i]) != 0 else 0)
    infoStrings = [f"Analysis over {round(len(pingHistory[0]) / 6, 2)} minute(s)\nCh#: <Average>, <% of Timeouts>, <Standard Deviation>\n"]
    for i in range(len(pingHistory)):
        channelInfo = f"Ch{('0' * (2 - len(str(i + 1)))) + str(i + 1)}: {round(averages[i])}ms, {round((timeouts[i] / len(pingHistory[i])) * 100, 2)}%, {round(stddevs[i])}ms"
        channelInfo += "\n" if (i % 2 == 1) else (" " * (30 - len(channelInfo)))
        infoStrings.append(channelInfo)
    lowestAverages = heapq.nsmallest(5, [x for x in range(len(CHANNEL_LIST))], key = lambda x: averages[x])
    lowestStddevs = heapq.nsmallest(5, [x for x in range(len(CHANNEL_LIST))], key = lambda x: stddevs[x])
    infoStrings.append("Lowest Averages:\n")
    lowestAverages = [f"Ch{('0' * (2 - len(str(x + 1)))) + str(x + 1)}: {round(averages[x], 2)}ms" for x in lowestAverages]
    infoStrings.append(", ".join(lowestAverages))
    infoStrings.append("\nLowest Standard Deviations:\n")
    lowestStddevs = [f"Ch{('0' * (2 - len(str(x + 1)))) + str(x + 1)}: {round(stddevs[x], 2)}ms" for x in lowestStddevs]
    infoStrings.append(", ".join(lowestStddevs))
    return "".join(infoStrings)

async def ping(loop, ip, port = 8585, timeout = TIMEOUT_DURATION):
    start = time.time()
    try:
        req = f"https://{ip}:{port}/"
        timeout = aiohttp.ClientTimeout(total = TIMEOUT_DURATION)
        async with aiohttp.ClientSession(timeout = timeout) as session:
            async with session.get(req) as response:
                pass
    except:
        pass
    output = 1000 * (time.time() - start)
    return output