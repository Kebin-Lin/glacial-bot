import asyncio
import discord
from discord.ext import commands
from util import extrafuncs

class Calculator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def sfcalc(self, ctx, numTrials = 1000):
        # try:
            message = ctx.message
            splitcontent = message.content.split()
            start = int(splitcontent[2])
            if (start < 0 or start > 21):
                await message.channel.send('Invalid starting star')
                return
            goal = int(splitcontent[3])
            if (goal < 0 or goal > 22):
                await message.channel.send('Invalid goal')
                return
            equiplv = int(splitcontent[4])
            if (equiplv < 1 or equiplv > 250):
                await message.channel.send('Invalid item level')
                return
            optionalArgs = splitcontent[5:]
            discount = 1
            safeguard = int("safeguard" in optionalArgs)
            fivetenfifteen = int("5/10/15" in optionalArgs)
            thirtyperc = int("30%" in optionalArgs)
            starcatch = int("starcatch" in optionalArgs)
            plustwo = int("+2" in optionalArgs)
            process = await asyncio.create_subprocess_shell(f"./sfcalc {start} {goal} {equiplv} {numTrials} {discount} {safeguard} {fivetenfifteen} {thirtyperc} {starcatch} {plustwo}", stdout = asyncio.subprocess.PIPE)
            stdout, stderr = await process.communicate()
            avgMeso, avgBooms, noBoomRate, mesoPercentiles, boomPercentiles = stdout.decode('utf-8').strip().split("\n")
            activeOptions = []
            if (safeguard):
                activeOptions.append("Safeguard")
            if (fivetenfifteen):
                activeOptions.append("5/10/15")
            if (thirtyperc):
                activeOptions.append("30%")
            if (starcatch):
                activeOptions.append("Starcatch")
            if (plustwo):
                activeOptions.append("+2 Stars")
            if len(activeOptions) == 0:
                activeOptions.append("None")
            embed = {
                "color" : 7855479,
                "author" : {
                    "name" : "Star Force Calculator",
                    "icon_url" : str(self.bot.user.avatar_url)
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
                formattedMesoPercentiles = ''
                for i in (extrafuncs.shortenNum(int(x)) for x in mesoPercentiles.split()):
                    formattedMesoPercentiles += i + (' ' * (8 - len(i)))
                formattedBoomPercentiles = ''
                for i in boomPercentiles.split():
                    formattedBoomPercentiles += i + (' ' * (8 - len(i)))
                embed['fields'].append({
                    "name" : "Cost Percentiles",
                    "value" : f"__Meso__\n```75%     85%     95%\n{formattedMesoPercentiles}```\n__Booms__```75%     85%     95%\n{formattedBoomPercentiles}```"
                })
            await message.channel.send(embed = discord.Embed.from_dict(embed))
            return
        # except:
        #     await message.channel.send('Invalid input')
        #     return

    @commands.command(name="sfcalc")
    async def sfcalcWrapper(self, ctx):
        await self.sfcalc(ctx)

    @commands.command()
    async def sfroll(self, ctx):
        await self.sfcalcFunc(ctx, numTrials = 1)

    @commands.command()
    async def flamecalc(self, ctx):
        # try:
            numTrials = 1000
            message = ctx.message
            splitcontent = message.content.split()
            equipType = splitcontent[2]
            if (equipType != 'weapon' and equipType != 'armor'):
                await message.channel.send('Invalid item type')
                return
            equiplv = int(splitcontent[3])
            if (equiplv < 1 or equiplv > 200):
                await message.channel.send('Invalid item level')
                return
            flameTarget = int(splitcontent[4])
            if (flameTarget < 0):
                await message.channel.send('Invalid flame score goal')
                return
            damageTarget = int(splitcontent[5]) if equipType == 'weapon' else 0
            if (damageTarget < 0):
                await message.channel.send('Invalid damage goal')
                return
            attTarget = int(splitcontent[6]) if equipType == 'weapon' else 0
            if (attTarget < 0):
                await message.channel.send('Invalid (M)ATT goal')
                return
            optionalArgs = splitcontent[7 if equipType == 'weapon' else 5:]
            userainbow = int("rainbow" in optionalArgs)
            advantage = int("flameadvantage" in optionalArgs)
            process = await asyncio.create_subprocess_shell(f"./flamecalc {equiplv} {advantage} {flameTarget} {damageTarget} {attTarget} {numTrials} {userainbow}", stdout = asyncio.subprocess.PIPE)
            procmessage = await message.channel.send('Processing...')
            stdout, stderr = await process.communicate()
            avgUsage, usagePercentiles = stdout.decode('utf-8').strip().split("\n")
            if (avgUsage == '-1'):
                await procmessage.edit(content = 'Goal too unlikely or impossible (no desired result in 100k flames used for at least one trial)')
                return
            activeOptions = []
            if (advantage):
                activeOptions.append("Flame Advantage")
            if (userainbow):
                activeOptions.append("Use Rainbow Flames")
            if len(activeOptions) == 0:
                activeOptions.append("None")
            embed = {
                "color" : 7855479,
                "author" : {
                    "name" : "Flame Calculator",
                    "icon_url" : str(self.bot.user.avatar_url)
                },
                "fields" : [
                    {
                        "name" : "Item Type",
                        "value" : equipType.capitalize(),
                        "inline" : True
                    },
                    {
                        "name" : "Flame Score Goal",
                        "value" : flameTarget,
                        "inline" : True
                    }
                ]
            }
            if (equipType == 'weapon') :
                embed['fields'].extend([
                    {
                        "name" : "Damage Goal",
                        "value" : damageTarget,
                        "inline" : True
                    },
                    {
                        "name" : "(M)ATT Tier Goal",
                        "value" : attTarget,
                        "inline" : True
                    }
                ])
            embed['fields'].extend([
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
                    "name" : "Average Flames Consumed",
                    "value" : avgUsage
                }
            ])
            formattedUsagePercentiles = ''
            for i in usagePercentiles.split():
                formattedUsagePercentiles += i + (' ' * (8 - len(i)))
            embed['fields'].append({
                "name" : "Usage Percentiles",
                "value" : f"```75%     85%     95%\n{formattedUsagePercentiles}```"
            })
            await procmessage.edit(content = "", embed = discord.Embed.from_dict(embed))
            return
        # except:
        #     await message.channel.send('Invalid input')
        #     return

def setup(bot):
    bot.add_cog(Calculator(bot))