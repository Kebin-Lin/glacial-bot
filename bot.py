import os, math, asyncio, random, subprocess, datetime
import discord
from discord.ext import tasks, commands
from util import database

intents = discord.Intents.all()
client = discord.Client(intents=intents)

@tasks.loop(seconds=60.0)
async def checkForEvents():
    database.confirmConnection()
    currentTime = datetime.datetime.now(datetime.timezone.utc)
    currentTime = currentTime.replace(second = 0, microsecond = 0)
    eventCheckTime = currentTime + datetime.timedelta(minutes = 15)
    dayReminderTime = currentTime + datetime.timedelta(days = 1)
    reminderList = database.findEvents(eventCheckTime)
    dayReminderList = database.findEvents(dayReminderTime)
    embed = {
        "color" : 7855479,
        "author" : {
            "name" : "15 Minute Event Reminder",
            "icon_url" : str(client.user.avatar_url)
        },
        "fields" : [
            {
                "name" : "Event Name",
                "value" : "Event"
            },
            {
                "name" : "Time",
                "value" : "Placeholder"
            },
            {
                "name" : "Participants",
                "value" : "None"
            }
        ]
    }
    for event in reminderList:
        message = await client.get_channel(event[4]).fetch_message(event[5])
        participants = " ".join(client.get_user(x[0]).mention for x in database.getAcceptedInvites(event[0]))
        embed["fields"][0]["value"] = event[2]
        embed["fields"][1]["value"] = str(event[3])
        embed["fields"][2]["value"] = "None" if len(participants) == 0 else participants
        await message.channel.send(None if len(participants) == 0 else participants, embed = discord.Embed.from_dict(embed))
        database.deleteEvent(event[0])
    embed["author"]["name"] = "1 Day Event Reminder"
    for event in dayReminderList:
        message = await client.get_channel(event[4]).fetch_message(event[5])
        participants = " ".join(client.get_user(x[0]).mention for x in database.getAcceptedInvites(event[0]))
        embed["fields"][0]["value"] = event[2]
        embed["fields"][1]["value"] = str(event[3])
        embed["fields"][2]["value"] = "None" if len(participants) == 0 else participants
        await message.channel.send(None if len(participants) == 0 else participants, embed = discord.Embed.from_dict(embed))

@checkForEvents.before_loop
async def beforeStartLoop():
    await client.wait_until_ready()

async def helpFunc(message, splitcontent):
    embed = {
        "color" : 7855479,
        "author" : {
            "name" : "Command List",
            "icon_url" : str(client.user.avatar_url)
        },
        "fields" : []
    }
    if len(splitcontent) > 2:
        cmd = splitcontent[2].lower()
        if cmd in COMMAND_SET:
            if 'alias' in COMMAND_SET[cmd]:
                cmd = COMMAND_SET[cmd]['alias']
            embed['author']['name'] = f"!gb {cmd}"
            embed['fields'].append({
                'name' : "Description",
                'value' : COMMAND_SET[cmd]['helpmsg']
            })
            embed['fields'].append({
                'name' : "Usage",
                'value' : COMMAND_SET[cmd]['usage']
            })
        else:
            await message.channel.send('Invalid command, for a list of commands, use !market help')
            return
    else:
        for i in sorted(COMMAND_SET.keys()):
            if 'alias' not in COMMAND_SET[i]:
                embed['fields'].append({
                    "name" : i,
                    "value" : COMMAND_SET[i]['helpmsg']
                })
    await message.channel.send(embed = discord.Embed.from_dict(embed))

async def reportFunc(message, splitcontent):
    if len(splitcontent) < 3:
        await message.channel.send("No score supplied")
        return
    score = 0
    try:
        score = int(splitcontent[2])
    except:
        await message.channel.send("Invalid score supplied")
        return
    database.reportScore(message.author.id, score)
    await message.add_reaction('✅')

