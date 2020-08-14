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

def reportFunc(message, splitcontent):
    pass

def confirmFunc(message, splitcontent):
    pass

def leaderboardFunc(message, splitcontent):
    pass

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
    'lb' {
        'alias' : 'leaderboard'
    }
}

print("Starting Bot")

@client.event
async def on_ready():
    print(f'Logged on as {client.user}')
    await client.change_presence(activity = discord.Game(name = 'Use "!market help" for a list of commands'))

@client.event
async def on_message(message):
    if message.author == client.user: #Ignore messages by self
        return

    if message.content.startswith('!market'):
        splitcontent = message.content.split()
        if len(splitcontent) <= 1 or splitcontent[1].lower() not in COMMAND_SET:
            await message.channel.send('Invalid command, for a list of commands, use !market help')
            return
        else:
            cmd = splitcontent[1].lower()
            if 'alias' in COMMAND_SET[cmd]:
                cmd = COMMAND_SET[cmd]['alias']
            await COMMAND_SET[cmd]['function'](message, splitcontent)
    # await message.channel.send(output)

client.run(os.environ["token"])