

#  _______________________________      __                     .__              
# /  _____/\______   \__    ___/  \    /  \_____ ______________|__| ___________ 
#/   \  ___ |     ___/ |    |  \   \/\/   /\__  \\_  __ \_  __ \  |/  _ \_  __ \
#\    \_\  \|    |     |    |   \        /  / __ \|  | \/|  | \/  (  <_> )  | \/
# \______  /|____|     |____|    \__/\  /  (____  /__|   |__|  |__|\____/|__|   
#        \/                           \/        \/                              


import discord
from discord.ext import commands
from discord.ui import Button, View
from collections import defaultdict
import time
from googletrans import Translator
from datetime import timedelta

# Bot setup
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Role required to create polls
POLL_CREATOR_ROLE = "Poll Creator"  # this should be the name of your poll creator role

# Admin role check
ADMIN_ROLE = "Admin"  # this should be the name of your admin role

user_messages = defaultdict(list)

# Bot ready
@bot.event
async def on_ready():
    print(f"Bot is ready. Logged in as {bot.user} Made by -> GPTWarrior")


# Detect repeated messages and ban spammers
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = message.author.id
    current_time = time.time()
    user_messages[user_id].append((message.content, current_time))

    # Keep only recent messages (2 seconds)
    user_messages[user_id] = [
        (msg, timestamp) for msg, timestamp in user_messages[user_id]
        if current_time - timestamp <= 2
    ]

    # Check for spam warnings (3 messages)
    if len(user_messages[user_id]) == 3 and len(set(msg for msg, _ in user_messages[user_id])) == 1:
        await message.channel.send(
            f"{message.author.mention}, stop spamming or you may get banned."
        )

    # Check for spam bans (5 messages)
    if len(user_messages[user_id]) >= 5 and len(set(msg for msg, _ in user_messages[user_id])) == 1:
        await message.channel.send(f"{message.author.mention} has been banned for spamming!")
        await message.guild.ban(message.author, reason="Spamming the same message repeatedly.")
        user_messages.pop(user_id, None)

    await bot.process_commands(message)


# Warn a user
@bot.command()
async def warn(ctx, user_id: int):
    """Warn a user with a reason and send them a DM."""
    
    # Check if the user using the command has the admin role
    admin_role = discord.utils.get(ctx.guild.roles, name=ADMIN_ROLE)
    if admin_role not in ctx.author.roles:
        await ctx.send("You don't have the required permissions to warn users!")
        return

    # Try to fetch the user by ID
    try:
        user_to_warn = await ctx.guild.fetch_member(user_id)
    except discord.NotFound:
        await ctx.send(f"User with ID {user_id} not found.")
        return
    
    # Ask for reason
    await ctx.send(f"Please provide the reason for warning {user_to_warn.mention}:")
    reason_msg = await bot.wait_for("message", check=lambda m: m.author == ctx.author)
    reason = reason_msg.content
    
    try:
        await user_to_warn.send(
            f"{user_to_warn.mention}, you have been warned by an admin(🤓) \n\nReason: {reason}"
        )
        await ctx.send(f"User {user_to_warn.mention} has been warned. A DM with the reason has been sent.")
    except discord.Forbidden:
        await ctx.send(f"I can't send a DM to {user_to_warn.mention}. Please ensure their DMs are open.")
    

# Get a random joke
@bot.command()
async def joke(ctx):
    await ctx.send("Why don't skeletons fight each other? They don't have the guts!")


# Roll a dice
@bot.command()
async def roll(ctx):
    from random import randint
    await ctx.send(f"You rolled a {randint(1, 6)}!")


# Check bot latency
@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! Latency: {round(bot.latency * 1000)}ms")


# server information
@bot.command()
async def serverinfo(ctx):
    guild = ctx.guild
    await ctx.send(f"Server name: {guild.name}\nTotal members: {guild.member_count}")


# List all available commands
@bot.command()
async def commands(ctx):
    command_list = """
**Available Commands:**
1. **!joke** - Get a random joke.
2. **!roll** - Roll a dice and return a random number.
3. **!ping** - Check the bot's latency.
4. **!serverinfo** - Display information about the server.
5. **!poll** - Create a poll (requires Poll Creator role).
6. **!warn <user_id>** - Warn a user and send a DM with the reason.
7. **!commands** - List all available commands.
"""
    await ctx.send(command_list)