async def confirmFunc(message, splitcontent):
    leadermanrole = discord.utils.find(lambda r: r.name == "Leader Man", message.guild.roles)
    jrrole = discord.utils.find(lambda r: r.name == "Jrs", message.guild.roles)
    if not (leadermanrole in message.author.roles or jrrole in message.author.roles):
        await message.channel.send('You do not have the role for this command')
        return

    embed = {
        "color" : 7855479,
        "author" : {
            "name" : "Scores to Confirm",
            "icon_url" : str(client.user.avatar_url)
        },
        "fields" : []
    }
    scores = database.getUnconfirmedScores()
    offset = 0
    reactions = ['1️⃣','2️⃣','3️⃣','4️⃣','5️⃣','6️⃣','7️⃣','8️⃣','9️⃣','🔟','◀️','▶️','❌']
    confirmedSet = set()
    deniedSet = set()

    if len(scores) == 0:
        embed['fields'].append({
            'name' : '\u200b',
            'value' : 'No scores found'
        })
        await message.channel.send(embed = discord.Embed.from_dict(embed))
        return

    embed['footer'] = {"text" : "✅ Confirm mode active"}

    def setupPage(embed, scores):
        embed["fields"] = []
        formattedScores = []
        emotectr = 0
        for i in scores[offset : offset + 10]:
            formattedScores.append(f"{'✅' if offset + emotectr in confirmedSet else '❌' if offset + emotectr in deniedSet else reactions[emotectr]} **{str(client.get_user(i[0]))}** - {i[1]} points over {i[2]} race(s)")
            emotectr += 1
        embed['fields'].append({
            'name' : '\u200b',
            'value' : '\n'.join(formattedScores)
        })
    
    setupPage(embed, scores)
    sentMsg = await message.channel.send(embed = discord.Embed.from_dict(embed))
    for i in range(min(10, len(scores))):
        await sentMsg.add_reaction(reactions[i])
    for i in range(10, 13):
        await sentMsg.add_reaction(reactions[i])
    
    waitForReaction = True
    denyMode = False

    def check(reaction, user):
        return reaction.message.id == sentMsg.id and user == message.author and str(reaction.emoji) in reactions

    while waitForReaction:
        try:
            done, pending = await asyncio.wait(
                [
                    client.wait_for('reaction_add', check = check),
                    client.wait_for('reaction_remove', check = check)
                ],
                return_when = asyncio.FIRST_COMPLETED,
                timeout = 30,
            )
            #Cancel other task
            gather = asyncio.gather(*pending)
            gather.cancel()
            try:
                await gather
            except asyncio.CancelledError:
                pass
            if len(done) == 0:
                raise asyncio.TimeoutError('No change in reactions')
            reaction = done.pop().result()[0]
        except asyncio.TimeoutError:
            waitForReaction = False
            embed['color'] = 0xff6961
            await sentMsg.edit(embed = discord.Embed.from_dict(embed))
        else:
            emote = str(reaction.emoji)
            match = -1
            for i in range(12, -1, -1): #Search for matching emote in emote list
                if reactions[i] == emote:
                    match = i
                    break
            if match == 12: #Toggle deny mode
                denyMode = not denyMode
                if denyMode:
                    embed['footer'] = {'text' : '❌ Deny mode active'}
                else:
                    embed['footer'] = {'text' : '✅ Confirm mode active'}
                await sentMsg.edit(embed = discord.Embed.from_dict(embed))
            elif match == 11: #Next page
                if offset + 10 < len(scores):
                    offset += 10
                    setupPage(embed, scores)
                    await sentMsg.edit(embed = discord.Embed.from_dict(embed))
            elif match == 10: #Previous page
                if offset - 10 >= 0:
                    offset -= 10
                    setupPage(embed, scores)
                    await sentMsg.edit(embed = discord.Embed.from_dict(embed))
            else:
                if offset + match < len(scores) and offset + match not in confirmedSet:
                    if denyMode:
                        deniedSet.add(offset + match)
                        database.denyScore(scores[offset + match][0])
                    else:
                        confirmedSet.add(offset + match)
                        database.confirmScore(scores[offset + match][0])
                    setupPage(embed, scores)
                    await sentMsg.edit(embed = discord.Embed.from_dict(embed))

