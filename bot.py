import os, math, asyncio, random, subprocess, datetime, traceback, sys
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
    inTestServer = ctx.guild != None and ctx.guild.id == TEST_SERVER_ID
    return inTestServer if TEST_MODE else not inTestServer

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        pass
    else:
        print(f'Ignoring exception in command {ctx.command}:', file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

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
    'reminderconfig' : {
        'helpmsg' : 'Configures what times reminders are triggered for a user. Can only be set in 15 minute intervals and up to a maximum of 24 hours away.',
        'usage' : '!gb reminderconfig <time1> <time2> <time3> ...\nExample: !gb reminderconfig .25 24'
    },
    'upcoming' : {
        'helpmsg' : 'Lists upcoming events that have been accepted',
        'usage' : '!gb upcoming'
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

extensions = ["cogs.CheckPing", "cogs.Scheduler", "cogs.Calculator", "cogs.FlagRace"]

if __name__ == "__main__":
    for i in extensions:
        bot.load_extension(i)

bot.run(os.environ["token"])
