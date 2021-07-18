import datetime
import discord
from discord.ext import tasks, commands
from util import database, extrafuncs

class Scheduler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.checkForEvents.start()

    @tasks.loop(seconds=60.0)
    async def checkForEvents(self):
        currentTime = datetime.datetime.now(datetime.timezone.utc)
        currentTime = currentTime.replace(second = 0, microsecond = 0)
        events = database.findEventsInMultiple(currentTime)
        for event in events:
            timediff = event[6]
            reminders = database.getReminders(event[0], timediff)
            if len(reminders) != 0:
                titlestring = []
                if timediff.days == 1:
                    titlestring.append("1 Day")
                else:
                    if timediff.seconds >= 3600:
                        titlestring.append(f"{timediff.seconds//3600} Hour")
                    if timediff.seconds % 3600 != 0:
                        titlestring.append(f"{timediff.seconds%3600//60} Minute")
                embed = {
                    "color" : 7855479,
                    "author" : {
                        "name" : ", ".join(titlestring) + " Event Reminder" if len(titlestring) != 0 else "Event Reminder",
                        "icon_url" : str(self.bot.user.avatar_url)
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
                embed["fields"][0]["value"] = event[2]
                embed["fields"][1]["value"] = extrafuncs.utcToResetDelta(event[3])
                embed["fields"][2]["value"] = " ".join(self.bot.get_user(x[0]).mention for x in database.getAcceptedInvites(event[0]))
                message = await self.bot.get_channel(event[4]).fetch_message(event[5])
                await message.reply(" ".join(self.bot.get_user(x[0]).mention for x in reminders), embed = discord.Embed.from_dict(embed))
            if timediff <= datetime.timedelta():
                database.deleteEvent(event[0])

    @checkForEvents.before_loop
    async def beforeStartLoopEvents(self):
        await self.bot.wait_until_ready()

    @commands.command()
    @commands.guild_only()
    async def reminderconfig(self, ctx, times: commands.Greedy[float]):
        times = [i for i in times if i % .25 == 0 and i >= 0 and i <= 24]
        responsestr = None
        if len(times) == 0:
            responsestr = f'No reminders will be sent for you.'
        else:
            responsestr = f"Reminder(s) set for {', '.join(str(x) for x in times[:-1])}{',' if len(times) > 2 else ''}{' and ' if len(times) > 1 else ''}{times[-1]} hour(s) before events."
        times = [datetime.timedelta(hours=i) for i in times]
        if database.updateReminderSettings(ctx.author.id, times):
            await ctx.send(responsestr)

    @commands.command()
    @commands.guild_only()
    async def schedule(self, ctx, eventName: str, eventTime: str):
        weekdays = {
            'monday' : 0, 'mon' : 0, 'tuesday' : 1, 'tues' : 1, 'tue' : 1, 'wednesday' : 2, 'wed' : 2, 'thursday' : 3, 'thurs' : 3, 'thu' : 3,
            'friday' : 4, 'fri' : 4, 'saturday' : 5, 'sat' : 5, 'sunday' : 6, 'sun' : 6
        }
        message = ctx.message
        organizer = ctx.author.id
        if eventName == "":
            await ctx.send("No event name provided")
            return
        eventTime = eventTime.split(",")
        eventTime[0] = eventTime[0].lower()
        if eventTime[0] not in weekdays:
            await ctx.send("Invalid day provided.")
            return
        try:
            eventTime[1] = float(eventTime[1])
        except:
            await ctx.send("Invalid time provided.")
            return
        eventTime[0] = weekdays[eventTime[0]]
        today = datetime.datetime.now(datetime.timezone.utc)
        today = today.replace(hour = 0, minute = 0, second = 0, microsecond = 0)
        daysUntil = (((eventTime[0] + 1) % 7) - today.weekday()) % 7
        eventTime = today + datetime.timedelta(days = daysUntil, hours = eventTime[1])
        eventTime = eventTime.replace(second = 0, microsecond = 0)
        if eventTime <= datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes = 15):
            if eventTime <= datetime.datetime.now(datetime.timezone.utc) and daysUntil <= 1:
                eventTime = eventTime + datetime.timedelta(days = 7)
            else:
                await ctx.send("You cannot schedule an event that is 15 minutes or less away.")
                return
        participants = set(x.id for x in message.mentions).union(
                    set(member.id for role in message.role_mentions
                        for member in role.members)
                    )
        if len(participants) == 0:
            await ctx.send("No participants provided.")
            return
        if database.eventExists(organizer, eventName):
            await ctx.send("You already have an event with the same name.")
            return
        embed = {
            "color" : 7855479,
            "author" : {
                "name" : "Event Invite",
                "icon_url" : str(self.bot.user.avatar_url)
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
                    "value" : "None"
                },
                {
                    "name" : "Pending Invites",
                    "value" : " ".join(self.bot.get_user(x).mention for x in participants)
                }
            ]
        }
        sentMsg = await ctx.send(embed = discord.Embed.from_dict(embed))
        database.createEvent(organizer, eventName, eventTime, participants, sentMsg.channel.id, sentMsg.id)
        await sentMsg.add_reaction('✅')
        conflicts = database.findConflicts(participants, eventTime)
        if len(conflicts) != 0:
            conflictsEmbed = {
                "color" : 0xff6961,
                "author" : {
                    "name" : "Timing Conflicts Found",
                    "icon_url" : str(self.bot.user.avatar_url)
                },
                "description" : " ".join(self.bot.get_user(x[0]).mention for x in conflicts)
            }
            await ctx.send(embed = discord.Embed.from_dict(conflictsEmbed))

    @schedule.error
    async def scheduleError(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Missing field(s). Usage: !gb schedule <event name> <event time (Monday,+2 for Monday, Reset + 2 hours)> <participant1> <participant2> ...")
        else:
            print(error)

    @commands.command()
    @commands.guild_only()
    async def cancel(self, ctx, eventName: str):
        organizer = ctx.author.id
        if database.cancelEvent(organizer, eventName):
            await ctx.message.add_reaction('✅')
        else:
            await ctx.send(f'You are not an organizer of an event titled {eventName}.')

    @commands.command()
    @commands.guild_only()
    async def upcoming(self, ctx):
        upcomingEvents = database.getUpcoming(ctx.author.id)
        embed = {
            "color" : 7855479,
            "author" : {
                "name" : "Upcoming Events",
                "icon_url" : str(self.bot.user.avatar_url)
            },
            "description" : "No upcoming events" if len(upcomingEvents) == 0 else "\n".join([])
        }
        if len(upcomingEvents) == 0:
            embed["description"] = "No upcoming events"
        else:
            formattedEvents = []
            for i in upcomingEvents:
                timediff = (i[3] - datetime.datetime.now())
                formattedEvents.append(f"[{i[2]}](https://discord.com/channels/{ctx.guild.id}/{i[4]}/{i[5]}): {extrafuncs.utcToResetDelta(i[3])} (in {timediff.days * 24 + timediff.seconds//3600} hours)")
            embed["description"] = "\n".join(formattedEvents)
        await ctx.send(embed = discord.Embed.from_dict(embed))

    @commands.command()
    @commands.guild_only()
    async def invite(self, ctx, eventName: str):
        message = ctx.message
        participants = [x.id for x in message.mentions]
        if len(participants) == 0:
            await message.channel.send("No participants provided.")
            return 0
        organizer = ctx.author.id
        eventInfo = database.getEventFromName(organizer, eventName)
        if len(eventInfo) == 0:
            await ctx.send(f"You are not an organizer of an event titled {eventName}.")
            return
        eventInfo = eventInfo[0]
        numAdded = database.addInvite(organizer, eventInfo[0], participants)
        if numAdded != 0:
            originalInvite = await self.bot.get_channel(eventInfo[4]).fetch_message(eventInfo[5])
            await originalInvite.reply(f"{numAdded} new participant(s) invited.\nClick on the reply to jump to the original invite.")
            #Update invite message
            participants = [x[0] for x in database.getAcceptedInvites(eventInfo[0])]
            pending = [x[0] for x in database.getPendingInvites(eventInfo[0])]
            embed = {
                "color" : 7855479,
                "author" : {
                    "name" : "Event Invite",
                    "icon_url" : str(self.bot.user.avatar_url)
                },
                "fields" : [
                    {
                        "name" : "Event Name",
                        "value" : eventName
                    },
                    {
                        "name" : "Time",
                        "value" : extrafuncs.utcToResetDelta(eventInfo[3])
                    },
                    {
                        "name" : "Participants",
                        "value" : "None" if len(participants) == 0 else " ".join(self.bot.get_user(x).mention for x in participants)
                    },
                    {
                        "name" : "Pending Invites",
                        "value" : "None" if len(pending) == 0 else " ".join(self.bot.get_user(x).mention for x in pending)
                    }
                ]
            }
            await originalInvite.edit(embed = discord.Embed.from_dict(embed))
        else:
            await message.channel.send("No new participants invited.")
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        emoji = str(payload.emoji)
        if message.author == self.bot.user and emoji == '✅': #Event Invites
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
                            "icon_url" : str(self.bot.user.avatar_url)
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
                                "value" : "None" if len(participants) == 0 else " ".join(self.bot.get_user(x).mention for x in participants)
                            },
                            {
                                "name" : "Pending Invites",
                                "value" : "None" if len(pending) == 0 else " ".join(self.bot.get_user(x).mention for x in pending)
                            }
                        ]
                    }
                    await message.edit(embed = discord.Embed.from_dict(embed))
        
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        emoji = str(payload.emoji)
        if message.author == self.bot.user and emoji == '✅': #Event Invites
            eventInfo = database.getEventFromInvite(message.id)
            if len(eventInfo) != 0:
                eventInfo = eventInfo[0]
                eventName = eventInfo[2]
                eventTime = eventInfo[3]
                if database.unacceptInvite(eventInfo[0], payload.user_id): #Valid user unaccepted invite
                    participants = [x[0] for x in database.getAcceptedInvites(eventInfo[0])]
                    pending = [x[0] for x in database.getPendingInvites(eventInfo[0])]
                    embed = {
                        "color" : 7855479,
                        "author" : {
                            "name" : "Event Invite",
                            "icon_url" : str(self.bot.user.avatar_url)
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
                                "value" : "None" if len(participants) == 0 else " ".join(self.bot.get_user(x).mention for x in participants)
                            },
                            {
                                "name" : "Pending Invites",
                                "value" : "None" if len(pending) == 0 else " ".join(self.bot.get_user(x).mention for x in pending)
                            }
                        ]
                    }
                    await message.edit(embed = discord.Embed.from_dict(embed))

def setup(bot):
    bot.add_cog(Scheduler(bot))