import asyncio
import discord
import random
from discord.ext import commands
from util import database

class FlagRace(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def report(self, ctx, score: int):
        database.createReport(ctx.message.id, ctx.channel.id)
        await ctx.message.add_reaction('✅')
        await ctx.message.add_reaction('❌')
    
    @report.error
    async def reportError(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("No score supplied")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("Invalid score supplied")
        else:
            print(error)

    @commands.command(aliases=['lb'])
    async def leaderboard(self, ctx):
        message = ctx.message
        embed = {
            "color" : 7855479,
            "author" : {
                "name" : "Leaderboards",
                "icon_url" : str(self.bot.user.avatar)
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
            await ctx.send(embed = discord.Embed.from_dict(embed))
            return

        async def setupLeaderboard(embed, scores):
            placing = offset + 1
            embed['fields'] = []
            formattedPlacings = []
            for i in scores[offset : offset + 10]:
                formattedPlacings.append(f"{placing}. **{str(await self.bot.fetch_user(i[0]))}** - {i[1]} points over {i[2]} race(s)")
                placing += 1
            embed['fields'].append({
                'name' : '\u200b',
                'value' : '\n'.join(formattedPlacings)
            })
        
        await setupLeaderboard(embed, scores)
        sentMsg = await ctx.send(embed = discord.Embed.from_dict(embed))

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
                        self.bot.wait_for('reaction_add', check = check),
                        self.bot.wait_for('reaction_remove', check = check)
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

    @commands.command()
    async def reset(self, ctx):
        role = discord.utils.find(lambda r: r.name == "Leader Man", ctx.guild.roles)
        if role in ctx.author.roles:
            database.reset()
            await ctx.message.add_reaction('✅')
        else:
            await ctx.send('You do not have the role for this command')

    @commands.command()
    async def setscore(self, ctx):
        message = ctx.message
        splitcontent = message.content.split()
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

    @commands.command()
    async def raffle(self, ctx):
        message = ctx.message
        role = discord.utils.find(lambda r: r.name == "Leader Man", message.guild.roles)
        if role not in message.author.roles:
            await message.channel.send('You do not have the role for this command')
            return
        
        embed = {
            "color" : 7855479,
            "author" : {
                "name" : "Raffle",
                "icon_url" : str(self.bot.user.avatar)
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
            await ctx.send('Less than three people are elegible for the raffle')
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

        sentMsg = await ctx.send(embed = discord.Embed.from_dict(embed))

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
                        self.bot.wait_for('reaction_add', check = check),
                        self.bot.wait_for('reaction_remove', check = check)
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
                        embed['fields'][2 - numRevealed]['value'] = str(self.bot.get_user(winners[2 - numRevealed]))
                        numRevealed += 1
                        await sentMsg.edit(embed = discord.Embed.from_dict(embed))
                    else:
                        waitForReaction = False
                        embed['color'] = 0xff6961
                        await sentMsg.edit(embed = discord.Embed.from_dict(embed))

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        if message.author != self.bot.user:
            leadermanrole = discord.utils.find(lambda r: r.name == "Leader Man", message.guild.roles)
            jrrole = discord.utils.find(lambda r: r.name == "Jrs", message.guild.roles)
            if database.isPendingReport(payload.message_id) and (leadermanrole in payload.member.roles or jrrole in payload.member.roles):
                emoji = str(payload.emoji)
                if emoji == '✅':
                    database.removeReport(message.id)
                    try:
                        score = int(message.content.split()[2])
                        database.applyScore(message.author.id, score)
                        await message.remove_reaction('❌', self.bot.user)
                    except:
                        await message.add_reaction('🚫')
                elif emoji == '❌':
                    database.removeReport(message.id)
                    await message.remove_reaction('✅', self.bot.user)

async def setup(bot):
    await bot.add_cog(FlagRace(bot))