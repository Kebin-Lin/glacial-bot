import asyncio, datetime
import discord
from discord.ext import tasks, commands
from util import extrafuncs

STATUS_CHANNEL_ID = 793333996380487682
STATUS_MESSAGE_ID = 793345605484544030

pingHistory = [[] for x in range(len(extrafuncs.CHANNEL_LIST))]

class CheckPing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.checkPing.start()

    @tasks.loop(seconds=10.0)
    async def checkPing(self):
        tasks = []
        for i in extrafuncs.CHANNEL_LIST:
            tasks.append(self.bot.loop.create_task(extrafuncs.ping(self.bot.loop, i)))
        await asyncio.wait(tasks)
        pings = [x.result() for x in tasks]
        if len(pingHistory[0]) == 60: #Over 10 minutes
            for i in pingHistory:
                i.pop(0)
        for i in range(len(pings)):
            pingHistory[i].append(pings[i])
        message = None
        output = extrafuncs.serverStatusSummary(pingHistory)
        while True:
            try:
                message = await self.bot.get_channel(STATUS_CHANNEL_ID).fetch_message(STATUS_MESSAGE_ID)
                await message.edit(content = "```" + output + f"\nTimestamp: {str(datetime.datetime.now(datetime.timezone.utc))} UTC```")
                break
            except discord.errors.DiscordServerError:
                print("Failed to update the server status tracker. Trying again.")
                continue

    @checkPing.before_loop
    async def beforeStartLoopPing(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(CheckPing(bot))