async def leaderboardFunc(message, splitcontent):
    embed = {
        "color" : 7855479,
        "author" : {
            "name" : "Leaderboards",
            "icon_url" : str(client.user.avatar_url)
        },
        "fields" : []
    }
    scores = database.getSortedScores()
    offset = 0

    if len(scores) == 0:
        embed['fields'].append({
            'name' : '\u200b',
            'value' : 'No scores found'
        })
        await message.channel.send(embed = discord.Embed.from_dict(embed))
        return

    def setupLeaderboard(embed, scores):
        placing = offset + 1
        embed['fields'] = []
        formattedPlacings = []
        for i in scores[offset : offset + 10]:
            formattedPlacings.append(f"{placing}. **{str(client.get_user(i[0]))}** - {i[1]} points over {i[2]} race(s)")
            placing += 1
        embed['fields'].append({
            'name' : '\u200b',
            'value' : '\n'.join(formattedPlacings)
        })
    
    setupLeaderboard(embed, scores)
    sentMsg = await message.channel.send(embed = discord.Embed.from_dict(embed))

    def check(reaction, user):
        return reaction.message.id == sentMsg.id and user == message.author and str(reaction.emoji) in reactions

    waitForReaction = True
    reactions = ['◀️','▶️']

    for i in reactions:
        await sentMsg.add_reaction(i)

    while waitForReaction:
        try:
            done, pending = await asyncio.wait(
                [
                    client.wait_for('reaction_add', check = check),
                    client.wait_for('reaction_remove', check = check)
                ],
                return_when = asyncio.FIRST_COMPLETED,
                timeout = 30,
            )
            #Cancel other task
            gather = asyncio.gather(*pending)
            gather.cancel()
            try:
                await gather
            except asyncio.CancelledError:
                pass
            if len(done) == 0:
                raise asyncio.TimeoutError('No change in reactions')
            reaction = done.pop().result()[0]
        except asyncio.TimeoutError:
            waitForReaction = False
            embed['color'] = 0xff6961
            await sentMsg.edit(embed = discord.Embed.from_dict(embed))
        else:
            emote = str(reaction.emoji)
            match = -1
            for i in range(2): #Search for matching emote in emote list
                if reactions[i] == emote:
                    match = i
                    break
            if match == 1: #Next page
                if offset + 10 < len(scores):
                    offset += 10
                    setupLeaderboard(embed, scores)
                    await sentMsg.edit(embed = discord.Embed.from_dict(embed))
            elif match == 0: #Previous page
                if offset - 10 >= 0:
                    offset -= 10
                    setupLeaderboard(embed, scores)
                    await sentMsg.edit(embed = discord.Embed.from_dict(embed))

async def resetFunc(message, splitcontent):
    role = discord.utils.find(lambda r: r.name == "Leader Man", message.guild.roles)
    if role in message.author.roles:
        database.reset()
        await message.add_reaction('✅')
    else:
        await message.channel.send('You do not have the role for this command')

async def setscoreFunc(message, splitcontent):
    leadermanrole = discord.utils.find(lambda r: r.name == "Leader Man", message.guild.roles)
    jrrole = discord.utils.find(lambda r: r.name == "Jrs", message.guild.roles)
    if not (leadermanrole in message.author.roles or jrrole in message.author.roles or message.author.id == 149328493740556288):
        await message.channel.send('You do not have the role for this command')
        return
    
    if len(message.mentions) < 1:
        await message.channel.send('No target mentioned')
        return
    
    if len(splitcontent) < 5:
        await message.channel.send('No score/number of races specified')
        return
    
    newScore = 0
    try:
        newScore = int(splitcontent[3])
    except:
        await message.channel.send('Invalid score specified')
        return
    
    newNumRaces = 0
    try:
        newNumRaces = int(splitcontent[4])
    except:
        await message.channel.send('Invalid number of races specified')
        return
    
    database.setScore(message.mentions[0].id, newScore, newNumRaces)
    await message.add_reaction('✅')

