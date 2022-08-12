import datetime
import enum
from time import time
import typing
import re
import pytz
import pendulum
import discord
from discord import app_commands
from discord.ext import tasks, commands
from util import database, extrafuncs

class Weekdays(enum.Enum):
    Monday = 0
    Tuesday = 1
    Wednesday = 2
    Thursday = 3
    Friday = 4
    Saturday = 5
    Sunday = 6

class InviteView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout = None)

    @discord.ui.button(label="Accept/Unaccept Invite", style=discord.ButtonStyle.blurple, custom_id='invite_view:inviteinteractionbutton')
    async def inviteInteractionButton(self, interaction: discord.Interaction, button: discord.ui.Button):
        eventInfo = database.getEventFromInvite(interaction.message.id)
        if len(eventInfo) != 0:
            eventInfo = eventInfo[0]
        updated = False
        if database.acceptInvite(eventInfo[0], interaction.user.id):
            updated = True
        elif database.unacceptInvite(eventInfo[0], interaction.user.id):
            updated = True
        if updated:
            participants = [x[0] for x in database.getAcceptedInvites(eventInfo[0])]
            pending = [x[0] for x in database.getPendingInvites(eventInfo[0])]
            embed = interaction.message.embeds[0].to_dict()
            embed["fields"][2]["value"] = "None" if len(participants) == 0 else " ".join(interaction.guild.get_member(x).mention for x in participants)
            embed["fields"][3]["value"] = "None" if len(pending) == 0 else " ".join(interaction.guild.get_member(x).mention for x in pending)
            await interaction.response.edit_message(embed = discord.Embed.from_dict(embed))
        else:
            await interaction.response.send_message("You were not invited to this event.", ephemeral = True)

class EventTimeTransformer(app_commands.Transformer):
    async def transform(self, interaction: discord.Interaction, eventtime: str) -> typing.List[str]:
        eventtime = eventtime.upper()
        if "AM" in eventtime:
            return [x.strip() for x in eventtime.partition("AM")]
        if "PM" in eventtime:
            return [x.strip() for x in eventtime.partition("PM")]
        for index, val in enumerate(eventtime):
            if val.isalpha():
                return [eventtime[:index], eventtime[index:]]
        else:
            return [eventtime]

class ParticipantsTransformer(app_commands.Transformer):
    async def transform(self, interaction: discord.Interaction, participants: str) -> typing.Set[int]:
        output = set()
        users = [interaction.guild.get_member(int(x)) for x in re.findall(r'<@!?(\d+)>', participants)]
        roles = [interaction.guild.get_role(int(x)) for x in re.findall(r'<@&(\d+)>', participants)]
        output = set(users)
        for role in roles:
            if role.mentionable:
                for member in role.members:
                    output.add(member.id)
        return output

