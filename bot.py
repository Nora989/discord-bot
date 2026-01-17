

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from datetime import timedelta
import os

TOKEN = os.getenv("TOKEN")

INTENTS = discord.Intents.default()
INTENTS.members = True
INTENTS.guilds = True
INTENTS.message_content = True

bot = commands.Bot(command_prefix="!", intents=INTENTS)

# STOCKAGE EN MÉMOIRE
owners = {}          # guild_id: set(user_id)
warns = {}           # guild_id: {user_id: count}
channel_spam_tasks = {}  # guild_id: asyncio.Task

TICKET_CATEGORY_NAME = "TICKETS"

# UTILS
def is_owner_or_admin(interaction: discord.Interaction):
    if interaction.user.guild_permissions.administrator:
        return True
    return interaction.user.id in owners.get(interaction.guild.id, set())

# READY
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Connecté en tant que {bot.user}")

# HELP
@bot.tree.command(name="help", description="Liste des commandes")
async def help_cmd(interaction: discord.Interaction):
    await interaction.response.send_message(
        "**📜 Commandes disponibles :**\n"
        "/say\n/on /off\n/lock /unlock\n"
        "/clear /clear_all\n"
        "/ticket\n"
        "/kick /ban\n"
        "/mute /unmute\n"
        "/warn /unwarn\n"
        "/role_add",
        ephemeral=True
    )

# -----------------------------
# SAY
# -----------------------------
@bot.tree.command(name="say", description="Faire parler le bot")
async def say(interaction: discord.Interaction, message: str):
    if not is_owner_or_admin(interaction):
        return await interaction.response.send_message("❌ Permission refusée", ephemeral=True)

    await interaction.response.defer(ephemeral=True)
    await interaction.channel.send(message)

# -----------------------------
# ON / OFF (salons infinis)
# -----------------------------
@bot.tree.command(name="on", description="Créer des salons en boucle")
async def on(interaction: discord.Interaction, name: str):
    if not is_owner_or_admin(interaction):
        return await interaction.response.send_message("❌ Permission refusée", ephemeral=True)

    if interaction.guild.id in channel_spam_tasks:
        return await interaction.response.send_message("⚠️ Déjà actif", ephemeral=True)

    await interaction.response.send_message("✅ Création lancée")

    async def spam():
        while True:
            await interaction.guild.create_text_channel(name)
            await asyncio.sleep(1)

    channel_spam_tasks[interaction.guild.id] = asyncio.create_task(spam())

@bot.tree.command(name="off", description="Stopper la création")
async def off(interaction: discord.Interaction):
    task = channel_spam_tasks.pop(interaction.guild.id, None)
    if task:
        task.cancel()
        await interaction.response.send_message("🛑 Création stoppée")
    else:
        await interaction.response.send_message("⚠️ Rien à stopper", ephemeral=True)

# -----------------------------
# LOCK / UNLOCK
# -----------------------------
@bot.tree.command(name="lock")
async def lock(interaction: discord.Interaction):
    if not is_owner_or_admin(interaction):
        return await interaction.response.send_message("❌ Permission refusée", ephemeral=True)

    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.response.send_message("🔒 Salon verrouillé")

@bot.tree.command(name="unlock")
async def unlock(interaction: discord.Interaction):
    if not is_owner_or_admin(interaction):
        return await interaction.response.send_message("❌ Permission refusée", ephemeral=True)

    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
    await interaction.response.send_message("🔓 Salon déverrouillé")

# -----------------------------
# CLEAR
# -----------------------------
@bot.tree.command(name="clear")
async def clear(interaction: discord.Interaction, amount: int):
    if not is_owner_or_admin(interaction):
        return await interaction.response.send_message("❌ Permission refusée", ephemeral=True)

    await interaction.channel.purge(limit=amount)
    await interaction.response.send_message(f"🧹 {amount} messages supprimés", ephemeral=True)