async def raffleFunc(message, splitcontent):
    role = discord.utils.find(lambda r: r.name == "Leader Man", message.guild.roles)
    if role not in message.author.roles:
        await message.channel.send('You do not have the role for this command')
        return
    
    embed = {
        "color" : 7855479,
        "author" : {
            "name" : "Raffle",
            "icon_url" : str(client.user.avatar_url)
        },
        "fields" : [
            {
                'name' : '25k NX Gift Winner',
                'value' : '❓'
            },
            {
                'name' : '10k NX Winner',
                'value' : '❓'
            },
            {
                'name' : '10k NX Winner',
                'value' : '❓'
            }
        ]
    }

    winners = []
    scores = database.getSortedScores()
    validEntries = []
    totalTickets = 0

    for i in scores: #Set up list of people who have over ten races
        if i[2] < 10:
            continue
        numTickets = 3 + (i[1] / 100)
        validEntries.append([i[0], numTickets])
        totalTickets += numTickets
    
    if len(validEntries) < 3:
        await message.channel.send('Less than three people are elegible for the raffle')
        return

    totalTickets = float(totalTickets)

    for i in range(3):
        winner = random.random() * totalTickets
        accumulator = 0
        for i in validEntries:
            accumulator += i[1]
            if accumulator > winner: #Winner found
                winners.append(i[0])
                totalTickets -= float(i[1])
                i[1] = 0
                break

    sentMsg = await message.channel.send(embed = discord.Embed.from_dict(embed))

    def check(reaction, user):
        return reaction.message.id == sentMsg.id and user == message.author and str(reaction.emoji) in reactions

    waitForReaction = True
    numRevealed = 0
    reactions = ['⏩']
    await sentMsg.add_reaction('⏩')

    while waitForReaction:
        try:
            done, pending = await asyncio.wait(
                [
                    client.wait_for('reaction_add', check = check),
                    client.wait_for('reaction_remove', check = check)
                ],
                return_when = asyncio.FIRST_COMPLETED,
                timeout = 60,
            )
            #Cancel other task
            gather = asyncio.gather(*pending)
            gather.cancel()
            try:
                await gather
            except asyncio.CancelledError:
                pass
            if len(done) == 0:
                raise asyncio.TimeoutError('No change in reactions')
            reaction = done.pop().result()[0]
        except asyncio.TimeoutError:
            waitForReaction = False
            embed['color'] = 0xff6961
            await sentMsg.edit(embed = discord.Embed.from_dict(embed))
        else:
            emote = str(reaction.emoji)
            if emote == '⏩':
                if numRevealed < 3:
                    embed['fields'][2 - numRevealed]['value'] = str(client.get_user(winners[2 - numRevealed]))
                    numRevealed += 1
                    await sentMsg.edit(embed = discord.Embed.from_dict(embed))
                else:
                    waitForReaction = False
                    embed['color'] = 0xff6961
                    await sentMsg.edit(embed = discord.Embed.from_dict(embed))

async def sfcalcFunc(message, splitcontent, numTrials = 1000):
    try:
        start = int(splitcontent[2])
        if (start < 0 or start > 21):
            await message.channel.send('Invalid starting star')
            return
        goal = int(splitcontent[3])
        if (goal < 0 or goal > 22):
            await message.channel.send('Invalid goal')
            return
        equiplv = int(splitcontent[4])
        if (equiplv < 1 or equiplv > 200):
            await message.channel.send('Invalid item level')
            return
        optionalArgs = splitcontent[5:]
        discount = 1
        safeguard = int("safeguard" in optionalArgs)
        fivetenfifteen = int("5/10/15" in optionalArgs)
        thirtyperc = int("30%" in optionalArgs)
        process = subprocess.Popen(["./sfcalc", str(start), str(goal), str(equiplv), str(numTrials), str(discount), str(safeguard), str(fivetenfifteen), str(thirtyperc)], stdout = subprocess.PIPE)
        avgMeso = process.stdout.readline().decode('utf-8').strip()
        avgBooms = process.stdout.readline().decode('utf-8').strip()
        noBoomRate = process.stdout.readline().decode('utf-8').strip()
        activeOptions = []
        if (safeguard):
            activeOptions.append("Safeguard")
        if (fivetenfifteen):
            activeOptions.append("5/10/15")
        if (thirtyperc):
            activeOptions.append("30%")
        if len(activeOptions) == 0:
            activeOptions.append("None")
        embed = {
            "color" : 7855479,
            "author" : {
                "name" : "Star Force Calculator",
                "icon_url" : str(client.user.avatar_url)
            },
            "fields" : [
                {
                    "name" : "Starting Star",
                    "value" : start,
                    "inline" : True
                },
                {
                    "name" : "Star Goal",
                    "value" : goal,
                    "inline" : True
                },
                {
                    "name" : "Item Level",
                    "value" : equiplv,
                    "inline" : True
                },
                {
                    "name" : "Active Options",
                    "value" : "\n".join(activeOptions)
                },
                {
                    "name" : "Average Meso Cost" if numTrials != 1 else "Meso Cost",
                    "value" : "{:,}".format(int(avgMeso))
                },
                {
                    "name" : "Average Number of Booms" if numTrials != 1 else "Number of Booms",
                    "value" : avgBooms
                }
            ]
        }
        if (numTrials != 1):
            embed['fields'].append({
                "name" : "No Boom Rate",
                "value" : f"{round(float(noBoomRate) * 100, 1)}%"
            })
        await message.channel.send(embed = discord.Embed.from_dict(embed))
        return
    except:
        await message.channel.send('Invalid input')
        return