class Scheduler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.checkForEvents.start()

    @tasks.loop(seconds=60.0)
    async def checkForEvents(self):
        currentTime = datetime.datetime.now(datetime.timezone.utc)
        currentTime = currentTime.replace(second = 0, microsecond = 0)
        events = database.findEventsInMultiple(currentTime)
        for event in events:
            message = await self.bot.get_channel(event[4]).fetch_message(event[5])
            thread: discord.Thread = self.bot.get_channel(event[5])
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
                        "icon_url" : str(self.bot.user.avatar)
                    }
                }
                if thread == None:
                    thread = await message.create_thread(name = "Event Reminders")
                await thread.send(" ".join(self.bot.get_user(x[0]).mention for x in reminders), embed = discord.Embed.from_dict(embed))
            if timediff <= datetime.timedelta():
                view: discord.ui.View = discord.ui.View.from_message(message)
                view.clear_items()
                view.stop()
                await message.edit(view = view)
                await thread.edit(auto_archive_duration=60)
                database.deleteEvent(event[0])

    @checkForEvents.before_loop
    async def beforeStartLoopEvents(self):
        await self.bot.wait_until_ready()

    @commands.hybrid_command()
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

    @app_commands.command(description = "Schedules an event")
    @app_commands.describe(
        eventname = "Name of the event",
        weekday = "Weekday of the event", 
        eventtime = "Event time ex: +3 | 22:00EST | 12AM PST",
        participants = "List of participants, can use mentions or mentionable roles"
    )
    @commands.guild_only()
    async def schedule(self, ctx: discord.Interaction, eventname: str, weekday: Weekdays, eventtime: app_commands.Transform[typing.List[str], EventTimeTransformer], participants: app_commands.Transform[typing.Set[int], ParticipantsTransformer]):
        timezones = { # Although it is more correct to leave the standard times alone, many people don't know the difference between EST and EST
            'EST' : 'US/Eastern', 'EDT' : 'US/Eastern', 'ET' : 'US/Eastern',
            'CST' : 'US/Central', 'CDT' : 'US/Central', 'CT' : 'US/Central',
            'MST' : 'US/Mountain', 'MDT' : 'US/Mountain', 'MT' : 'US/Mountain',
            'PST' : 'US/Pacific', 'PDT' : 'US/Pacific', 'PT' : 'US/Pacific'
        }

        try:
            weekdayValue = weekday.value
            if len(eventtime) >= 2:
                splitTime = [int(x) for x in eventtime[0].split(":")]
                hour = splitTime[0]
                if len(eventtime) == 3 and eventtime[1] == "PM":
                    hour += 12
                minute = 0
                if len(splitTime) >= 2: # Seconds and further will be ignored
                    minute = splitTime[1]
                tzarg = pytz.timezone(timezones[eventtime[1].upper()]) if len(eventtime) == 2 else pytz.timezone(timezones[eventtime[2].upper()])
                today = pendulum.today(tzarg)
                daysUntil = (weekdayValue - today.weekday() + 7) % 7
                newDate = today.add(days = daysUntil, hours = hour, minutes = minute)
                eventtime = datetime.datetime.fromtimestamp(newDate.timestamp(), newDate.timezone)
            else: # UTC + 1 day
                today = datetime.datetime.now(datetime.timezone.utc).replace(hour = 0, minute = 0, second = 0, microsecond = 0)
                weekdayValue += 1
                eventtime[0] = float(eventtime[0])
                if eventtime[0] < 0:
                    weekdayValue = (weekdayValue - 1) % 7
                eventtime[0] %= 24
                daysUntil = (weekdayValue - today.weekday() + 7) % 7
                eventtime = today + datetime.timedelta(days = daysUntil, hours = eventtime[0])
        except:
            await ctx.response.send_message("Invalid time provided.", ephemeral=True)
            return

        organizer = ctx.user.id
        if eventname == "":
            await ctx.response.send_message("No event name provided", ephemeral=True)
            return
        if eventtime <= datetime.datetime.now(datetime.timezone.utc):
            await ctx.response.send_message("You cannot schedule an event in the past.")
            return
        if len(participants) == 0:
            await ctx.response.send_message("No participants provided.", ephemeral=True)
            return
        if len(participants) > 50:
            await ctx.response.send_message("Only up to 50 members can be added in an event.", ephemeral=True)
            return
        if database.eventExists(organizer, eventname):
            await ctx.response.send_message("You already have an event with the same name.", ephemeral=True)
            return
        embed = {
            "color" : 7855479,
            "author" : {
                "name" : "Event Invite",
                "icon_url" : str(self.bot.user.avatar)
            },
            "fields" : [
                {
                    "name" : "Event Name",
                    "value" : eventname
                },
                {
                    "name" : "Time",
                    "value" : f"<t:{int(eventtime.timestamp())}>"
                },
                {
                    "name" : "Participants",
                    "value" : "None"
                },
                {
                    "name" : "Pending Invites",
                    "value" : " ".join(x.mention for x in participants)
                }
            ]
        }

        await ctx.response.send_message(" ".join(x.mention for x in participants), embed = discord.Embed.from_dict(embed), view = InviteView())
        sentMsg = await ctx.original_response()
        database.createEvent(organizer, eventname, eventtime, [x.id for x in participants], sentMsg.channel.id, sentMsg.id)
        
        conflicts = database.findConflicts([x.id for x in participants], eventtime)
        if len(conflicts) != 0:
            conflictsEmbed = {
                "color" : 0xff6961,
                "author" : {
                    "name" : "Timing Conflicts Found",
                    "icon_url" : str(self.bot.user.avatar)
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

    @app_commands.command()
    @commands.guild_only()
    async def cancel(self, ctx: discord.Interaction, eventname: str):
        organizer = ctx.user.id
        if database.cancelEvent(organizer, eventname):
            await ctx.response.send_message(f'Event titled {eventname} deleted.')
        else:
            await ctx.response.send_message(f'You are not an organizer of an event titled {eventname}.')

    @commands.hybrid_command()
    @commands.guild_only()
    async def upcoming(self, ctx):
        upcomingEvents = database.getUpcoming(ctx.author.id)
        upcomingEvents.sort(key = lambda x: x[3])
        embed = {
            "color" : 7855479,
            "author" : {
                "name" : "Upcoming Events",
                "icon_url" : str(self.bot.user.avatar)
            },
            "description" : "No upcoming events" if len(upcomingEvents) == 0 else "\n".join([])
        }
        if len(upcomingEvents) == 0:
            embed["description"] = "No upcoming events"
        else:
            formattedEvents = []
            for i in upcomingEvents:
                adjustedTime = i[3].replace(tzinfo = datetime.timezone.utc)
                timediff = (adjustedTime - datetime.datetime.now(datetime.timezone.utc))
                formattedEvents.append(f"[{i[2]}](https://discord.com/channels/{ctx.guild.id}/{i[4]}/{i[5]}): <t:{int(adjustedTime.timestamp())}> (in {timediff.days * 24 + timediff.seconds//3600} hours)")
            embed["description"] = "\n".join(formattedEvents)
        await ctx.send(embed = discord.Embed.from_dict(embed))

    @commands.command()
    @commands.guild_only()
    async def invite(self, ctx, eventname: str):
        message = ctx.message
        participants = [x.id for x in message.mentions]
        if len(participants) == 0:
            await message.channel.send("No participants provided.")
            return 0
        organizer = ctx.author.id
        eventInfo = database.getEventFromName(organizer, eventname)
        if len(eventInfo) == 0:
            await ctx.send(f"You are not an organizer of an event titled {eventname}.")
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
                    "icon_url" : str(self.bot.user.avatar)
                },
                "fields" : [
                    {
                        "name" : "Event Name",
                        "value" : eventname
                    },
                    {
                        "name" : "Time",
                        "value" : f"<t:{int(eventInfo[3].timestamp())}>"
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
    
    async def cog_load(self):
        self.bot.add_view(InviteView())

async def setup(bot):
    await bot.add_cog(Scheduler(bot))
