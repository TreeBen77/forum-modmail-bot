import server
import discord, json, os, time
from discord import app_commands

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)
client.tree = app_commands.CommandTree(client)

channel_id = 123
webhook_id = 123

modmailWebhook: discord.Webhook = None

@client.event
async def on_ready():
    global webhook_id, modmailWebhook
    await client.change_presence(activity=discord.Game("DM me to contact staff!"))
    print(f"connected to Discord as {client.user}")
    await client.tree.sync()
    modmailWebhook = await client.fetch_webhook(webhook_id)

@client.event
async def on_message(message: discord.Message):
    if message.channel.type == discord.ChannelType.private and not message.author.bot and (message.content or len(message.attachments) > 0):
        try:
            with open("modmail.json", "r+") as file:
                data = json.load(file)

                thread = None
                thread_id = data["threads"].get(str(message.channel.id), False)
                if thread_id:
                    thread: discord.Thread = client.get_channel(thread_id)
                    if not thread or thread.archived: thread_id, thread = None, None
                if not thread_id and not message.author.id in data["blocked"] and not data["locked"]:
                    channel = client.get_channel(channel_id)

                    embed = discord.Embed(title=f"New Thread with {message.author}", color=0x79da00,
                        description="send a message in the thread to reply! Messages starting with `=` will be ignored and can be used for staff chatting.")
                    if message.content: embed.add_field(name="Initial Message", value=message.content)
                    embed.set_thumbnail(url=message.author.display_avatar)

                    thread, _message = await channel.create_thread(name=f"{message.author.name}-{message.author.discriminator}",
                        auto_archive_duration=10080, content="I'll cut to the chase, there's a new thread and im pinging <@&881572739536805929>, and <@&864446612449263628>. They better not say deleted role. Either of them.", embeds=[embed])
                    data["threads"][str(message.channel.id)] = thread.id
                
                    file.seek(0), file.truncate()
                    json.dump(data, file, indent=2)
                    time.sleep(4)
                
                if thread:
                    files = []
                    for attachment in message.attachments:
                        files.append(await attachment.to_file())
                    await modmailWebhook.send(message.content, files=files, username=str(message.author), avatar_url=message.author.display_avatar, thread=thread)
                    await message.add_reaction(client.get_emoji(996674435857780746))
                elif message.author.id in data["blocked"]:
                    await message.reply("<:ban_icon:999582766037467216> You're blocked from starting threads with modmail. Only staff can start a threads with you.", mention_author=False)
                elif data["locked"]:
                    await message.reply("<:timeout_icon:999583773245046884> The staff have temporary locked modmail for everyone.", mention_author=False)

                else: raise Exception("thread wasn't made!!!")
        except(Exception) as error:
            print("error while sending modmail (dm -> server):", error)
            await message.add_reaction(client.get_emoji(996674437707477074))
    elif message.channel.type == discord.ChannelType.public_thread and message.channel.parent_id == channel_id and not message.author.bot and not message.content.startswith("=") and (message.content or len(message.attachments) > 0):
        try:
            with open("modmail.json", "r+") as file:
                data = json.load(file)

                recipient = client.get_partial_messageable(list(data["threads"].keys())
                [list(data["threads"].values()).index(message.channel.id)], type=discord.ChannelType.private)

                files = []
                for attachment in message.attachments:
                    files.append(await attachment.to_file())

                if message.content:
                    await recipient.send(f"**{message.author}**: {message.content}", files=files)
                else:
                    await recipient.send(f"**{message.author}**", files=files)

                await message.add_reaction(client.get_emoji(996674435857780746))
        except(Exception) as error:
            print("error while sending modmail (server -> dm):", error)
            await message.add_reaction(client.get_emoji(996674437707477074))

def is_support_thread(interaction: discord.Interaction) -> bool:
    return interaction.channel.type == discord.ChannelType.private or (interaction.channel.type == discord.ChannelType.public_thread and interaction.channel.parent_id == channel_id)