async def sfrollFunc(message, splitcontent):
    await sfcalcFunc(message, splitcontent, numTrials = 1)

async def scheduleFunc(message, splitcontent):
    weekdays = {
        'monday' : 0, 'mon' : 0, 'tuesday' : 1, 'tues' : 1, 'wednesday' : 2, 'wed' : 2, 'thursday' : 3, 'thurs' : 3,
        'friday' : 4, 'fri' : 4, 'saturday' : 5, 'sat' : 5, 'sunday' : 6, 'sun' : 6
    }
    organizer = message.author.id
    eventName = splitcontent[2]
    if eventName == "":
        await message.channel.send("No event name provided")
        return
    eventTime = splitcontent[3].split(',')
    eventTime[0] = eventTime[0].lower()
    if eventTime[0] not in weekdays:
        await message.channel.send("Invalid day provided.")
        return
    try:
        eventTime[1] = eval(eventTime[1])
    except:
        await message.channel.send("Invalid time provided.")
        return
    eventTime[0] = weekdays[eventTime[0]]
    today = datetime.datetime.now(datetime.timezone.utc)
    today = today.replace(hour = 0, minute = 0, second = 0, microsecond = 0)
    daysUntil = (((eventTime[0] + 1) % 7) - today.weekday()) % 7
    eventTime = today + datetime.timedelta(days = daysUntil, hours = eventTime[1])
    eventTime = eventTime.replace(second = 0, microsecond = 0)
    if eventTime <= datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes = 15):
        await message.channel.send("You cannot schedule an event that is 15 minutes or less away.")
        return
    participants = [x.id for x in message.mentions]
    if len(participants) == 0:
        await message.channel.send("No participants provided.")
        return
    if database.eventExists(organizer, eventName):
        await message.channel.send("You already have an event with the same name.")
        return
    embed = {
        "color" : 7855479,
        "author" : {
            "name" : "Event Invite",
            "icon_url" : str(client.user.avatar_url)
        },
        "fields" : [
            {
                "name" : "Event Name",
                "value" : eventName
            },
            {
                "name" : "Time",
                "value" : str(eventTime)
            },
            {
                "name" : "Participants",
                "value" : "None"
            },
            {
                "name" : "Pending Invites",
                "value" : " ".join(client.get_user(x).mention for x in participants)
            }
        ]
    }
    sentMsg = await message.channel.send(embed = discord.Embed.from_dict(embed))
    database.createEvent(organizer, eventName, eventTime, participants, sentMsg.channel.id, sentMsg.id)
    await sentMsg.add_reaction('✅')

async def cancelFunc(message, splitcontent):
    organizer = message.author.id
    eventName = splitcontent[2]
    if database.cancelEvent(organizer, eventName):
        await message.add_reaction('✅')
    else:
        await message.channel.send(f'You are not an organizer of an event titled {eventName}')