@bot.command()
async def poll(ctx):
    """
    Command to create a poll with Yes and No buttons.
    Poll question and duration are taken as input from the chat.
    """
    # Check if the user has the required role
    required_role = discord.utils.get(ctx.guild.roles, name=POLL_CREATOR_ROLE)
    if required_role not in ctx.author.roles:
        await ctx.send("You don't have the required role to create polls!")
        return

    # poll question
    await ctx.send("Please enter your poll question:")
    question_msg = await bot.wait_for("message", check=lambda m: m.author == ctx.author)
    question = question_msg.content

    # poll duration
    await ctx.send("Please enter the poll duration in seconds (default is 60 seconds):")
    duration_msg = await bot.wait_for("message", check=lambda m: m.author == ctx.author)
    duration_str = duration_msg.content

    # default poll time
    duration = int(duration_str) if duration_str.isdigit() else 60

    # Create the poll embed
    embed = discord.Embed(
        title="📊 Poll",
        description=question,
        color=discord.Color.blue(),
    )
    embed.set_footer(text=f"Poll created by {ctx.author.display_name}")

    # buttons
    yes_button = Button(label="Yes", style=discord.ButtonStyle.success, custom_id="poll_yes")
    no_button = Button(label="No", style=discord.ButtonStyle.danger, custom_id="poll_no")

    view = View()
    view.add_item(yes_button)
    view.add_item(no_button)

    # Store vote counts
    view.vote_counts = {"Yes": 0, "No": 0}
    view.voters = set() 

    # Button callbacks
    async def yes_callback(interaction: discord.Interaction):
        if interaction.user.id in view.voters:
            await interaction.response.send_message("You've already voted!", ephemeral=True)
            return

        view.vote_counts["Yes"] += 1
        view.voters.add(interaction.user.id)
        await interaction.response.send_message("You voted Yes!", ephemeral=True)

    async def no_callback(interaction: discord.Interaction):
        if interaction.user.id in view.voters:
            await interaction.response.send_message("You've already voted!", ephemeral=True)
            return

        view.vote_counts["No"] += 1
        view.voters.add(interaction.user.id)
        await interaction.response.send_message("You voted No!", ephemeral=True)

    # Assign callbacks
    yes_button.callback = yes_callback
    no_button.callback = no_callback

    # Send the poll
    poll_message = await ctx.send(embed=embed, view=view)

  
    await discord.utils.sleep_until(discord.utils.utcnow() + timedelta(seconds=duration))

    # Disable buttons and display results
    view.clear_items()
    yes_votes = view.vote_counts["Yes"]
    no_votes = view.vote_counts["No"]
    total_votes = yes_votes + no_votes

    if total_votes > 0:
        yes_percentage = (yes_votes / total_votes) * 100
        no_percentage = (no_votes / total_votes) * 100
    else:
        yes_percentage = 0
        no_percentage = 0

    results_embed = discord.Embed(
        title="📊 Poll Results",
        description=f"**Question:** {question}\n\n**Yes:** {yes_votes} ({yes_percentage:.2f}%)\n**No:** {no_votes} ({no_percentage:.2f}%)",
        color=discord.Color.green(),
    )
    await poll_message.edit(embed=results_embed)


Translate a message to English and send it in DM
@bot.command()
async def translate(ctx, message_id: int):
    """Translate a message to English and send it via DM."""
    try:
        # Fetch the message by id
        message = await ctx.fetch_message(message_id)
        
      
        if message.guild != ctx.guild:
            await ctx.send("I can only translate messages from this server.")
            return
        
        # Translate the message
        translator = Translator()
        translated = translator.translate(message.content, src='auto', dest='en').text
        
        
        await ctx.author.send(f"Here's the translation of the message:\n\n{translated}")
        
        
        await ctx.send(f"I've sent the translation to your DM, {ctx.author.mention}!")
    
    except discord.NotFound:
        await ctx.send("The message with that ID was not found.")
    except discord.Forbidden:
        await ctx.send("I can't send you a DM. Please make sure your DMs are open.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")


# poll error handling
@poll.error
async def poll_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have the required role to create polls!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("You need to provide a question for the poll!")


# Run the bot
bot.run("bot_token")