@client.tree.command(name="close", description="closes the support thread linked to this channel.")
@app_commands.check(is_support_thread)
@app_commands.default_permissions(manage_messages=True)
async def command_close(interaction: discord.Interaction):
    if interaction.channel.type == discord.ChannelType.private:
        try:
            with open("modmail.json", "r+") as file:
                data = json.load(file)

                thread = None
                thread_id = data["threads"].get(str(interaction.channel.id), False)
                if thread_id:
                    thread: discord.Thread = client.get_channel(thread_id)
                    if not thread or thread.archived: thread_id, thread = None, None                    
                
                if thread:
                    await thread.send(f"<:delete_icon:999617707282538559> Support thread closed by **{interaction.user}**\n*tip: send another message to reopen it. this will fail if the user has opened another thread since.*")
                    await thread.edit(archived=True)
                    await interaction.response.send_message(f"<:delete_icon:999617707282538559> Support thread closed by **{interaction.user}**")
                else: raise Exception("thread no exist!!!")
        except(Exception) as error:
            print("error while closing modmail (dm -> server):", error)
            await interaction.response.send_message(f"<:error_icon:996674437707477074> Closing support thread failed!", ephemeral=True)
    else:
        try:
            with open("modmail.json", "r+") as file:
                data = json.load(file)
    
                recipient = client.get_partial_messageable(list(data["threads"].keys())
                [list(data["threads"].values()).index(interaction.channel.id)], type=discord.ChannelType.private)                
                
                if recipient:
                    await recipient.send(f"<:delete_icon:999617707282538559> Support thread closed by **{interaction.user}**")
                    await interaction.response.send_message(f"<:delete_icon:999617707282538559> Support thread closed by **{interaction.user}**\n*tip: send another message to reopen it. this will fail if the user has opened another thread since.*")
                    await interaction.channel.edit(archived=True)
                else: raise Exception("thread no exist!!!")
        except(Exception) as error:
            print("error while closing modmail (dm -> server):", error)
            await interaction.response.send_message(f"<:error_icon:996674437707477074> Closing support thread failed!", ephemeral=True)

@client.tree.command(name="open", description="Starts a thread with a user.")
@app_commands.guild_only()
@app_commands.rename(user="member")
@app_commands.describe(user="The member to start the thread with, must be in the server.")
@app_commands.default_permissions(moderate_members=True)
async def command_open(interaction: discord.Interaction, user: discord.Member):
    with open("modmail.json", "r+") as file:
        data = json.load(file)

        if user.dm_channel and user.dm_channel.id in data["threads"].keys():
            await interaction.response.send_message(f"<:error_icon:996674437707477074> a support thread is already open with this user.")
            return

        try:
            message = await user.send(f"<:mail_icon:1007939588981014600> Hey **{user.name}**! {interaction.user} from **{interaction.guild.name}** created a modmail ticket with you. Messages will appear below this and any message you send to me will automaticly be sent to them. Use the `/close` command to close this ticket.")
        except(discord.errors.Forbidden, discord.errors.HTTPException):
            await interaction.response.send_message(f"<:error_icon:996674437707477074> I don't have permission to direct message {user}. Either they aren't in this server, have their direct messages disabled or have blocked me.")
        else:
            channel = client.get_channel(channel_id)

            embed = discord.Embed(title=f"Staff-Created Thread for {message.author}", color=0x79da00,
                description="send a message in the thread to reply! Messages starting with `=` will be ignored and can be used for staff chatting.")
            embed.set_thumbnail(url=user.display_avatar)

            thread, _message = await channel.create_thread(name=f"{user.name}-{user.discriminator}",
                auto_archive_duration=10080, embeds=[embed], content=interaction.user.mention)
            data["threads"][str(message.channel.id)] = thread.id
        
            file.seek(0), file.truncate()
            json.dump(data, file, indent=2)

            class thread_jump_view(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=180)
                    self.add_item(discord.ui.Button(style=discord.ButtonStyle.url, label="Jump to Thread", url=thread.jump_url))

            await interaction.response.send_message(f"<:success_icon:996674435857780746> Modmail ticket was successfully created with **{user}**!", view=thread_jump_view())

@client.tree.context_menu(name="Open Thread")
@app_commands.guild_only()
@app_commands.default_permissions(moderate_members=True)
async def command_open_thread(interaction: discord.Interaction, user: discord.Member):
    with open("modmail.json", "r+") as file:
        data = json.load(file)

        if user.dm_channel and user.dm_channel.id in data["threads"].keys():
            await interaction.response.send_message(f"<:error_icon:996674437707477074> a support thread is already open with this user.")
            return

        try:
            message = await user.send(f"<:mail_icon:1007939588981014600> Hey **{user.name}**! {interaction.user} from **{interaction.guild.name}** created a modmail ticket with you. Messages will appear below this and any message you send to me will automaticly be sent to them. Use the `/close` command to close this ticket.")
        except(discord.errors.Forbidden, discord.errors.HTTPException):
            await interaction.response.send_message(f"<:error_icon:996674437707477074> I don't have permission to direct message {user}. Either they aren't in this server, have their direct messages disabled or have blocked me.")
        else:
            channel = client.get_channel(channel_id)

            embed = discord.Embed(title=f"Staff-Created Thread for {message.author}", color=0x79da00,
                description="send a message in the thread to reply! Messages starting with `=` will be ignored and can be used for staff chatting.")
            embed.set_thumbnail(url=user.display_avatar)

            thread, _message = await channel.create_thread(name=f"{user.name}-{user.discriminator}",
                auto_archive_duration=10080, embeds=[embed], content=interaction.user.mention)
            data["threads"][str(message.channel.id)] = thread.id
        
            file.seek(0), file.truncate()
            json.dump(data, file, indent=2)

            class thread_jump_view(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=180)
                    self.add_item(discord.ui.Button(style=discord.ButtonStyle.url, label="Jump to Thread", url=thread.jump_url))

            await interaction.response.send_message(f"<:success_icon:996674435857780746> Modmail ticket was successfully created with **{user}**!", view=thread_jump_view())