@bot.tree.command(name="clear_all")
async def clear_all(interaction: discord.Interaction):
    if not is_owner_or_admin(interaction):
        return await interaction.response.send_message("❌ Permission refusée", ephemeral=True)

    channel = interaction.channel
    pos = channel.position
    await channel.delete()
    new = await interaction.guild.create_text_channel(channel.name)
    await new.edit(position=pos)

# -----------------------------
# MODERATION
# -----------------------------
@bot.tree.command(name="kick")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    if not is_owner_or_admin(interaction):
        return await interaction.response.send_message("❌ Permission refusée", ephemeral=True)
    await member.kick(reason=reason)
    await interaction.response.send_message(f"👢 {member} kick")

@bot.tree.command(name="ban")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    if not is_owner_or_admin(interaction):
        return await interaction.response.send_message("❌ Permission refusée", ephemeral=True)
    await member.ban(reason=reason)
    await interaction.response.send_message(f"🔨 {member} banni")

# -----------------------------
# MUTE
# -----------------------------
@bot.tree.command(name="mute")
async def mute(interaction: discord.Interaction, member: discord.Member, minutes: int):
    if not is_owner_or_admin(interaction):
        return await interaction.response.send_message("❌ Permission refusée", ephemeral=True)

    await member.timeout(timedelta(minutes=minutes))
    await interaction.response.send_message(f"🔇 {member} mute {minutes} min")

@bot.tree.command(name="unmute")
async def unmute(interaction: discord.Interaction, member: discord.Member):
    if not is_owner_or_admin(interaction):
        return await interaction.response.send_message("❌ Permission refusée", ephemeral=True)

    await member.timeout(None)
    await interaction.response.send_message(f"🔊 {member} unmute")

# -----------------------------
# WARN
# -----------------------------
@bot.tree.command(name="warn")
async def warn(interaction: discord.Interaction, member: discord.Member):
    warns.setdefault(interaction.guild.id, {})
    warns[interaction.guild.id][member.id] = warns[interaction.guild.id].get(member.id, 0) + 1
    await interaction.response.send_message(f"⚠️ {member} warn ({warns[interaction.guild.id][member.id]})")

@bot.tree.command(name="unwarn")
async def unwarn(interaction: discord.Interaction, member: discord.Member):
    warns.get(interaction.guild.id, {}).pop(member.id, None)
    await interaction.response.send_message(f"✅ Warns supprimés")

# -----------------------------
# ROLE ADD
# -----------------------------
@bot.tree.command(name="role_add")
async def role_add(interaction: discord.Interaction, role: discord.Role, minutes: int = None):
    if not is_owner_or_admin(interaction):
        return await interaction.response.send_message("❌ Permission refusée", ephemeral=True)

    member = interaction.user
    await member.add_roles(role)

    if minutes:
        await interaction.response.send_message(f"🎭 Rôle ajouté {minutes} min")
        await asyncio.sleep(minutes * 60)
        await member.remove_roles(role)
    else:
        await interaction.response.send_message("🎭 Rôle ajouté (infini)")

# -----------------------------
# TICKET SYSTEM
# -----------------------------
class TicketView(discord.ui.View):
    @discord.ui.button(label="🎫 Créer un ticket", style=discord.ButtonStyle.green)
    async def create(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
        if not category:
            category = await guild.create_category(TICKET_CATEGORY_NAME)

        channel = await guild.create_text_channel(
            f"ticket-{interaction.user.name}",
            category=category
        )
        await channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
        await interaction.response.send_message("✅ Ticket créé", ephemeral=True)
        await channel.send("Cliquez pour fermer le ticket", view=CloseTicketView())

class CloseTicketView(discord.ui.View):
    @discord.ui.button(label="🔒 Fermer", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()

@bot.tree.command(name="ticket")
async def ticket(interaction: discord.Interaction):
    await interaction.response.send_message("🎟️ Ouvrir un ticket :", view=TicketView())

# -----------------------------
bot.run(TOKEN)



