import os, math, asyncio, random, subprocess, datetime
import discord
from discord.ext import tasks, commands
from util import database, extrafuncs

TEST_MODE = bool(int(os.environ["testMode"]))
TEST_SERVER_ID = 682341452184813599

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!gb ", intents=intents)

bot.remove_command("help")

@bot.check
async def testmode(ctx):
    return not TEST_MODE or ctx.guild != None and ctx.guild.id == TEST_SERVER_ID

@bot.command(name="help")
async def helpFunc(ctx, cmd: str = None):
    embed = {
        "color" : 7855479,
        "author" : {
            "name" : "Command List",
            "icon_url" : str(bot.user.avatar_url)
        },
        "fields" : []
    }
    if cmd:
        cmd = cmd.lower()
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
            await ctx.send('Invalid command, for a list of commands, use !market help')
            return
    else:
        for i in sorted(COMMAND_SET.keys()):
            if 'alias' not in COMMAND_SET[i]:
                embed['fields'].append({
                    "name" : i,
                    "value" : COMMAND_SET[i]['helpmsg']
                })
    await ctx.send(embed = discord.Embed.from_dict(embed))

COMMAND_SET = {
    'help' : {
        'helpmsg' : 'Prints out the list of commands available, !gb help <cmd> for command usage',
        'usage' : '!gb help <cmd>'
    },
    'report' : {
        'helpmsg' : 'Reports a score',
        'usage' : '!gb report <score>'
    },
    'leaderboard' : {
        'helpmsg' : 'Opens the score leaderboard (only considers already confirmed scores)',
        'usage' : '!gb leaderboard'
    },
    'lb' : {
        'alias' : 'leaderboard'
    },
    'reset' : {
        'helpmsg' : 'Resets all scores (Leaderman only command)',
        'usage' : '!gb reset'
    },
    'setscore' : {
        'helpmsg' : 'Sets the score of a user (JR+ only)',
        'usage' : '!gb setscore @target <score> <number of races>'
    },
    'raffle' : {
        'helpmsg' : 'Initiates raffle drawing (Leaderman only command)',
        'usage' : '!gb raffle'
    },
    'sfcalc' : {
        'helpmsg' : 'Simulates starforcing',
        'usage' : '!gb sfcalc <start stars> <target stars> <item level> Optional: safeguard 5/10/15 30% starcatch +2'
    },
    'sfroll' : {
        'helpmsg' : 'Simulates one roll for starforce',
        'usage' : '!gb sfroll <start stars> <target stars> <item level> Optional: safeguard 5/10/15 30% starcatch +2'
    },
    'flamecalc' : {
        'helpmsg' : 'Simulates flaming',
        'usage' : '!gb flamecalc weapon <item level> <flame score goal> <damage goal> <(m)att tier goal>\nOr: !gb flamecalc armor <item level> <flame score goal>\nOptional: rainbow, flameadvantage'
    },
    'schedule' : {
        'helpmsg' : 'Schedules an event',
        'usage' : '!gb schedule <event name> <event time (Monday,+2 for Monday, Reset + 2 hours)> <participant1> <participant2> ...'
    },
    'cancel' : {
        'helpmsg' : 'Cancels an event',
        'usage' : '!gb cancel <event name>'
    },
    'invite' : {
        'helpmsg' : 'Invites user(s) to an event (ignores already invited participants)',
        'usage' : '!gb invite <event name> <participants>'
    }
}

print("Starting Bot")

@bot.event
async def on_ready():
    print(f'Logged on as {bot.user}')
    if TEST_MODE:
        print('Test mode is on')
    await bot.change_presence(activity = discord.Game(name = 'Use "!gb help" for a list of commands'))

@bot.event
async def on_raw_reaction_add(payload):
    if TEST_MODE and payload.guild_id != TEST_SERVER_ID:
        return
    if payload.user_id == bot.user.id:
        return
    message = await bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
    if message.author == bot.user: #Event Invites
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
                        "icon_url" : str(bot.user.avatar_url)
                    },
                    "fields" : [
                        {
                            "name" : "Event Name",
                            "value" : eventName
                        },
                        {
                            "name" : "Time",
                            "value" : extrafuncs.utcToResetDelta(eventTime)
                        },
                        {
                            "name" : "Participants",
                            "value" : "None" if len(participants) == 0 else " ".join(bot.get_user(x).mention for x in participants)
                        },
                        {
                            "name" : "Pending Invites",
                            "value" : "None" if len(pending) == 0 else " ".join(bot.get_user(x).mention for x in pending)
                        }
                    ]
                }
                await message.edit(embed = discord.Embed.from_dict(embed))
    else:
        leadermanrole = discord.utils.find(lambda r: r.name == "Leader Man", message.guild.roles)
        jrrole = discord.utils.find(lambda r: r.name == "Jrs", message.guild.roles)
        if database.isPendingReport(payload.message_id) and (leadermanrole in payload.member.roles or jrrole in payload.member.roles):
            emoji = str(payload.emoji)
            if emoji == '✅':
                database.removeReport(message.id)
                try:
                    score = int(message.content.split()[2])
                    database.applyScore(message.author.id, score)
                    await message.remove_reaction('❌', bot.user)
                except:
                    await message.add_reaction('🚫')
            elif emoji == '❌':
                database.removeReport(message.id)
                await message.remove_reaction('✅', bot.user)

extensions = ["cogs.CheckPing", "cogs.Scheduler", "cogs.Calculator", "cogs.FlagRace"]

if __name__ == "__main__":
    for i in extensions:
        bot.load_extension(i)

bot.run(os.environ["token"])