@client.tree.command(name="block", description="Blocks a member from starting support threads themselves.")
@app_commands.guild_only()
@app_commands.describe(member="The member to be blocked. Mustn't be blocked.")
@app_commands.default_permissions(moderate_members=True)
async def command_block(interaction: discord.Interaction, member: discord.User):
    with open("modmail.json", "r+") as file:
        data = json.load(file)

        if member.id in data["blocked"]:
            await interaction.response.send_message(f"<:error_icon:996674437707477074> **{member}** is already blocked. *tip: use `/unblock` to unblock them*")
            return

        data["blocked"].append(member.id)

        file.seek(0)
        file.truncate()
        json.dump(data, file, indent=2)
    await interaction.response.send_message(f"<:success_icon:996674435857780746> **{member}** has been blocked.")

@client.tree.command(name="unblock", description="Unblocks a member so they can start support threads.")
@app_commands.guild_only()
@app_commands.describe(member="The member to be unblocked. Must be blocked.")
@app_commands.default_permissions(moderate_members=True)
async def command_unblock(interaction: discord.Interaction, member: discord.User):
    with open("modmail.json", "r+") as file:
        data = json.load(file)

        if not member.id in data["blocked"]:
            await interaction.response.send_message(f"<:error_icon:996674437707477074> **{member}** isn't blocked.")
            return

        data["blocked"].remove(member.id)

        file.seek(0)
        file.truncate()
        json.dump(data, file, indent=2)
    await interaction.response.send_message(f"<:success_icon:996674435857780746> **{member}** has been unblocked! :D")

@client.tree.command(name="lock", description="Toggles wether modmail tickets can be created or not. Useful for raids.")
@app_commands.guild_only()
@app_commands.default_permissions(manage_guild=True)
async def command_lock(interaction: discord.Interaction):
    with open("modmail.json", "r+") as file:
        data = json.load(file)

        data["locked"] = not data["locked"]

        file.seek(0)
        file.truncate()
        json.dump(data, file, indent=2)
    if data["locked"] == True:
        await interaction.response.send_message(f"<:success_icon:996674435857780746> Modmail has been disabled for EVERYONE. *tip: use the `/lock` command again to reenable it.*")
    else:
        await interaction.response.send_message(f"<:success_icon:996674435857780746> Modmail has been reenabled.")

@client.tree.context_menu(name="Toggle Modmail Block")
@app_commands.guild_only()
@app_commands.default_permissions(moderate_members=True)
async def command_toggle_block(interaction: discord.Interaction, user: discord.User):
    with open("modmail.json", "r+") as file:
        data = json.load(file)

        if user.id in data["blocked"]:
            data["blocked"].remove(user.id)

            file.seek(0)
            file.truncate()
            json.dump(data, file, indent=2)
            await interaction.response.send_message(f"<:success_icon:996674435857780746> **{user}** has been unblocked.")
        else:
            data["blocked"].append(user.id)

            file.seek(0)
            file.truncate()
            json.dump(data, file, indent=2)
            await interaction.response.send_message(f"<:success_icon:996674435857780746> **{user}** has been blocked.")

@command_close.error
async def experiment_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if type(error) == app_commands.errors.CheckFailure:
        await interaction.response.send_message(f"<:error_icon:996674437707477074> This channel isn't linked to a support thread.", ephemeral=True)
    else:
        await interaction.response.send_message(f"<insert concrete sound here> https://tenor.com/view/slow-thumbs-down-thumbs-down-thumbs-up-thumbs-down-gladiator-thumbs-down-alan-spicer-gif-17086415\n{error}", ephemeral=True)

client.run(os.environ["DISCORD_CLIENT"])
