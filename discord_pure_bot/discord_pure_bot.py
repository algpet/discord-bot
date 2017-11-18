import asyncio

import discord

import digicoins.libs.bittrex_api_copy as bittrex
import wall_calculator
from presets import test_presets

discordClient = discord.Client()


@discordClient.event
async def on_ready():
    print('Logged in as', discordClient.user.name, discordClient.user.id)


def update_pair_volumes():
    try:
        result = bittrexClient.get_market_summaries()['result']
        for market in result:
            market_name = market['MarketName']
            new_value = market['BaseVolume']
            if market_name not in HISTORY:
                HISTORY[market_name] = []
            HISTORY[market_name].insert(0,new_value)
    except Exception:
        for market_name in HISTORY:
            new_value = HISTORY[market_name][0]
            HISTORY[market_name].insert(0, new_value)


async def volume_changes():
    await discordClient.wait_until_ready()

    while not discordClient.is_closed:
        update_pair_volumes()

        message = ""

        for pair in HISTORY:

            if not (pair.startswith("BTC-") or pair.endswith("-BTC")):
                continue

            pair_history = HISTORY[pair]
            tracked = False
            for time_frame,threshold in presets["tracked_timeframes"].items():
                if len(pair_history) <= time_frame:
                    continue

                try:
                    new = pair_history[0]
                    old = pair_history[time_frame]
                    change = (new - old) / old
                    change_prc = change * 100
                    counter_ccy = pair.split("-")[1]

                    if change < threshold:
                        continue
                    tracked = True
                    message += "```\n[{}]\n" \
                               "Vol. Change: {:.02f}%\n"\
                               "Time Period: {} minutes\n\n"\
                               "{}'s volume has risen {:.02f}% in the last {} minutes, this could be signs of mass accumulation, trade accordingly.```\n"\
                        .format(pair,change_prc,time_frame,counter_ccy,change_prc,time_frame)
                except Exception as problem:
                    await discordClient.send_message(channel, "oops I got exception " + str(problem))

            if tracked:
                HISTORY[pair] = []
            if len(HISTORY[pair]) >= 1000:
                HISTORY[pair] = HISTORY[pair][:100]

        if message != "":
            print(message)
            try:
                for channel in CHANNELS:
                    await discordClient.send_message(channel, message)
            except Exception as problem:
                print("unable to send message",problem)
        else:
            print("no big deals ..")
        await asyncio.sleep(60) # task runs every 60 seconds


@discordClient.event
async def on_message(message):

    if message.author.id == presets["bot-id"]:
        return

    try:
        #print("new message sent by ", message.author.id, message.author , "channel", message.channel, "text" , message.content)
        if message.channel.is_private:
            print("private message ", message.channel, message.channel.is_private)

            if message.author.id in presets["bot-admin-ids"]:
                await discordClient.send_message(message.channel, "yes my lord !")
                if not message.content.startswith("!"):
                    print("not a command")
                    return

                if message.content.startswith("!walls"):
                    answer = wallCalculator.walls(message)
                    if answer is not None:
                        await discordClient.send_message(message.channel,answer)

                if message.content.startswith("!tf"):
                    s = message.content[4:].upper()
                    data = s.split(",")
                    print(data)
                    if len(data) == 2:
                        minutes = int(data[0])
                        percent = float(data[1])
                        presets["tracked_timeframes"][minutes] = percent
                    elif len(data) == 1:
                        if int(data[0]) in presets["tracked_timeframes"]:
                            del presets["tracked_timeframes"][int(data[0])]
                    await discordClient.send_message(message.channel, " new timetable " + str(presets["tracked_timeframes"]))

                elif message.content.startswith("!pair"):
                    s = message.content[6:].upper()
                    if not s in presets["tracked_pairs"]:
                        presets["tracked_pairs"].append(s)
                        await discordClient.send_message(message.channel,"bot will now track " + s)
                        print("bot will now track",s)
                elif message.content.startswith("!unpair"):
                    s = message.content[8:].upper().strip(" ")
                    if not s in presets["tracked_pairs"]:
                        await discordClient.send_message(message.channel, s + " is not there")
                    else:
                        presets["tracked_pairs"].remove(s)
                        await discordClient.send_message(message.channel, "bot will not track " + s + " anymore")

                print("processed")
            else:
                pass
        else:
            if message.content.startswith("!walls"):
                answer = wallCalculator.walls(message)
                if answer is not None:
                    await discordClient.send_message(message.channel, answer)

                print("public channel message",message.channel,message.channel.id)
    except Exception as problem:
        print("error while processing message ", message)



bittrexClient = bittrex.Bittrex('123key123zzuegflsrksfyousufferbutwhy', 'meowwhoiscareaboutthisbotbutstillhavetoaddsecretkey')
wallCalculator = wall_calculator.WallCalculator()
presets = test_presets
CHANNELS = [discord.Object(id=id) for id in presets["channel_ids"]]
HISTORY = {}
discordClient.loop.create_task(volume_changes())
discordClient.run(presets['bot-token'])

