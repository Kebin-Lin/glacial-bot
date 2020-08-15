import os, math, asyncio, random
import discord
from util import database

client = discord.Client()

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
    reactions = ['1️⃣','2️⃣','3️⃣','4️⃣','5️⃣','6️⃣','7️⃣','8️⃣','9️⃣','🔟','◀️','▶️']
    confirmedSet = set()

    if len(scores) == 0:
        embed['fields'].append({
            'name' : '\u200b',
            'value' : 'No scores found'
        })
        await message.channel.send(embed = discord.Embed.from_dict(embed))
        return

    def setupPage(embed, scores):
        embed["fields"] = []
        formattedScores = []
        emotectr = 0
        for i in scores[offset : offset + 10]:
            formattedScores.append(f"{reactions[emotectr] if offset + emotectr not in confirmedSet else '✅'} **{str(client.get_user(i[0]))}** - {i[1]} points over {i[2]} race(s)")
            emotectr += 1
        embed['fields'].append({
            'name' : '\u200b',
            'value' : '\n'.join(formattedScores)
        })
    
    setupPage(embed, scores)
    sentMsg = await message.channel.send(embed = discord.Embed.from_dict(embed))
    for i in range(min(10, len(scores))):
        await sentMsg.add_reaction(reactions[i])
    for i in range(10, 12):
        await sentMsg.add_reaction(reactions[i])
    
    waitForReaction = True

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
            for i in range(11, -1, -1): #Search for matching emote in emote list
                if reactions[i] == emote:
                    match = i
                    break
            if match == 11: #Next page
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
                    confirmedSet.add(offset + match)
                    setupPage(embed, scores)
                    database.confirmScore(scores[offset + match][0])
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
    if not (leadermanrole in message.author.roles or jrrole in message.author.roles):
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
        newScore = int(splitcontent[4])
    except:
        await message.channel.send('Invalid number of races specified')
        return
    
    database.setScore(message.mentions[0].id, newScore, newNumRaces)
    await message.add_reaction('✅')

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

client.run(os.environ["token"])