COMMAND_SET = {
    'help' : {
        'helpmsg' : 'Prints out the list of commands available, !gb help <cmd> for command usage',
        'usage' : '!gb help <cmd>',
        'function' : helpFunc
    },
    'report' : {
        'helpmsg' : 'Reports a score',
        'usage' : '!gb report <score>',
        'function' : reportFunc
    },
    'confirm' : {
        'helpmsg' : 'Opens menu to confirm scores (JR+ only)',
        'usage' : '!gb confirm',
        'function' : confirmFunc
    },
    'leaderboard' : {
        'helpmsg' : 'Opens the score leaderboard (only considers already confirmed scores)',
        'usage' : '!gb leaderboard',
        'function' : leaderboardFunc
    },
    'lb' : {
        'alias' : 'leaderboard'
    },
    'reset' : {
        'helpmsg' : 'Resets all scores (Leaderman only command)',
        'usage' : '!gb reset',
        'function' : resetFunc
    },
    'setscore' : {
        'helpmsg' : 'Sets the score of a user (JR+ only)',
        'usage' : '!gb setScore @target <score> <number of races>',
        'function' : setscoreFunc
    },
    'raffle' : {
        'helpmsg' : 'Initiates raffle drawing (Leaderman only command)',
        'usage' : '!gb raffle',
        'function' : raffleFunc
    },
    'sfcalc' : {
        'helpmsg' : 'Simulates starforcing',
        'usage' : '!gb sfcalc <start stars> <target stars> <item level> Optional: safeguard 5/10/15 30%',
        'function' : sfcalcFunc
    },
    'sfroll' : {
        'helpmsg' : 'Simulates one roll for starforce',
        'usage' : '!gb sfroll <start stars> <target stars> <item level> Optional: safeguard 5/10/15 30%',
        'function' : sfrollFunc
    },
    'schedule' : {
        'helpmsg' : 'Schedules an event',
        'usage' : '!gb schedule <event name> <event time (Monday,+2 for Monday, Reset + 2 hours)> <participant1> <participant2> ...',
        'function' : scheduleFunc
    },
    'cancel' : {
        'helpmsg' : 'Cancels an event',
        'usage' : '!gb cancel <event name>',
        'function' : cancelFunc
    }
}

print("Starting Bot")

@client.event
async def on_ready():
    print(f'Logged on as {client.user}')
    await client.change_presence(activity = discord.Game(name = 'Use "!gb help" for a list of commands'))

@client.event
async def on_message(message):
    if message.author == client.user or message.guild is False: #Ignore messages by self and in DMs
        return

    if message.content.startswith('!gb'):
        splitcontent = message.content.split()
        if len(splitcontent) <= 1 or splitcontent[1].lower() not in COMMAND_SET:
            await message.channel.send('Invalid command, for a list of commands, use !gb help')
            return
        else:
            cmd = splitcontent[1].lower()
            if 'alias' in COMMAND_SET[cmd]:
                cmd = COMMAND_SET[cmd]['alias']
            await COMMAND_SET[cmd]['function'](message, splitcontent)
    # await message.channel.send(output)

@client.event
async def on_raw_reaction_add(payload):
    message = await client.get_channel(payload.channel_id).fetch_message(payload.message_id)
    if message.author.id == client.user.id:
        eventInfo = database.getEventFromInvite(message.id)
        if len(eventInfo) != 0:
            eventInfo = eventInfo[0]
            eventName = eventInfo[2]
            eventTime = eventInfo[3]
            if database.acceptInvite(eventInfo[0], payload.user_id): #Valid user accepted invite
                participants = [x[0] for x in database.getAcceptedInvites(eventInfo[0])]
                pending = [x[0] for x in database.getPendingInvites(eventInfo[0])]
                embed = {
                    "color" : 7855479,
                    "author" : {
                        "name" : "Event Invite",
                        "icon_url" : str(client.user.avatar_url)
                    },
                    "fields" : [
                        {
                            "name" : "Event Name",
                            "value" : eventName
                        },
                        {
                            "name" : "Time",
                            "value" : str(eventTime)
                        },
                        {
                            "name" : "Participants",
                            "value" : "None" if len(participants) == 0 else " ".join(client.get_user(x).mention for x in participants)
                        },
                        {
                            "name" : "Pending Invites",
                            "value" : "None" if len(pending) == 0 else " ".join(client.get_user(x).mention for x in pending)
                        }
                    ]
                }
                await message.edit(embed = discord.Embed.from_dict(embed))

            

checkForEvents.start()
client.run(os.environ["token"])
