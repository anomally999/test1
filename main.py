import os
import random
import sqlite3
import discord
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv
from datetime import timedelta, datetime as dt, timezone
from discord.utils import utcnow
import asyncio
import re
from io import BytesIO
import aiohttp
import ast
import sys
import traceback
from contextlib import contextmanager
# ---------- ENVIRONMENT ----------
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("PREFIX", "!")
DB_NAME = os.getenv("DB_PATH", "medieval_moderator.db")  # Made configurable for persistent storage on Render
# ---------- ROYAL SEAL IMAGE ----------
ROYAL_SEAL_URL = "https://imgs.search.brave.com/ybyUdUFEw0dNXKCLGu2FuNAlJpvCTxkjXZUxOSFKcMM/rs:fit:500:0:1:0/g:ce/aHR0cHM6Ly90aHVt/YnMuZHJlYW1zdGlt/ZS5jb20vYi9yb3lh/bC1kZWNyZWUtdW52/ZWlsZWQtZXhxdWlz/aXRlLWdvbGQtc2Vh/bC12aW50YWdlLXN0/YXRpb25lcnktaGFu/ZHdyaXR0ZW4tbGV0/dGVyLWV4cGxvcmUt/b3B1bGVuY2UtcmVn/YWwtc3RlcC1iYWNr/LTM1MTI2NjUwOC5q/cGc"
# ---------- DATABASE CONNECTION MANAGER ----------
@contextmanager
def get_db_connection():
    """Context manager for database connections to prevent race conditions"""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME, timeout=10.0, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL") # Write-Ahead Logging for better concurrency
        conn.row_factory = sqlite3.Row
        yield conn
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
# ---------- MEDIEVAL FLAIR ----------
MEDIEVAL_COLORS = {
    "gold": discord.Colour.gold(),
    "red": discord.Colour.dark_red(),
    "green": discord.Colour.dark_green(),
    "blue": discord.Colour.dark_blue(),
    "purple": discord.Colour.purple(),
    "orange": discord.Colour.dark_orange(),
    "teal": discord.Colour.teal(),
    "blurple": discord.Colour.blurple(),
    "yellow": discord.Colour.yellow(),
}
MEDIEVAL_PREFIXES = [
    "Hark!", "Verily,", "By mine honour,", "Prithee,", "Forsooth,", "Hear ye, hear ye!",
    "Lo and behold,", "By mine troth,", "Marry,", "Gadzooks!", "Zounds!", "By the saints,",
    "By my halidom,", "In faith,", "By my beard,", "By the rood,", "Alack,", "Alas,", "Fie!",
    "Good my lord,", "Noble sir,", "Fair lady,", "By the mass,", "Gramercy,", "Well met,",
    "God ye good den,", "What ho!", "Avaunt!", "By cock and pie,", "Odds bodikins!",
]
MEDIEVAL_SUFFIXES = [
    "m'lord.", "good sir.", "fair maiden.", "noble knight.", "worthy peasant.", "gentle soul.",
    "brave warrior.", "wise sage.", "royal subject.", "courtier.", "squire.", "yeoman.",
    "varlet.", "knave.", "villager.", "my liege.", "thou valiant soul.", "thou stout yeoman.",
    "thou gracious dame.", "as the saints bear witness.", "upon mine honour.", "by the Virgin's grace.",
]
MEDIEVAL_GREETINGS = [
    "Hail, good traveler!", "Well met in these fair lands!", "God's greeting to thee!",
    "May fortune favor thee this day!", "A joyous day to thee, wanderer!",
    "The realm welcomes thy presence!", "Blessings upon thee, wayfarer!",
]
# MEDIEVAL LOG MESSAGES
LOG_MESSAGES = {
    "message_edit": [
        "📜 **SCROLL AMENDED** 📜\n{user} hath revised their words!\n**Before:** {before}\n**After:** {after}",
        "📝 **CHRONICLE ALTERED** 📝\n{user} hath changed their discourse!\n**Original:** {before}\n**Amended:** {after}",
        "⚔️ **WORDS REFORGED** ⚔️\n{user} hath reforged their message!\n**Prior:** {before}\n**Anew:** {after}"
    ],
    "message_delete": [
        "🔥 **WORDS CONSUMED** 🔥\n{user} hath recalled their message!\n**Content:** {content}",
        "⚰️ **DISCOURSE BURIED** ⚰️\n{user} hath erased their words!\n**Said:** {content}",
        "🗡️ **MESSAGE SLAIN** 🗡️\n{user} hath slain their own words!\n**Was:** {content}"
    ],
    "member_join": [
        "🚪 **TRAVELER ARRIVES** 🚪\n{user} hath entered the realm!\n**Account created:** {created}",
        "⚔️ **NEW RECRUIT** ⚔️\n{user} joins our noble cause!\n**Journey began:** {created}",
        "🏰 **CITIZEN WELCOMED** 🏰\n{user} now walks among us!\n**Since:** {created}"
    ],
    "member_leave": [
        "👋 **SOUL DEPARTS** 👋\n{user} hath left the realm!",
        "⚰️ **CITIZEN GONE** ⚰️\n{user} hath abandoned these lands!",
        "🕊️ **TRAVELER FLED** 🕊️\n{user} hath fled our domain!"
    ],
    "avatar_change": [
        "🎭 **VISAGE ALTERED** 🎭\n{user} hath changed their appearance!",
        "👑 **COUNTENANCE RENEWED** 👑\n{user} bears a new visage!",
        "⚔️ **FACE REFORGED** ⚔️\n{user} presents a new likeness!"
    ],
    "banner_change": [
        "🏰 **STANDARD UPDATED** 🏰\n{user} hath raised a new banner!",
        "🎨 **HERALDRY ALTERED** 🎨\n{user} displays new heraldry!",
        "⚔️ **COLORS CHANGED** ⚔️\n{user} flies different colors!"
    ],
    "nickname_change": [
        "📜 **NAME AMENDED** 📜\n{user} is now known as **{after}**!",
        "⚔️ **TITLE ALTERED** ⚔️\n{user} hath taken the name **{after}**!",
        "👑 **APPELLATION CHANGED** 👑\n{user} shall be called **{after}**!"
    ],
    "role_add": [
        "⚔️ **HONOR BESTOWED** ⚔️\n{user} hath gained the role **{role}**!",
        "👑 **PRIVILEGE GRANTED** 👑\n{user} now bears **{role}**!",
        "🏰 **RANK ELEVATED** 🏰\n{user} is elevated to **{role}**!"
    ],
    "role_remove": [
        "🗡️ **HONOR STRIPPED** 🗡️\n{user} hath lost the role **{role}**!",
        "⚰️ **PRIVILEGE REVOKED** ⚰️\n{user} no longer bears **{role}**!",
        "👑 **RANK DIMINISHED** 👑\n{role} is removed from {user}!"
    ]
}
# PILLORY MESSAGES - Enhanced with Royal Decree formatting and Royal Seal
PILLORY_SHAME_MESSAGES = [
    """👑 **ROYAL DECREE OF PUBLIC SHAME** 👑
    @here
    **BY ORDER OF THE CROWN AND THE REALM'S JUSTICE**
    Let it be known throughout the kingdom that the **WRETCHED {user}**
    doth stand CONDEMNED before the eyes of all subjects!
    **🎯 CRIME COMMITTED:** {reason}
    **⏰ SENTENCE:** {duration} minutes of UNRELENTING PUBLIC HUMILIATION!
    🔥 **LET ALL WITNESS THIS JUSTICE!** 🔥
    🔥 **MAY THIS BE A LESSON TO ALL WHO WOULD TRANSGRESS!** 🔥
    *The Crown shows no mercy to those who break the peace of the realm!*
    *All subjects are commanded to witness this spectacle of justice!*
    **SO IT IS DECREED!** ⚖️""",
    """⚔️ **PROCLAMATION OF THE REALM** ⚔️
    @here
    **Hear ye, hear ye!** By the authority vested in the Crown and the ancient laws of this kingdom!
    The **MISERABLE {user}** hath been JUDGED and found MOST WANTING in character and conduct!
    **📜 OFFENSE AGAINST THE REALM:** {reason}
    **⚖️ PUNISHMENT PRESCRIBED:** {duration} minutes in the STONES OF ETERNAL SHAME!
    👑 **LET THE CHURCH BELLS RING FORTH THIS JUSTICE!**
    👑 **LET THE TOWNSFOLK GATHER AND WITNESS!**
    *May this spectacle serve as warning to all who would disturb the peace!*
    *The Crown's justice is swift and terrible to behold!*
    **BY ROYAL COMMAND!** 🏰""",
    """🔥 **EDICT OF THE CROWN** 🔥
    @here
    **BE IT KNOWN TO ALL SUBJECTS OF THE REALM!**
    His/Her Majesty doth pronounce that **{user}** shall face the CONSEQUENCES of their base actions!
    **⚠️ TRANSGRESSION COMMITTED:** {reason}
    **🎯 DOOM APPOINTED:** {duration} minutes of PUBLIC HUMILIATION WITHOUT MERCY!
    ⚖️ **SO DECLARES THE CROWN AND THE REALM'S JUSTICE!**
    ⚖️ **LET NONE INTERFERE WITH THE COURSE OF JUSTICE!**
    *Gather round, good subjects, and witness the majesty of law!*
    *Let this be carved in the annals of the realm's history!*
    **THIS DECREE IS LAW!** 📜"""
]
PILLORY_UPDATE_MESSAGES = [
    """⏰ **CHRONICLE OF CONTINUING SHAME** ⏰
    @here
    **UPDATE FROM THE ROYAL COURT OF JUSTICE**
    The **WRETCHED {user}** CONTINUES to suffer the consequences of their crimes against the realm!
    **⏳ TIME SERVED:** {elapsed} minutes of shame
    **⏳ TIME REMAINING:** {remaining} MORE minutes of public spectacle!
    *Justice is patient but thorough in its application!*
    *The Crown's judgment knows neither haste nor leniency!*
    **LET THE SPECTACLE CONTINUE!** 🔥""",
    """🔔 **BULLETIN FROM THE PILORY** 🔔
    @here
    **ATTENTION ALL SUBJECTS OF THE REALM!**
    {user} STILL PAYS THE PRICE for their transgressions against the peace of the kingdom!
    **⚖️ JUSTICE SERVED:** {elapsed} minutes completed
    **⚖️ JUSTICE PENDING:** {remaining} additional minutes of shame!
    *The royal chronicles mark each passing moment!*
    *Time moves slowly when justice demands its due!*
    **THE CROWN IS WATCHING!** 👁️"""
]
PILLORY_INSULTS_EXTENDED = [
    "Such shame! Even the village fool covers his eyes in embarrassment!",
    "The gods themselves weep at such pitiful display of character!",
    "Rats flee the square, unable to bear witness to such humiliation!",
    "Even the stones cry out for mercy at this terrible sight!",
    "The crows circle overhead, awaiting the carrion of shattered pride!",
    "Children point and laugh, learning what NOT to become in life!",
    "The shadows themselves reject this poor wretch's presence!",
    "Time moves slowly when justice demands its terrible due!",
    "The church bells toll in mourning for this soul's reputation!",
    "Even the dogs refuse to bark in the presence of such shame!"
]
# CHANNEL LOCK MESSAGES - Enhanced Royal Decree format
MEDIEVAL_LOCK_MESSAGES = [
    """🔒 **ROYAL DECREE - CHAMBER SEALED** 🔒
    **BY THE DIVINE RIGHT OF THE CROWN AND THE AUTHORITY OF THE REALM**
    Let it be proclaimed that **{channel}** is HEREBY SEALED by royal command!
    **👑 Authority:** {moderator}
    **📜 Cause:** {reason}
    *Let NONE dare speak within these hallowed walls until the Crown declares otherwise!*
    *The realm demands quiet contemplation and respectful silence!*
    *Any subject who violates this decree shall face the full wrath of justice!*
    **SO SPEAKS THE CROWN!** ⚖️""",
    """⚔️ **PROCLAMATION - CHAMBER SILENCED** ⚔️
    **Hear ye, hear ye!** By ancient law and royal prerogative!
    The chamber known as **{channel}** now FACES ROYAL SILENCE and is forbidden to all discourse!
    **🎯 Sealed by:** {moderator}
    **⚠️ Reason:** {reason}
    *The realm demands quiet contemplation and meditation!*
    *Let the stones themselves remember this day of enforced silence!*
    *May wisdom come to those who would break the peace!*
    **BY ORDER OF THE REALM!** 🏰"""
]
MEDIEVAL_UNLOCK_MESSAGES = [
    """🔓 **ROYAL DECREE - CHAMBER RESTORED** 🔓
    **BY THE MERCY AND WISDOM OF THE CROWN**
    Be it known that **{channel}** is RESTORED TO DISCOURSE by royal mercy!
    **👑 Mercy shown by:** {moderator}
    **📜 Reason:** {reason}
    *Speak freely once more, but remember the lessons that silence hath taught!*
    *Let wisdom guide thy words henceforth, good subjects!*
    *The Crown shows clemency, but remembers all transgressions!*
    **THE KING'S MERCY PREVAILS!** 🕊️""",
    """🕊️ **PROCLAMATION - SILENCE BROKEN** 🕊️
    **ATTENTION ALL SUBJECTS!**
    The chamber **{channel}** may ONCE MORE RING WITH VOICES and discourse!
    **⚖️ Unsealed by:** {moderator}
    **🕊️ Cause:** {reason}
    *Speak freely, but remember the lessons of enforced silence!*
    *Let thy words be measured and wise henceforth!*
    *The Crown's mercy is great, but justice is always watching!*
    **DISCOURSE IS RESTORED!** 📜"""
]
def get_medieval_prefix():
    return random.choice(MEDIEVAL_PREFIXES)
def get_medieval_suffix():
    return random.choice(MEDIEVAL_SUFFIXES) if random.random() > 0.4 else ""
def medieval_greeting():
    return random.choice(MEDIEVAL_GREETINGS)
def medieval_embed(title="", description="", color_name="gold", thumbnail_url=None):
    color = MEDIEVAL_COLORS.get(color_name, MEDIEVAL_COLORS["gold"])
    embed = discord.Embed(
        title=f"🏰 {title}" if "🏰" not in title and "💰" not in title and "🏪" not in title else title,
        description=description,
        colour=color,
        timestamp=utcnow()
    )
    # Add royal seal thumbnail to all embeds
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    else:
        embed.set_thumbnail(url=ROYAL_SEAL_URL)
    embed.set_footer(text="By royal decree of the realm")
    return embed
def medieval_response(message, success=True, extra=""):
    prefix = get_medieval_prefix()
    suffix = get_medieval_suffix()
    color = "green" if success else "red"
    full_message = f"{prefix} {message} {suffix}".strip().capitalize()
    if extra:
        full_message += f"\n\n{extra}"
    return medieval_embed(description=full_message, color_name=color)
# ---------- BOT ----------
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.moderation = True
intents.guilds = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None, case_insensitive=True)
tree = bot.tree
# ---------- DATABASE ----------
def init_db():
    """Initialize database with proper schema and error handling"""
    try:
        with get_db_connection() as db:
            # Pillory system tables - with proper schema updates
            db.execute("""
            CREATE TABLE IF NOT EXISTS pillory_config (
                guild_id INTEGER PRIMARY KEY,
                pillory_channel INTEGER,
                pillory_role INTEGER,
                bypass_roles TEXT,
                allowed_roles TEXT,
                log_channel INTEGER
            )""")
            # Check if log_channel column exists, add if not
            cursor = db.execute("PRAGMA table_info(pillory_config)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'log_channel' not in columns:
                print("Adding missing 'log_channel' column to pillory_config table...")
                db.execute("ALTER TABLE pillory_config ADD COLUMN log_channel INTEGER")
            db.execute("""
            CREATE TABLE IF NOT EXISTS active_pillories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                start_time TEXT,
                end_time TEXT,
                reason TEXT,
                active INTEGER DEFAULT 1
            )""")
            # Moderation logs
            db.execute("""
            CREATE TABLE IF NOT EXISTS moderation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                moderator_id INTEGER,
                target_id INTEGER,
                action TEXT,
                reason TEXT,
                timestamp TEXT
            )""")
            # Warning system
            db.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                moderator_id INTEGER,
                reason TEXT,
                timestamp TEXT
            )""")
            # Mute system
            db.execute("""
            CREATE TABLE IF NOT EXISTS mutes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                moderator_id INTEGER,
                end_time TEXT,
                active INTEGER DEFAULT 1
            )""")
            # Channel locks system
            db.execute("""
            CREATE TABLE IF NOT EXISTS channel_locks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                channel_id INTEGER,
                moderator_id INTEGER,
                reason TEXT,
                unlock_reason TEXT,
                timestamp TEXT,
                active INTEGER DEFAULT 1
            )""")
            # Message tracking for edits/deletes
            db.execute("""
            CREATE TABLE IF NOT EXISTS message_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                channel_id INTEGER,
                message_id INTEGER,
                user_id INTEGER,
                content TEXT,
                attachments TEXT,
                timestamp TEXT
            )""")
            db.commit()
            print("✅ Database initialized successfully")
    except sqlite3.Error as e:
        print(f"❌ Database initialization error: {e}")
        raise
# ---------- PAGINATED HELP COMMAND ----------
class HelpView(discord.ui.View):
    def __init__(self, embeds, timeout=60.0):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.current_page = 0
        self.update_buttons()
    def update_buttons(self):
        # Update button states
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == len(self.embeds) - 1
    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.blurple)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
    @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.blurple)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < len(self.embeds) - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
    @discord.ui.button(label="🗑️ Close", style=discord.ButtonStyle.red)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()
# ---------- LOGGING FUNCTIONS ----------
def get_log_channel(guild_id):
    """Get the log channel for a guild with proper error handling"""
    try:
        with get_db_connection() as db:
            row = db.execute("SELECT log_channel FROM pillory_config WHERE guild_id=?", (guild_id,)).fetchone()
            return row[0] if row and row[0] else None
    except sqlite3.Error as e:
        print(f"Error getting log channel: {e}")
        return None
def set_log_channel(guild_id, channel_id):
    """Set the log channel for a guild with upsert"""
    try:
        with get_db_connection() as db:
            existing = db.execute("SELECT * FROM pillory_config WHERE guild_id=?", (guild_id,)).fetchone()
            if existing:
                db.execute("UPDATE pillory_config SET log_channel=? WHERE guild_id=?", (channel_id, guild_id))
            else:
                db.execute("INSERT INTO pillory_config (guild_id, log_channel) VALUES (?,?)", (guild_id, channel_id))
            db.commit()
        print(f"✅ Log channel set to {channel_id} for guild {guild_id}")
    except sqlite3.Error as e:
        print(f"❌ Error setting log channel: {e}")
        raise
def store_message(message):
    """Store message content for edit/delete tracking with proper error handling"""
    if not message.guild or message.author.bot:
        return
    try:
        attachments = []
        if message.attachments:
            for att in message.attachments:
                attachments.append({
                    "url": att.url,
                    "filename": att.filename,
                    "size": att.size,
                    "content_type": getattr(att, 'content_type', None)
                })
        with get_db_connection() as db:
            db.execute("""
            INSERT INTO message_history (guild_id, channel_id, message_id, user_id, content, attachments, timestamp)
            VALUES (?,?,?,?,?,?,?)
            """, (
                message.guild.id,
                message.channel.id,
                message.id,
                message.author.id,
                message.content,
                str(attachments) if attachments else None,
                utcnow().isoformat()
            ))
            db.commit()
    except Exception as e:
        print(f"Error storing message: {e}")
def get_message_history(message_id):
    """Get stored message data"""
    try:
        with get_db_connection() as db:
            row = db.execute("""
            SELECT content, attachments, user_id FROM message_history
            WHERE message_id=? ORDER BY timestamp DESC LIMIT 1
            """, (message_id,)).fetchone()
            return row if row else None
    except Exception as e:
        print(f"Error getting message history: {e}")
        return None
def format_attachments(attachments_str):
    """Format attachment data for display"""
    if not attachments_str:
        return ""
    try:
        attachments = ast.literal_eval(attachments_str)
        if attachments:
            files = []
            for att in attachments:
                size_kb = att['size'] / 1024 if att.get('size') else 0
                content_type = att.get('content_type', '')
                emoji = "🖼️" if any(img in content_type.lower() for img in ['image', 'photo', 'jpeg', 'png', 'gif']) else "📎"
                files.append(f"{emoji} `{att['filename']}` ({size_kb:.1f}KB)")
            return "\n".join(files)
    except Exception as e:
        print(f"Error formatting attachments: {e}")
    return ""
async def send_log_embed(guild, embed_type, title, description, fields=None, color="blue", thumbnail=None):
    """Send log embed to configured channel with enhanced validation"""
    if not guild:
        return False
    log_channel_id = get_log_channel(guild.id)
    if not log_channel_id:
        return False
    log_channel = guild.get_channel(log_channel_id)
    if not log_channel:
        print(f"❌ Log channel {log_channel_id} not found in guild {guild.id}")
        # Try to remove invalid channel from database
        try:
            with get_db_connection() as db:
                db.execute("UPDATE pillory_config SET log_channel=NULL WHERE guild_id=?", (guild.id,))
                db.commit()
        except:
            pass
        return False
    try:
        embed = medieval_embed(title=title, description=description, color_name=color)
        if fields:
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        embed.set_footer(text=f"Server: {guild.name} | ID: {guild.id}")
        await log_channel.send(embed=embed)
        return True
    except discord.Forbidden:
        print(f"❌ No permission to send logs to channel {log_channel_id}")
        return False
    except Exception as e:
        print(f"❌ Error sending log: {e}")
        return False
# ---------- PILLORY FUNCTIONS ----------
def get_pillory_channel(guild_id):
    """Get the pillory channel for a guild"""
    try:
        with get_db_connection() as db:
            row = db.execute("SELECT pillory_channel FROM pillory_config WHERE guild_id=?", (guild_id,)).fetchone()
            return row[0] if row and row[0] else None
    except sqlite3.Error as e:
        print(f"Error getting pillory channel: {e}")
        return None
def set_pillory_channel(guild_id, channel_id):
    """Set the pillory channel for a guild with upsert"""
    try:
        with get_db_connection() as db:
            existing = db.execute("SELECT * FROM pillory_config WHERE guild_id=?", (guild_id,)).fetchone()
            if existing:
                db.execute("UPDATE pillory_config SET pillory_channel=? WHERE guild_id=?", (channel_id, guild_id))
            else:
                db.execute("INSERT INTO pillory_config (guild_id, pillory_channel) VALUES (?,?)", (guild_id, channel_id))
            db.commit()
    except sqlite3.Error as e:
        print(f"Error setting pillory channel: {e}")
        raise
def get_pillory_role(guild_id):
    """Get the pillory role for a guild"""
    try:
        with get_db_connection() as db:
            row = db.execute("SELECT pillory_role FROM pillory_config WHERE guild_id=?", (guild_id,)).fetchone()
            return row[0] if row and row[0] else None
    except sqlite3.Error:
        return None
def set_pillory_role(guild_id, role_id):
    """Set the pillory role for a guild"""
    try:
        with get_db_connection() as db:
            existing = db.execute("SELECT * FROM pillory_config WHERE guild_id=?", (guild_id,)).fetchone()
            if existing:
                db.execute("UPDATE pillory_config SET pillory_role=? WHERE guild_id=?", (role_id, guild_id))
            else:
                db.execute("INSERT INTO pillory_config (guild_id, pillory_role) VALUES (?,?)", (guild_id, role_id))
            db.commit()
    except sqlite3.Error as e:
        print(f"Error setting pillory role: {e}")
        raise
def get_pillory_bypass_roles(guild_id):
    """Get pillory bypass roles for a guild"""
    try:
        with get_db_connection() as db:
            row = db.execute("SELECT bypass_roles FROM pillory_config WHERE guild_id=?", (guild_id,)).fetchone()
            return row[0] if row and row[0] else None
    except sqlite3.Error:
        return None
def set_pillory_bypass_roles(guild_id, role_ids):
    """Set pillory bypass roles for a guild"""
    try:
        roles_str = ",".join(map(str, role_ids)) if role_ids else ""
        with get_db_connection() as db:
            existing = db.execute("SELECT * FROM pillory_config WHERE guild_id=?", (guild_id,)).fetchone()
            if existing:
                db.execute("UPDATE pillory_config SET bypass_roles=? WHERE guild_id=?", (roles_str, guild_id))
            else:
                db.execute("INSERT INTO pillory_config (guild_id, bypass_roles) VALUES (?,?)", (guild_id, roles_str))
            db.commit()
    except sqlite3.Error as e:
        print(f"Error setting bypass roles: {e}")
        raise
def get_pillory_allowed_roles(guild_id):
    """Get pillory allowed roles for a guild"""
    try:
        with get_db_connection() as db:
            row = db.execute("SELECT allowed_roles FROM pillory_config WHERE guild_id=?", (guild_id,)).fetchone()
            return row[0] if row and row[0] else None
    except sqlite3.Error:
        return None
def set_pillory_allowed_roles(guild_id, role_ids):
    """Set pillory allowed roles for a guild"""
    try:
        roles_str = ",".join(map(str, role_ids)) if role_ids else ""
        with get_db_connection() as db:
            existing = db.execute("SELECT * FROM pillory_config WHERE guild_id=?", (guild_id,)).fetchone()
            if existing:
                db.execute("UPDATE pillory_config SET allowed_roles=? WHERE guild_id=?", (roles_str, guild_id))
            else:
                db.execute("INSERT INTO pillory_config (guild_id, allowed_roles) VALUES (?,?)", (guild_id, roles_str))
            db.commit()
    except sqlite3.Error as e:
        print(f"Error setting allowed roles: {e}")
        raise
def can_use_pillory(guild_id, user_id):
    """Check if user can use pillory commands based on allowed roles"""
    try:
        allowed_roles_str = get_pillory_allowed_roles(guild_id)
        if not allowed_roles_str:
            return True # No restrictions set
        allowed_role_ids = [int(r) for r in allowed_roles_str.split(',') if r]
        if not allowed_role_ids:
            return True
        guild = bot.get_guild(guild_id)
        if not guild:
            return False
        member = guild.get_member(user_id)
        if not member:
            return False
        # Check if user has any of the allowed roles or mod permissions
        return any(role.id in allowed_role_ids for role in member.roles) or member.guild_permissions.moderate_members
    except Exception as e:
        print(f"Error checking pillory permissions: {e}")
        return True
def has_pillory_bypass(guild_id, user_id):
    """Check if user has pillory bypass role"""
    try:
        bypass_roles_str = get_pillory_bypass_roles(guild_id)
        if not bypass_roles_str:
            return False
        bypass_role_ids = [int(r) for r in bypass_roles_str.split(',') if r]
        if not bypass_role_ids:
            return False
        guild = bot.get_guild(guild_id)
        if not guild:
            return False
        member = guild.get_member(user_id)
        if not member:
            return False
        # Check if user has any bypass role
        return any(role.id in bypass_role_ids for role in member.roles)
    except Exception as e:
        print(f"Error checking bypass: {e}")
        return False
def add_pillory(guild_id, user_id, duration_minutes, reason):
    """Add a new pillory with proper error handling"""
    try:
        start_time = utcnow()
        end_time = start_time + timedelta(minutes=duration_minutes)
        with get_db_connection() as db:
            db.execute("""
            INSERT INTO active_pillories (guild_id, user_id, start_time, end_time, reason)
            VALUES (?,?,?,?,?)
            """, (guild_id, user_id, start_time.isoformat(), end_time.isoformat(), reason))
            pillory_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            db.commit()
        return pillory_id
    except Exception as e:
        print(f"Error adding pillory: {e}")
        return None
def get_active_pillories(guild_id):
    """Get all active pillories for a guild"""
    try:
        with get_db_connection() as db:
            rows = db.execute("""
            SELECT id, user_id, start_time, end_time, reason
            FROM active_pillories
            WHERE guild_id=? AND active=1
            """, (guild_id,)).fetchall()
            return rows
    except Exception as e:
        print(f"Error getting active pillories: {e}")
        return []
def end_pillory(pillory_id):
    """End a pillory by ID"""
    try:
        with get_db_connection() as db:
            db.execute("UPDATE active_pillories SET active=0 WHERE id=?", (pillory_id,))
            db.commit()
    except Exception as e:
        print(f"Error ending pillory: {e}")
def is_user_pilloried(guild_id, user_id):
    """Check if user is currently pilloried"""
    try:
        with get_db_connection() as db:
            row = db.execute("""
            SELECT id FROM active_pillories
            WHERE guild_id=? AND user_id=? AND active=1
            """, (guild_id, user_id)).fetchone()
            return row[0] if row else None
    except Exception as e:
        print(f"Error checking if user is pilloried: {e}")
        return None
# ---------- MODERATION FUNCTIONS ----------
def add_warning(guild_id, user_id, moderator_id, reason):
    """Add a warning with proper error handling"""
    try:
        with get_db_connection() as db:
            db.execute("""
            INSERT INTO warnings (guild_id, user_id, moderator_id, reason, timestamp)
            VALUES (?,?,?,?,?)
            """, (guild_id, user_id, moderator_id, reason, utcnow().isoformat()))
            db.commit()
    except Exception as e:
        print(f"Error adding warning: {e}")
        raise
def get_warnings(guild_id, user_id):
    """Get warnings for a user"""
    try:
        with get_db_connection() as db:
            rows = db.execute("""
            SELECT moderator_id, reason, timestamp
            FROM warnings
            WHERE guild_id=? AND user_id=?
            ORDER BY timestamp DESC
            """, (guild_id, user_id)).fetchall()
            return rows
    except Exception as e:
        print(f"Error getting warnings: {e}")
        return []
def add_moderation_log(guild_id, moderator_id, target_id, action, reason):
    """Add moderation log entry"""
    try:
        with get_db_connection() as db:
            db.execute("""
            INSERT INTO moderation_logs (guild_id, moderator_id, target_id, action, reason, timestamp)
            VALUES (?,?,?,?,?,?)
            """, (guild_id, moderator_id, target_id, action, reason, utcnow().isoformat()))
            db.commit()
    except Exception as e:
        print(f"Error adding moderation log: {e}")
        raise
# ---------- CHANNEL LOCK FUNCTIONS ----------
def is_channel_locked(guild_id, channel_id):
    """Check if a channel is currently locked"""
    try:
        with get_db_connection() as db:
            row = db.execute("""
            SELECT id FROM channel_locks
            WHERE guild_id=? AND channel_id=? AND active=1
            """, (guild_id, channel_id)).fetchone()
            return row[0] if row else None
    except Exception as e:
        print(f"Error checking if channel is locked: {e}")
        return None
def lock_channel(guild_id, channel_id, moderator_id, reason):
    """Lock a channel and return lock ID"""
    try:
        with get_db_connection() as db:
            db.execute("""
            INSERT INTO channel_locks (guild_id, channel_id, moderator_id, reason, timestamp)
            VALUES (?,?,?,?,?)
            """, (guild_id, channel_id, moderator_id, reason, utcnow().isoformat()))
            lock_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            db.commit()
        return lock_id
    except Exception as e:
        print(f"Error locking channel: {e}")
        return None
def unlock_channel(lock_id, reason):
    """Unlock a channel"""
    try:
        with get_db_connection() as db:
            db.execute("UPDATE channel_locks SET active=0, unlock_reason=? WHERE id=?", (reason, lock_id))
            db.commit()
    except Exception as e:
        print(f"Error unlocking channel: {e}")
def get_locked_channels(guild_id):
    """Get all locked channels in a guild"""
    try:
        with get_db_connection() as db:
            rows = db.execute("""
            SELECT id, channel_id, moderator_id, reason, timestamp
            FROM channel_locks
            WHERE guild_id=? AND active=1
            ORDER BY timestamp DESC
            """, (guild_id,)).fetchall()
            return rows
    except Exception as e:
        print(f"Error getting locked channels: {e}")
        return []
# ---------- BACKGROUND TASKS ----------
@tasks.loop(minutes=1)
async def check_pillories():
    """Background task to check and end expired pillories"""
    try:
        now = utcnow()
        with get_db_connection() as db:
            rows = db.execute("""
            SELECT id, guild_id, user_id, end_time
            FROM active_pillories
            WHERE active=1
            """).fetchall()
            for pillory_id, guild_id, user_id, end_time_str in rows:
                try:
                    end_time = dt.fromisoformat(end_time_str).replace(tzinfo=timezone.utc)
                    if now >= end_time:
                        # End pillory
                        db.execute("UPDATE active_pillories SET active=0 WHERE id=?", (pillory_id,))
                        # Notify in pillory channel
                        guild = bot.get_guild(guild_id)
                        if guild:
                            pillory_channel_id = get_pillory_channel(guild_id)
                            if pillory_channel_id:
                                channel = guild.get_channel(pillory_channel_id)
                                if channel:
                                    member = guild.get_member(user_id)
                                    if member:
                                        release_ceremonies = [
                                            f"""👑 **ROYAL DECREE - RELEASE GRANTED** 👑
@here
**BY THE MERCY AND WISDOM OF THE CROWN**
{member.mention} hath been RELEASED from the pillory by royal mercy after serving their full sentence!
**⚖️ Justice has been served!**
**🕊️ May wisdom guide thee henceforth!**
*The Crown shows clemency, but remembers all transgressions!*
*Go forth and sin no more, good subject!*
**THE KING'S MERCY PREVAILS!** 🏰""",
                                            f"""🕊️ **PROCLAMATION OF RELEASE** 🕊️
@here
**Hear ye, hear ye!** {member.mention} is FREED from yonder pillory!
**⚔️ The sentence is complete!**
**📜 Justice has had its due!**
*Let this be a lesson learned!*
*Walk henceforth with greater wisdom!*
**BY ORDER OF THE REALM!** 📜"""
                                        ]
                                        await channel.send(random.choice(release_ceremonies))
                except ValueError as e:
                    print(f"Error parsing end_time: {e}")
                    continue
            db.commit()
    except Exception as e:
        print(f"Error in check_pillories: {e}")
@check_pillories.before_loop
async def before_pillories():
    await bot.wait_until_ready()
# ---------- ENHANCED LOGGING EVENT HANDLERS ----------
@bot.event
async def on_message_edit(before, after):
    """Log message edits with full detail and validation"""
    if before.author.bot or before.content == after.content:
        return
    if not before.guild:
        return
    # Store the edited message
    store_message(after)
    # Get old message from history
    old_data = get_message_history(before.id)
    old_content = old_data[0] if old_data else before.content
    # Create log embed
    fields = [
        ("👤 User", f"{after.author.mention} (`{after.author.id}`)", True),
        ("📺 Channel", f"{after.channel.mention} (`{after.channel.id}`)", True),
        ("📜 Before", f"```{old_content[:1000]}```" if len(old_content) <= 1000 else f"```{old_content[:997]}...```", False),
        ("📝 After", f"```{after.content[:1000]}```" if len(after.content) <= 1000 else f"```{after.content[:997]}...```", False),
        ("🔗 Message", f"[Jump to message]({after.jump_url})", True)
    ]
    # Add attachment info if present
    if after.attachments:
        attachment_info = "\n".join([f"📎 `{att.filename}` ({att.size/1024:.1f}KB)" for att in after.attachments])
        fields.append(("📎 Attachments", attachment_info, False))
    await send_log_embed(
        after.guild,
        "message_edit",
        "📜 Scroll Amended",
        random.choice(LOG_MESSAGES["message_edit"]).format(
            user=after.author.mention,
            before=old_content[:100],
            after=after.content[:100]
        ),
        fields=fields,
        color="yellow",
        thumbnail=str(after.author.avatar.url) if after.author.avatar else None
    )
@bot.event
async def on_message_delete(message):
    """Log message deletions with full detail"""
    if message.author.bot:
        return
    if not message.guild:
        return
    # Get stored message data
    old_data = get_message_history(message.id)
    content = old_data[0] if old_data else message.content
    attachments_str = old_data[1] if old_data else None
    # Create log embed
    fields = [
        ("👤 User", f"{message.author.mention} (`{message.author.id}`)", True),
        ("📺 Channel", f"{message.channel.mention} (`{message.channel.id}`)", True),
        ("📜 Content", f"```{content[:1000]}```" if len(content) <= 1000 else f"```{content[:997]}...```", False)
    ]
    # Handle attachments
    if attachments_str:
        attachment_info = format_attachments(attachments_str)
        if attachment_info:
            fields.append(("📎 Attachments", attachment_info, False))
    elif message.attachments:
        attachment_info = "\n".join([f"📎 `{att.filename}` ({att.size/1024:.1f}KB)" for att in message.attachments])
        fields.append(("📎 Attachments", attachment_info, False))
    await send_log_embed(
        message.guild,
        "message_delete",
        "🔥 Words Consumed",
        random.choice(LOG_MESSAGES["message_delete"]).format(
            user=message.author.mention,
            content=content[:100]
        ),
        fields=fields,
        color="red",
        thumbnail=str(message.author.avatar.url) if message.author.avatar else None
    )
@bot.event
async def on_member_join(member):
    """Log member joins with full detail"""
    if member.bot:
        return
    created_date = f"<t:{int(member.created_at.timestamp())}:R>"
    fields = [
        ("👤 Member", f"{member.mention} (`{member.id}`)", True),
        ("📅 Account Created", created_date, True),
        ("📊 Total Members", f"{member.guild.member_count}", True)
    ]
    await send_log_embed(
        member.guild,
        "member_join",
        "🚪 Traveler Arrives",
        random.choice(LOG_MESSAGES["member_join"]).format(
            user=member.mention,
            created=created_date
        ),
        fields=fields,
        color="green",
        thumbnail=str(member.avatar.url) if member.avatar else None
    )
@bot.event
async def on_member_remove(member):
    """Log member leaves with full detail"""
    if member.bot:
        return
    # Get join date if available
    join_date = "Unknown"
    if member.joined_at:
        join_date = f"<t:{int(member.joined_at.timestamp())}:R>"
    fields = [
        ("👤 Member", f"{member.mention} (`{member.id}`)", True),
        ("📅 Joined Server", join_date, True),
        ("📊 Total Members", f"{member.guild.member_count}", True)
    ]
    await send_log_embed(
        member.guild,
        "member_leave",
        "👋 Soul Departs",
        random.choice(LOG_MESSAGES["member_leave"]).format(user=member.mention),
        fields=fields,
        color="orange",
        thumbnail=str(member.avatar.url) if member.avatar else None
    )
@bot.event
async def on_user_update(before, after):
    """Log user profile changes (avatar, banner, etc.)"""
    # Avatar changes
    if before.avatar != after.avatar:
        for guild in bot.guilds:
            member = guild.get_member(before.id)
            if member and not member.bot:
                await send_log_embed(
                    guild,
                    "avatar_change",
                    "🎭 Visage Altered",
                    random.choice(LOG_MESSAGES["avatar_change"]).format(user=member.mention),
                    fields=[("👤 User", f"{member.mention} (`{member.id}`)", True)],
                    color="purple",
                    thumbnail=str(after.avatar.url) if after.avatar else None
                )
    # Banner changes (if available)
    if hasattr(before, 'banner') and hasattr(after, 'banner') and before.banner != after.banner:
        for guild in bot.guilds:
            member = guild.get_member(before.id)
            if member and not member.bot:
                await send_log_embed(
                    guild,
                    "banner_change",
                    "🏰 Standard Updated",
                    random.choice(LOG_MESSAGES["banner_change"]).format(user=member.mention),
                    fields=[("👤 User", f"{member.mention} (`{member.id}`)", True)],
                    color="blue",
                    thumbnail=str(after.avatar.url) if after.avatar else None
                )
@bot.event
async def on_member_update(before, after):
    """Log member updates (nickname, roles, etc.)"""
    if before.bot:
        return
    # Nickname changes
    if before.nick != after.nick:
        fields = [
            ("👤 Member", f"{before.mention} (`{before.id}`)", True),
            ("📜 Before", f"`{before.nick}`" if before.nick else "`None`", True),
            ("📝 After", f"`{after.nick}`" if after.nick else "`None`", True)
        ]
        await send_log_embed(
            before.guild,
            "nickname_change",
            "📜 Name Amended",
            random.choice(LOG_MESSAGES["nickname_change"]).format(
                user=before.mention,
                after=after.nick or before.name
            ),
            fields=fields,
            color="yellow",
            thumbnail=str(after.avatar.url) if after.avatar else None
        )
    # Role changes
    added_roles = [role for role in after.roles if role not in before.roles and not role.is_default()]
    removed_roles = [role for role in before.roles if role not in after.roles and not role.is_default()]
    # Role additions
    for role in added_roles:
        fields = [
            ("👤 Member", f"{after.mention} (`{after.id}`)", True),
            ("⚔️ Role", f"{role.mention} (`{role.id}`)", True),
            ("📊 Color", f"#{role.color.value:06x}" if role.color.value else "None", True)
        ]
        await send_log_embed(
            after.guild,
            "role_add",
            "⚔️ Honor Bestowed",
            random.choice(LOG_MESSAGES["role_add"]).format(
                user=after.mention,
                role=role.mention
            ),
            fields=fields,
            color="green",
            thumbnail=str(after.avatar.url) if after.avatar else None
        )
    # Role removals
    for role in removed_roles:
        fields = [
            ("👤 Member", f"{after.mention} (`{after.id}`)", True),
            ("🗡️ Role", f"{role.mention} (`{role.id}`)", True),
            ("📊 Color", f"#{role.color.value:06x}" if role.color.value else "None", True)
        ]
        await send_log_embed(
            after.guild,
            "role_remove",
            "🗡️ Honor Stripped",
            random.choice(LOG_MESSAGES["role_remove"]).format(
                user=after.mention,
                role=role.mention
            ),
            fields=fields,
            color="red",
            thumbnail=str(after.avatar.url) if after.avatar else None
        )
@bot.event
async def on_guild_channel_create(channel):
    """Log channel creation"""
    if not isinstance(channel, (discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel)):
        return
    fields = [
        ("📺 Channel", f"{channel.mention} (`{channel.id}`)", True),
        ("📁 Type", channel.type.name.title(), True),
        ("📅 Created", f"<t:{int(channel.created_at.timestamp())}:R>", True)
    ]
    if hasattr(channel, 'category') and channel.category:
        fields.append(("📂 Category", channel.category.name, True))
    await send_log_embed(
        channel.guild,
        "channel_create",
        "📺 Chamber Created",
        f"A new {channel.type.name} chamber hath been created: {channel.mention}",
        fields=fields,
        color="green"
    )
@bot.event
async def on_guild_channel_delete(channel):
    """Log channel deletion"""
    if not isinstance(channel, (discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel)):
        return
    fields = [
        ("📺 Channel", f"#{channel.name}` (`{channel.id}`)", True),
        ("📁 Type", channel.type.name.title(), True)
    ]
    if hasattr(channel, 'category') and channel.category:
        fields.append(("📂 Category", channel.category.name, True))
    await send_log_embed(
        channel.guild,
        "channel_delete",
        "📺 Chamber Destroyed",
        f"A {channel.type.name} chamber hath been destroyed: #{channel.name}",
        fields=fields,
        color="red"
    )
@bot.event
async def on_guild_role_create(role):
    """Log role creation"""
    fields = [
        ("⚔️ Role", f"{role.mention} (`{role.id}`)", True),
        ("📊 Color", f"#{role.color.value:06x}" if role.color.value else "None", True),
        ("📅 Created", f"<t:{int(role.created_at.timestamp())}:R>", True)
    ]
    await send_log_embed(
        role.guild,
        "role_create",
        "⚔️ Honor Created",
        f"A new role hath been created: {role.mention}",
        fields=fields,
        color="green"
    )
@bot.event
async def on_guild_role_delete(role):
    """Log role deletion"""
    fields = [
        ("🗡️ Role", f"@{role.name}` (`{role.id}`)", True),
        ("📊 Color", f"#{role.color.value:06x}" if role.color.value else "None", True)
    ]
    await send_log_embed(
        role.guild,
        "role_delete",
        "🗡️ Honor Destroyed",
        f"A role hath been destroyed: @{role.name}",
        fields=fields,
        color="red"
    )
# ---------- ENHANCED HELP COMMAND WITH ALL COMMANDS ----------
@bot.command(name="help")
@commands.guild_only()
async def _help(ctx):
    """Comprehensive help command with ALL commands and pagination"""
    try:
        # Complete list of ALL commands - both traditional and slash commands
        all_commands = {
            "🏰 **Royal Administration**": [
                ("help", "Display this royal charter of commands"),
                ("setlogchannel <channel>", "Set the royal chronicle channel for all logs"),
                ("psetchannel <channel>", "Set the pillory channel for public shaming"),
            ],
            "⚔️ **Pillory System**": [
                ("pillory <member> <duration> <reason>", "Place a knave in public shame"),
                ("pillories", "View all active pillories in the realm"),
                ("pardon <pillory_id>", "Show mercy and end a pillory early"),
                ("pbypass <role1> [role2]...", "Set roles immune to pillory punishment"),
                ("pbypasslist", "List roles with pillory immunity"),
                ("pallow <role1> [role2]...", "Set roles allowed to use pillory commands"),
                ("pallowlist", "List roles with pillory command privileges"),
            ],
            "🔒 **Chamber Management**": [
                ("seal [reason]", "Seal a chamber to silence all discourse"),
                ("unseal [reason]", "Unseal a chamber and restore discourse"),
                ("sealed", "View all sealed chambers in the realm"),
            ],
            "⚠️ **Warning System**": [
                ("warn <member> <reason>", "Issue a warning to a miscreant"),
                ("warnings [member]", "Check warnings for a subject"),
                ("clearwarn <member>", "Clear warnings from a repentant soul"),
            ],
            "🔨 **Punishment & Justice**": [
                ("kick <member> [reason]", "Banish a knave from the realm"),
                ("ban <member> [reason]", "Permanently exile a criminal"),
                ("unban <user_id> [reason]", "Grant royal pardon to an exile"),
                ("mute <member> <duration> [reason]", "Silence a chatterer for a time"),
                ("unmute <member> [reason]", "Restore voice to the silenced"),
                ("purge <amount>", "Cleanse the chat of messages (1-100)"),
            ],
            "📜 **Slash Commands - Setup**": [
                ("/setlogchannel <channel>", "Set the royal chronicle channel"),
                ("/pillory <member> <duration> <reason>", "Place a knave in public shame"),
                ("/pbypass <@role1> [@role2]...", "Set roles immune to pillory"),
                ("/pallow <@role1> [@role2]...", "Set roles allowed to use pillory"),
            ],
            "⚔️ **Slash Commands - Pillory**": [
                ("/pbypasslist", "List bypass roles"),
                ("/pallowlist", "List allowed roles"),
                ("/pillories", "View active pillories"),
                ("/pardon <pillory_id>", "End a pillory early"),
                ("/warn <member> <reason>", "Issue a warning"),
                ("/warnings [member]", "Check warnings"),
            ],
            "🔨 **Slash Commands - Moderation**": [
                ("/kick <member> [reason]", "Banish a knave from the realm"),
                ("/ban <member> [reason]", "Permanently exile a criminal"),
                ("/mute <member> <duration> [reason]", "Silence a chatterer"),
                ("/purge <amount>", "Cleanse the chat of messages"),
            ],
            "🔒 **Slash Commands - Chambers**": [
                ("/seal [reason]", "Seal a channel to prevent messages"),
                ("/unseal [reason]", "Unseal a channel and restore discourse"),
                ("/sealed", "View all sealed chambers"),
            ],
            "💡 **Royal Tips & Usage**": [
                ("Permissions", "Most commands require moderate_members or admin permissions"),
                ("Setup Required", "Use !setlogchannel and !psetchannel to configure essential features"),
                ("Pillory System", "Requires designated channel and optional role for full functionality"),
                ("Slash Commands", "All traditional commands also work as modern slash commands"),
                ("Medieval Flair", "All messages feature dramatic royal decree formatting"),
                ("Royal Seal", "Every embed displays the authentic royal seal for authority"),
            ]
        }
        # Create embeds for each page - exactly 10 items per page
        embeds = []
        page_num = 1
        total_pages = sum((len(commands) + 9) // 10 for commands in all_commands.values())
        for category, commands in all_commands.items():
            # Split commands into chunks of 10 for pagination
            for i in range(0, len(commands), 10):
                chunk = commands[i:i+10]
                embed = medieval_embed(
                    title=f"📜 The Complete Royal Charter - Page {page_num}/{total_pages}",
                    description=f"{medieval_greeting()}\n\n**{category}**",
                    color_name="purple"
                )
                for cmd, desc in chunk:
                    embed.add_field(
                        name=f"**{cmd}**",
                        value=desc,
                        inline=False
                    )
                page_num += 1
                embed.set_footer(text="Use the buttons below to navigate • All commands work with both ! and / prefixes")
                embeds.append(embed)
        # Send the first page with navigation buttons
        view = HelpView(embeds)
        await ctx.send(embed=embeds[0], view=view)
    except Exception as e:
        print(f"Error in help command: {e}")
        await ctx.send(embed=medieval_response("An error occurred displaying the royal charter!", success=False))
# ---------- ADMIN COMMANDS ----------
@bot.command(name="setlogchannel")
@commands.has_permissions(manage_guild=True)
@commands.guild_only()
async def set_log_channel_cmd(ctx, channel: discord.TextChannel):
    """Set the royal chronicle channel for all server logs"""
    try:
        set_log_channel(ctx.guild.id, channel.id)
        embed = medieval_response(
            f"The royal chronicles shall now be recorded in {channel.mention}!",
            success=True,
            extra="All server activities will be documented henceforth!"
        )
        await ctx.send(embed=embed)
        # Send test log
        test_embed = medieval_embed(
            title="📜 Royal Chronicle Initialized",
            description=f"Chronicle system activated by {ctx.author.mention}!",
            color_name="green"
        )
        test_embed.add_field(name="📺 Channel", value=channel.mention, inline=True)
        test_embed.add_field(name="👑 Authority", value=ctx.author.mention, inline=True)
        test_embed.set_footer(text="All server activities will be recorded henceforth!")
        await channel.send(embed=test_embed)
    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error setting chronicle channel: {str(e)}", success=False))
@bot.command(name="psetchannel")
@commands.has_permissions(manage_channels=True)
@commands.guild_only()
async def set_pillory_channel_cmd(ctx, channel: discord.TextChannel):
    """Set the pillory channel for public shaming"""
    try:
        set_pillory_channel(ctx.guild.id, channel.id)
        embed = medieval_response(
            f"The pillory shall now be erected in {channel.mention}!",
            success=True
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error setting channel: {str(e)}", success=False))
# ---------- PILLORY COMMANDS ----------
@bot.command(name="pbypass")
@commands.has_permissions(administrator=True)
@commands.guild_only()
async def set_pillory_bypass_cmd(ctx, *roles: discord.Role):
    """Set roles that can bypass pillory punishment (Admin)"""
    try:
        if not roles:
            return await ctx.send(embed=medieval_response(
                "Thou must specify at least one role for bypass!",
                success=False
            ))
        role_ids = [r.id for r in roles]
        set_pillory_bypass_roles(ctx.guild.id, role_ids)
        role_mentions = " ".join(r.mention for r in roles)
        embed = medieval_embed(
            title="👑 Royal Bypass Privilege",
            description=f"The following roles now possess royal immunity: {role_mentions}",
            color_name="purple"
        )
        embed.add_field(
            name="⚔️ Privilege Granted",
            value="Holders of these roles shall never face the shame of the pillory!",
            inline=False
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error setting bypass roles: {str(e)}", success=False))
@bot.command(name="pallow")
@commands.has_permissions(administrator=True)
@commands.guild_only()
async def set_pillory_allowed_roles_cmd(ctx, *roles: discord.Role):
    """Set roles allowed to use pillory commands (Admin)"""
    try:
        if not roles:
            return await ctx.send(embed=medieval_response(
                "Thou must specify at least one role for pillory privileges!",
                success=False
            ))
        role_ids = [r.id for r in roles]
        set_pillory_allowed_roles(ctx.guild.id, role_ids)
        role_mentions = " ".join(r.mention for r in roles)
        embed = medieval_embed(
            title="⚔️ Royal Pillory Privileges",
            description=f"The following roles now command the power of the pillory: {role_mentions}",
            color_name="purple"
        )
        embed.add_field(
            name="🏰 Authority Bestowed",
            value="Only these chosen roles may condemn souls to public shame!",
            inline=False
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error setting allowed roles: {str(e)}", success=False))
@bot.command(name="pbypasslist")
@commands.guild_only()
async def list_pillory_bypass_roles_cmd(ctx):
    """List roles with pillory bypass privilege"""
    try:
        bypass_roles_str = get_pillory_bypass_roles(ctx.guild.id)
        if not bypass_roles_str:
            return await ctx.send(embed=medieval_response(
                "No roles possess royal bypass privileges!",
                success=True
            ))
        bypass_role_ids = [int(r) for r in bypass_roles_str.split(',') if r]
        roles = [ctx.guild.get_role(role_id) for role_id in bypass_role_ids if ctx.guild.get_role(role_id)]
        if not roles:
            return await ctx.send(embed=medieval_response(
                "The bypass roles exist no more!",
                success=True
            ))
        role_mentions = " ".join(r.mention for r in roles)
        embed = medieval_embed(
            title="👑 Royal Bypass Privileges",
            description=f"These noble roles possess immunity: {role_mentions}",
            color_name="gold"
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error listing bypass roles: {str(e)}", success=False))
@bot.command(name="pallowlist")
@commands.guild_only()
async def list_pillory_allowed_roles_cmd(ctx):
    """List roles allowed to use pillory commands"""
    try:
        allowed_roles_str = get_pillory_allowed_roles(ctx.guild.id)
        if not allowed_roles_str:
            return await ctx.send(embed=medieval_response(
                "All subjects may use the pillory - no restrictions set!",
                success=True
            ))
        allowed_role_ids = [int(r) for r in allowed_roles_str.split(',') if r]
        roles = [ctx.guild.get_role(role_id) for role_id in allowed_role_ids if ctx.guild.get_role(role_id)]
        if not roles:
            return await ctx.send(embed=medieval_response(
                "The privileged roles exist no more!",
                success=True
            ))
        role_mentions = " ".join(r.mention for r in roles)
        embed = medieval_embed(
            title="⚔️ Pillory Command Privileges",
            description=f"These chosen roles command the pillory: {role_mentions}",
            color_name="gold"
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error listing allowed roles: {str(e)}", success=False))
@bot.command(name="pillory")
@commands.guild_only()
async def pillory_cmd(ctx, member: discord.Member, duration_minutes: int, *, reason: str):
    """Place a knave in public shame with dramatic enhanced formatting"""
    try:
        print(f"Pillory command triggered: {member.display_name}, {duration_minutes}, {reason}")
        # Check permissions
        if not ctx.author.guild_permissions.moderate_members:
            return await ctx.send(embed=medieval_response(
                "Thou hast not the royal privilege to command the pillory!",
                success=False
            ))
        # Check if user can use pillory commands
        if not can_use_pillory(ctx.guild.id, ctx.author.id):
            return await ctx.send(embed=medieval_response(
                "Thou hast not the royal privilege to command the pillory!",
                success=False
            ))
        # Check if target has bypass
        if has_pillory_bypass(ctx.guild.id, member.id):
            return await ctx.send(embed=medieval_response(
                f"{member.display_name} possesses royal immunity from the pillory!",
                success=False
            ))
        # Check if pillory channel is set
        pillory_channel_id = get_pillory_channel(ctx.guild.id)
        if not pillory_channel_id:
            return await ctx.send(embed=medieval_response(
                "No pillory channel hath been set! Use `!psetchannel` first.",
                success=False
            ))
        # Check if user is already pilloried
        existing_pillory = is_user_pilloried(ctx.guild.id, member.id)
        if existing_pillory:
            return await ctx.send(embed=medieval_response(
                f"{member.display_name} is already in the pillory!",
                success=False
            ))
        # Validate duration
        if duration_minutes < 1 or duration_minutes > 1440: # Max 24 hours
            return await ctx.send(embed=medieval_response(
                "Duration must be between 1 and 1440 minutes!",
                success=False
            ))
        # Add pillory
        pillory_id = add_pillory(ctx.guild.id, member.id, duration_minutes, reason)
        if not pillory_id:
            return await ctx.send(embed=medieval_response(
                "Failed to create pillory! Check database.",
                success=False
            ))
        # Get pillory channel
        pillory_channel = ctx.guild.get_channel(pillory_channel_id)
        if not pillory_channel:
            return await ctx.send(embed=medieval_response(
                "The pillory channel exists not! Check thy settings.",
                success=False
            ))
        # Add pillory role if set
        pillory_role_id = get_pillory_role(ctx.guild.id)
        if pillory_role_id:
            pillory_role = ctx.guild.get_role(pillory_role_id)
            if pillory_role:
                try:
                    await member.add_roles(pillory_role)
                except discord.Forbidden:
                    pass
        # Create enhanced shame message with @here and royal seal
        shame_message = random.choice(PILLORY_SHAME_MESSAGES).format(
            user=member.display_name.upper(),
            reason=reason,
            duration=duration_minutes,
            moderator=ctx.author.display_name.upper()
        )
        # Send the shame message first (as plain text for @here to work)
        await pillory_channel.send(shame_message)
        # Add moderation log
        add_moderation_log(ctx.guild.id, ctx.author.id, member.id, "pillory", reason)
        # Schedule updates if duration > 5 minutes
        if duration_minutes > 5:
            async def schedule_dramatic_updates():
                try:
                    remaining = duration_minutes
                    update_count = 0
                    while remaining > 0:
                        await asyncio.sleep(300) # Wait 5 minutes
                        remaining -= 5
                        update_count += 1
                        if remaining > 0:
                            # Check if pillory is still active
                            with get_db_connection() as db:
                                row = db.execute("SELECT active FROM active_pillories WHERE id=?", (pillory_id,)).fetchone()
                                if row and row[0] == 1:
                                    # Create dramatic update with @here
                                    update_message = random.choice(PILLORY_UPDATE_MESSAGES).format(
                                        user=member.display_name.upper(),
                                        reason=reason,
                                        elapsed=update_count * 5,
                                        remaining=remaining
                                    )
                                    await pillory_channel.send(update_message)
                                    # Add extra insult for more shame
                                    insult = random.choice(PILLORY_INSULTS_EXTENDED)
                                    await pillory_channel.send(f"*{insult}*")
                                else:
                                    break
                except Exception as e:
                    print(f"Error in pillory updates: {e}")
            bot.loop.create_task(schedule_dramatic_updates())
        await ctx.send(embed=medieval_response(
            f"{member.display_name} hath been placed in the pillory for {duration_minutes} minutes by royal decree!",
            success=True
        ))
    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error creating pillory: {str(e)}", success=False))
@bot.command(name="pillories")
@commands.guild_only()
async def list_pillories(ctx):
    """View active pillories in the realm"""
    try:
        pillories = get_active_pillories(ctx.guild.id)
        if not pillories:
            return await ctx.send(embed=medieval_response(
                "The pillory stands empty this day!",
                success=True
            ))
        embed = medieval_embed(
            title="🎯 Active Pillories",
            description=f"There are **{len(pillories)}** souls in public shame:",
            color_name="orange"
        )
        for pillory_id, user_id, start_time, end_time, reason in pillories:
            member = ctx.guild.get_member(user_id)
            if member:
                try:
                    end_dt = dt.fromisoformat(end_time).replace(tzinfo=timezone.utc)
                    remaining = end_dt - utcnow()
                    minutes_left = max(0, int(remaining.total_seconds() / 60))
                    embed.add_field(
                        name=f"Pillory #{pillory_id} - {member.display_name}",
                        value=f"**Time left:** {minutes_left} minutes\n**Reason:** {reason}",
                        inline=False
                    )
                except ValueError:
                    pass
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error listing pillories: {str(e)}", success=False))
@bot.command(name="pardon")
@commands.guild_only()
async def pardon_cmd(ctx, pillory_id: int):
    """Show mercy and end a pillory early with royal ceremony"""
    try:
        with get_db_connection() as db:
            row = db.execute("SELECT user_id, active FROM active_pillories WHERE id=? AND guild_id=?",
                            (pillory_id, ctx.guild.id)).fetchone()
            if not row:
                return await ctx.send(embed=medieval_response(
                    f"No pillory with ID #{pillory_id} exists!",
                    success=False
                ))
            user_id, active = row
            if not active:
                return await ctx.send(embed=medieval_response(
                    f"Pillory #{pillory_id} is already ended!",
                    success=False
                ))
            # Check permissions
            if not ctx.author.guild_permissions.moderate_members:
                return await ctx.send(embed=medieval_response(
                    "Thou hast not the authority to grant pardons!",
                    success=False
                ))
            # End the pillory
            db.execute("UPDATE active_pillories SET active=0 WHERE id=?", (pillory_id,))
            db.commit()
        # Remove pillory role if set
        pillory_role_id = get_pillory_role(ctx.guild.id)
        if pillory_role_id:
            pillory_role = ctx.guild.get_role(pillory_role_id)
            if pillory_role:
                member = ctx.guild.get_member(user_id)
                if member:
                    try:
                        await member.remove_roles(pillory_role)
                    except discord.Forbidden:
                        pass
        # Get pillory channel and announce pardon with ceremony
        pillory_channel_id = get_pillory_channel(ctx.guild.id)
        if pillory_channel_id:
            pillory_channel = ctx.guild.get_channel(pillory_channel_id)
            if pillory_channel:
                member = ctx.guild.get_member(user_id)
                if member:
                    pardon_ceremonies = [
                        f"""👑 **ROYAL DECREE - MERCY GRANTED** 👑
@here
**BY THE INFINITE WISDOM AND MERCY OF THE CROWN**
The sovereign authority {ctx.author.mention} in their infinite wisdom hath shown LENIENCY to {member.mention}!
**⚖️ The sentence is commuted!**
**🕊️ Mercy prevails over harsh justice this day!**
*Let this be recorded in the annals of the realm!*
*May all subjects mark this day when justice was tempered with compassion!*
**THE KING'S MERCY IS BOUNDLESS!** 📜""",
                        f"""🕊️ **PROCLAMATION OF ROYAL PARDON** 🕊️
@here
**ATTENTION ALL SUBJECTS OF THE REALM!**
By special dispensation and royal prerogative, {ctx.author.mention} hath granted PARDON to {member.mention}!
**📜 The Crown's mercy extends to all who show repentance!**
**⚔️ Justice is served, but mercy is remembered!**
*Let this deed be carved in the chronicles of our fair kingdom!*
*Walk henceforth with wisdom, pardoned soul!*
**SO DECREES THE CROWN!** ⚖️"""
                    ]
                    pardon_message = random.choice(pardon_ceremonies)
                    await pillory_channel.send(pardon_message)
        await ctx.send(embed=medieval_response(
            f"Pillory #{pillory_id} hath been ended by royal pardon!",
            success=True
        ))
    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error granting pardon: {str(e)}", success=False))
# Warning System Commands
@bot.command(name="warn")
@commands.guild_only()
async def warn_cmd(ctx, member: discord.Member, *, reason: str):
    """Issue a warning to a miscreant"""
    try:
        if not ctx.author.guild_permissions.moderate_members:
            return await ctx.send(embed=medieval_response(
                "Thou hast not the authority to issue warnings!",
                success=False
            ))
        if member.id == ctx.author.id:
            return await ctx.send(embed=medieval_response(
                "Thou cannot warn thyself!",
                success=False
            ))
        add_warning(ctx.guild.id, member.id, ctx.author.id, reason)
        embed = medieval_embed(
            title="⚠️ Royal Warning",
            description=f"{member.mention} hath been warned by {ctx.author.mention}!",
            color_name="orange"
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        await ctx.send(embed=embed)
        # Try to DM the user
        try:
            dm_embed = medieval_embed(
                title="⚠️ Royal Warning Received",
                description=f"Thou hast been warned in **{ctx.guild.name}**!",
                color_name="orange"
            )
            dm_embed.add_field(name="Reason", value=reason, inline=False)
            dm_embed.add_field(name="Moderator", value=ctx.author.display_name, inline=False)
            await member.send(embed=dm_embed)
        except:
            pass
    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error issuing warning: {str(e)}", success=False))
@bot.command(name="warnings")
@commands.guild_only()
async def warnings_cmd(ctx, member: discord.Member = None):
    """Check warnings for a subject"""
    try:
        member = member or ctx.author
        warnings = get_warnings(ctx.guild.id, member.id)
        if not warnings:
            return await ctx.send(embed=medieval_response(
                f"{member.display_name} hath a clean record!",
                success=True
            ))
        embed = medieval_embed(
            title=f"⚠️ Warnings for {member.display_name}",
            description=f"Total warnings: **{len(warnings)}**",
            color_name="orange"
        )
        for i, (moderator_id, reason, timestamp) in enumerate(warnings[:5]):
            moderator = ctx.guild.get_member(moderator_id)
            mod_name = moderator.display_name if moderator else f"Moderator {moderator_id}"
            try:
                warn_time = dt.fromisoformat(timestamp).replace(tzinfo=timezone.utc)
                time_str = f"<t:{int(warn_time.timestamp())}:R>"
            except ValueError:
                time_str = "Unknown time"
            embed.add_field(
                name=f"Warning #{i+1}",
                value=f"**By:** {mod_name}\n**When:** {time_str}\n**Reason:** {reason}",
                inline=False
            )
        if len(warnings) > 5:
            embed.add_field(
                name="ℹ️ Note",
                value=f"Showing latest 5 of {len(warnings)} warnings",
                inline=False
            )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error checking warnings: {str(e)}", success=False))
@bot.command(name="clearwarn")
@commands.guild_only()
async def clearwarn_cmd(ctx, member: discord.Member):
    """Clear warnings from a repentant soul"""
    try:
        if not ctx.author.guild_permissions.moderate_members:
            return await ctx.send(embed=medieval_response(
                "Thou hast not the authority to clear warnings!",
                success=False
            ))
        with get_db_connection() as db:
            db.execute("DELETE FROM warnings WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id))
            db.commit()
        await ctx.send(embed=medieval_response(
            f"All warnings for {member.display_name} have been cleared!",
            success=True
        ))
    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error clearing warnings: {str(e)}", success=False))
# Moderation Commands
@bot.command(name="kick")
@commands.guild_only()
async def kick_cmd(ctx, member: discord.Member, *, reason: str = None):
    """Banish a knave from the realm"""
    try:
        if not ctx.author.guild_permissions.kick_members:
            return await ctx.send(embed=medieval_response(
                "Thou hast not the authority to banish souls!",
                success=False
            ))
        if member.id == ctx.author.id:
            return await ctx.send(embed=medieval_response(
                "Thou cannot banish thyself!",
                success=False
            ))
        if member.top_role >= ctx.author.top_role:
            return await ctx.send(embed=medieval_response(
                "Thou cannot banish one of equal or higher station!",
                success=False
            ))
        await member.kick(reason=reason)
        embed = medieval_embed(
            title="⚔️ Banishment",
            description=f"{member.display_name} hath been banished from the realm!",
            color_name="red"
        )
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
        await ctx.send(embed=embed)
        add_moderation_log(ctx.guild.id, ctx.author.id, member.id, "kick", reason or "No reason given")
    except discord.Forbidden:
        await ctx.send(embed=medieval_response(
            "I lack the power to banish this soul!",
            success=False
        ))
    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error banishing: {str(e)}", success=False))
@bot.command(name="ban")
@commands.guild_only()
async def ban_cmd(ctx, member: discord.Member, *, reason: str = None):
    """Permanently exile a criminal"""
    try:
        if not ctx.author.guild_permissions.ban_members:
            return await ctx.send(embed=medieval_response(
                "Thou hast not the authority to exile souls!",
                success=False
            ))
        if member.id == ctx.author.id:
            return await ctx.send(embed=medieval_response(
                "Thou cannot exile thyself!",
                success=False
            ))
        if member.top_role >= ctx.author.top_role:
            return await ctx.send(embed=medieval_response(
                "Thou cannot exile one of equal or higher station!",
                success=False
            ))
        await member.ban(reason=reason)
        embed = medieval_embed(
            title="🔨 Eternal Exile",
            description=f"{member.display_name} hath been forever exiled from the realm!",
            color_name="red"
        )
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
        await ctx.send(embed=embed)
        add_moderation_log(ctx.guild.id, ctx.author.id, member.id, "ban", reason or "No reason given")
    except discord.Forbidden:
        await ctx.send(embed=medieval_response(
            "I lack the power to exile this soul!",
            success=False
        ))
    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error exiling: {str(e)}", success=False))
@bot.command(name="unban")
@commands.guild_only()
async def unban_cmd(ctx, user_id: str, *, reason: str = None):
    """Grant royal pardon to an exile"""
    try:
        if not ctx.author.guild_permissions.ban_members:
            return await ctx.send(embed=medieval_response(
                "Thou hast not the authority to grant pardons!",
                success=False
            ))
        user = await bot.fetch_user(int(user_id))
        await ctx.guild.unban(user, reason=reason)
        embed = medieval_embed(
            title="⚖️ Royal Pardon",
            description=f"{user.display_name} hath been granted pardon and may return to the realm!",
            color_name="green"
        )
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
        await ctx.send(embed=embed)
        add_moderation_log(ctx.guild.id, ctx.author.id, user.id, "unban", reason or "Royal pardon")
    except discord.NotFound:
        await ctx.send(embed=medieval_response(
            "This exile exists not in our records!",
            success=False
        ))
    except ValueError:
        await ctx.send(embed=medieval_response(
            "Provide a valid user ID, good sir!",
            success=False
        ))
    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error granting pardon: {str(e)}", success=False))
@bot.command(name="mute")
@commands.guild_only()
async def mute_cmd(ctx, member: discord.Member, duration_minutes: int, *, reason: str = None):
    """Silence a chatterer for a time"""
    try:
        if not ctx.author.guild_permissions.moderate_members:
            return await ctx.send(embed=medieval_response(
                "Thou hast not the authority to silence souls!",
                success=False
            ))
        if member.id == ctx.author.id:
            return await ctx.send(embed=medieval_response(
                "Thou cannot silence thyself!",
                success=False
            ))
        if member.top_role >= ctx.author.top_role:
            return await ctx.send(embed=medieval_response(
                "Thou cannot silence one of equal or higher station!",
                success=False
            ))
        if duration_minutes < 1 or duration_minutes > 40320: # Max 28 days
            return await ctx.send(embed=medieval_response(
                "Duration must be between 1 and 40320 minutes!",
                success=False
            ))
        duration = timedelta(minutes=duration_minutes)
        await member.timeout(duration, reason=reason)
        embed = medieval_embed(
            title="🔇 Silenced",
            description=f"{member.display_name} hath been silenced for {duration_minutes} minutes!",
            color_name="orange"
        )
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
        await ctx.send(embed=embed)
        add_moderation_log(ctx.guild.id, ctx.author.id, member.id, "mute", reason or f"Muted for {duration_minutes} minutes")
    except discord.Forbidden:
        await ctx.send(embed=medieval_response(
            "I lack the power to silence this soul!",
            success=False
        ))
    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error silencing: {str(e)}", success=False))
@bot.command(name="unmute")
@commands.guild_only()
async def unmute_cmd(ctx, member: discord.Member, *, reason: str = None):
    """Restore voice to the silenced"""
    try:
        if not ctx.author.guild_permissions.moderate_members:
            return await ctx.send(embed=medieval_response(
                "Thou hast not the authority to restore voices!",
                success=False
            ))
        await member.timeout(None, reason=reason)
        embed = medieval_embed(
            title="🔊 Voice Restored",
            description=f"{member.display_name} may speak once more!",
            color_name="green"
        )
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
        await ctx.send(embed=embed)
        add_moderation_log(ctx.guild.id, ctx.author.id, member.id, "unmute", reason or "Mute lifted")
    except discord.Forbidden:
        await ctx.send(embed=medieval_response(
            "I cannot restore this soul's voice!",
            success=False
        ))
    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error restoring voice: {str(e)}", success=False))
@bot.command(name="purge")
@commands.guild_only()
async def purge_cmd(ctx, amount: int):
    """Cleanse the chat of messages"""
    try:
        if not ctx.author.guild_permissions.manage_messages:
            return await ctx.send(embed=medieval_response(
                "Thou hast not the authority to cleanse messages!",
                success=False
            ))
        if amount < 1 or amount > 100:
            return await ctx.send(embed=medieval_response(
                "Thou mayest purge between 1 and 100 messages!",
                success=False
            ))
        deleted = await ctx.channel.purge(limit=amount + 1) # +1 for the command message
        embed = medieval_embed(
            title="🧹 Chat Cleansed",
            description=f"**{len(deleted) - 1}** messages have been purged from the records!",
            color_name="green"
        )
        msg = await ctx.send(embed=embed)
        await asyncio.sleep(5)
        await msg.delete()
    except discord.Forbidden:
        await ctx.send(embed=medieval_response(
            "I lack the power to cleanse these messages!",
            success=False
        ))
    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error cleansing chat: {str(e)}", success=False))
# ---------- CHANNEL LOCK COMMANDS ----------
@bot.command(name="seal")
@commands.guild_only()
async def seal_channel_cmd(ctx, *, reason: str = "By royal decree"):
    """🔒 Seal a channel - prevent sending messages"""
    try:
        if not ctx.author.guild_permissions.manage_channels:
            return await ctx.send(embed=medieval_response(
                "Thou hast not the authority to seal chambers!",
                success=False
            ))
        # Check if channel is already sealed
        existing_lock = is_channel_locked(ctx.guild.id, ctx.channel.id)
        if existing_lock:
            return await ctx.send(embed=medieval_response(
                "This chamber is already sealed by royal decree!",
                success=False
            ))
        # Get the channel's current permissions
        channel = ctx.channel
        everyone_role = ctx.guild.default_role
        # Check current permissions
        current_perms = channel.overwrites_for(everyone_role)
        if current_perms.send_messages is False:
            return await ctx.send(embed=medieval_response(
                "This chamber is already forbidding discourse!",
                success=False
            ))
        # Seal the channel - deny send_messages to @everyone
        try:
            await channel.set_permissions(
                everyone_role,
                send_messages=False,
                reason=f"Channel sealed by {ctx.author.display_name}: {reason}"
            )
        except discord.Forbidden:
            return await ctx.send(embed=medieval_response(
                "I lack the power to seal this chamber!",
                success=False
            ))
        # Record the lock in database
        lock_id = lock_channel(ctx.guild.id, ctx.channel.id, ctx.author.id, reason)
        # Create dramatic announcement
        lock_message = random.choice(MEDIEVAL_LOCK_MESSAGES).format(
            channel=channel.mention,
            moderator=ctx.author.mention,
            reason=reason
        )
        await ctx.send(lock_message)
        # Add moderation log
        add_moderation_log(ctx.guild.id, ctx.author.id, None, "channel_lock", reason)
        # Create follow-up embed with royal seal
        embed = medieval_embed(
            title="🔒 Chamber Sealed",
            description=f"{channel.mention} hath been sealed by royal authority!",
            color_name="red"
        )
        embed.add_field(name="👑 Authority", value=ctx.author.mention, inline=True)
        embed.add_field(name="📜 Reason", value=reason, inline=True)
        embed.set_footer(text="Let none dare speak until the Crown declares otherwise!")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error sealing chamber: {str(e)}", success=False))
@bot.command(name="unseal")
@commands.guild_only()
async def unseal_channel_cmd(ctx, *, reason: str = "By royal mercy"):
    """🔓 Unseal a channel - restore sending messages"""
    try:
        if not ctx.author.guild_permissions.manage_channels:
            return await ctx.send(embed=medieval_response(
                "Thou hast not the authority to unseal chambers!",
                success=False
            ))
        # Check if channel is sealed
        lock_id = is_channel_locked(ctx.guild.id, ctx.channel.id)
        if not lock_id:
            return await ctx.send(embed=medieval_response(
                "This chamber is not sealed!",
                success=False
            ))
        channel = ctx.channel
        everyone_role = ctx.guild.default_role
        # Restore send_messages permission
        try:
            # Reset to default (None means inherit from category/server)
            await channel.set_permissions(
                everyone_role,
                send_messages=None, # Reset to default
                reason=f"Channel unsealed by {ctx.author.display_name}: {reason}"
            )
        except discord.Forbidden:
            return await ctx.send(embed=medieval_response(
                "I lack the power to unseal this chamber!",
                success=False
            ))
        # Update database
        unlock_channel(lock_id, reason)
        # Create dramatic announcement
        unlock_message = random.choice(MEDIEVAL_UNLOCK_MESSAGES).format(
            channel=channel.mention,
            moderator=ctx.author.mention,
            reason=reason
        )
        await ctx.send(unlock_message)
        # Add moderation log
        add_moderation_log(ctx.guild.id, ctx.author.id, None, "channel_unlock", reason)
        # Create follow-up embed with royal seal
        embed = medieval_embed(
            title="🔓 Chamber Unsealed",
            description=f"{channel.mention} is once more open to discourse!",
            color_name="green"
        )
        embed.add_field(name="👑 Mercy", value=ctx.author.mention, inline=True)
        embed.add_field(name="📜 Reason", value=reason, inline=True)
        embed.set_footer(text="Speak freely, but remember the lessons of silence!")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error unsealing chamber: {str(e)}", success=False))
@bot.command(name="sealed")
@commands.guild_only()
async def list_sealed_channels_cmd(ctx):
    """📋 List all sealed channels in the realm"""
    try:
        locked_channels = get_locked_channels(ctx.guild.id)
        if not locked_channels:
            return await ctx.send(embed=medieval_response(
                "No chambers are sealed in this realm!",
                success=True
            ))
        embed = medieval_embed(
            title="🔒 Sealed Chambers",
            description=f"There are **{len(locked_channels)}** chambers sealed by royal decree:",
            color_name="orange"
        )
        for lock_id, channel_id, moderator_id, reason, timestamp in locked_channels:
            channel = ctx.guild.get_channel(channel_id)
            moderator = ctx.guild.get_member(moderator_id)
            if channel and moderator:
                try:
                    lock_time = dt.fromisoformat(timestamp).replace(tzinfo=timezone.utc)
                    time_str = f"<t:{int(lock_time.timestamp())}:R>"
                except ValueError:
                    time_str = "Unknown time"
                embed.add_field(
                    name=f"🔒 {channel.name}",
                    value=f"**Sealed by:** {moderator.mention}\n**When:** {time_str}\n**Reason:** {reason}",
                    inline=False
                )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(embed=medieval_response(f"Error listing sealed chambers: {str(e)}", success=False))
# ---------- SLASH COMMANDS ----------
@tree.command(name="setlogchannel", description="Set the royal chronicle channel for all server logs")
@app_commands.describe(channel="The channel for server chronicles")
@app_commands.guild_only
async def slash_set_log_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    try:
        await interaction.response.defer()
        set_log_channel(interaction.guild.id, channel.id)
        embed = medieval_response(
            f"The royal chronicles shall now be recorded in {channel.mention}!",
            success=True,
            extra="All server activities will be documented henceforth!"
        )
        await interaction.followup.send(embed=embed)
        # Send test log
        test_embed = medieval_embed(
            title="📜 Royal Chronicle Initialized",
            description=f"Chronicle system activated by {interaction.user.mention}!",
            color_name="green"
        )
        test_embed.add_field(name="📺 Channel", value=channel.mention, inline=True)
        test_embed.add_field(name="👑 Authority", value=interaction.user.mention, inline=True)
        test_embed.set_footer(text="All server activities will be recorded henceforth!")
        await channel.send(embed=test_embed)
    except Exception as e:
        await interaction.followup.send(embed=medieval_response(f"Error setting chronicle channel: {str(e)}", success=False))
@tree.command(name="help", description="View the complete royal charter of commands")
@app_commands.guild_only
async def slash_help(interaction: discord.Interaction):
    """Slash command version with comprehensive help"""
    try:
        # Create comprehensive help embed
        embed = medieval_embed(
            title="📜 The Complete Royal Charter",
            description=f"{medieval_greeting()}\n\n**🏰 All Commands Available:**\n\nUse `!help` for full paginated experience with ALL commands!\n\n**Quick Reference:**\n`!pillory` - Public shaming system\n`!setlogchannel` - Configure logging\n`!seal/unseal` - Channel locking\n`!warn/warnings` - Warning system\n`!kick/ban/mute` - Moderation tools\n\n**✨ Features:**\n• Royal decree formatting on all messages\n• Comprehensive logging system\n• Pillory with dramatic announcements\n• Channel sealing/unsealing\n• Warning system with database\n• Full medieval theming with royal seal\n• Both ! and / command support",
            color_name="purple"
        )
        embed.add_field(
            name="⚔️ **Key Systems:**",
            value="**Pillory:** Public shaming with @here announcements\n**Logging:** Complete server activity tracking\n**Moderation:** Kick, ban, mute, purge, warnings\n**Chambers:** Lock/unlock channels with ceremony",
            inline=False
        )
        embed.add_field(
            name="🔧 **Setup Required:**",
            value="`!setlogchannel <channel>` - Enable logging\n`!psetchannel <channel>` - Enable pillory system\n`!pbypass <roles>` - Set immune roles\n`!pallow <roles>` - Set who can use pillory",
            inline=False
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(embed=medieval_response("Error displaying help!", success=False))
@tree.command(name="pillory", description="Place a knave in public shame")
@app_commands.describe(member="The miscreant to pillory", duration="Duration in minutes", reason="The offense committed")
@app_commands.guild_only
async def slash_pillory(interaction: discord.Interaction, member: discord.Member, duration: int, reason: str):
    await interaction.response.defer()
    class MockCtx:
        def __init__(self, interaction):
            self.author = interaction.user
            self.guild = interaction.guild
            self.send = interaction.followup.send
    ctx = MockCtx(interaction)
    await pillory_cmd(ctx, member, duration, reason=reason)
@tree.command(name="pbypass", description="Set roles immune to pillory punishment")
@app_commands.describe(roles="The roles to grant bypass privilege (mention them)")
@app_commands.guild_only
async def slash_pbypass(interaction: discord.Interaction, roles: str):
    await interaction.response.defer()
    try:
        # Parse role mentions from the string input
        role_ids = []
        for mention in roles.split():
            if "<@&" in mention and ">" in mention:
                try:
                    role_id = int(mention.strip("<@&>"))
                    role_ids.append(role_id)
                except ValueError:
                    continue
        if not role_ids:
            return await interaction.followup.send(embed=medieval_response(
                "Please mention valid roles!",
                success=False
            ))
        discord_roles = []
        for role_id in role_ids:
            role = interaction.guild.get_role(role_id)
            if role:
                discord_roles.append(role)
        if not discord_roles:
            return await interaction.followup.send(embed=medieval_response(
                "No valid roles found!",
                success=False
            ))
        # Set bypass roles
        role_ids = [r.id for r in discord_roles]
        set_pillory_bypass_roles(interaction.guild.id, role_ids)
        role_mentions = " ".join(r.mention for r in discord_roles)
        embed = medieval_embed(
            title="👑 Royal Bypass Privilege",
            description=f"The following roles now possess royal immunity: {role_mentions}",
            color_name="purple"
        )
        embed.add_field(
            name="⚔️ Privilege Granted",
            value="Holders of these roles shall never face the shame of the pillory!",
            inline=False
        )
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(embed=medieval_response(f"Error setting bypass roles: {str(e)}", success=False))
@tree.command(name="pallow", description="Set roles allowed to use pillory commands")
@app_commands.describe(roles="The roles to grant pillory privileges (mention them)")
@app_commands.guild_only
async def slash_pallow(interaction: discord.Interaction, roles: str):
    await interaction.response.defer()
    try:
        # Parse role mentions from the string input
        role_ids = []
        for mention in roles.split():
            if "<@&" in mention and ">" in mention:
                try:
                    role_id = int(mention.strip("<@&>"))
                    role_ids.append(role_id)
                except ValueError:
                    continue
        if not role_ids:
            return await interaction.followup.send(embed=medieval_response(
                "Please mention valid roles!",
                success=False
            ))
        discord_roles = []
        for role_id in role_ids:
            role = interaction.guild.get_role(role_id)
            if role:
                discord_roles.append(role)
        if not discord_roles:
            return await interaction.followup.send(embed=medieval_response(
                "No valid roles found!",
                success=False
            ))
        # Set allowed roles
        role_ids = [r.id for r in discord_roles]
        set_pillory_allowed_roles(interaction.guild.id, role_ids)
        role_mentions = " ".join(r.mention for r in discord_roles)
        embed = medieval_embed(
            title="⚔️ Royal Pillory Privileges",
            description=f"The following roles now command the power of the pillory: {role_mentions}",
            color_name="purple"
        )
        embed.add_field(
            name="🏰 Authority Bestowed",
            value="Only these chosen roles may condemn souls to public shame!",
            inline=False
        )
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(embed=medieval_response(f"Error setting allowed roles: {str(e)}", success=False))
@tree.command(name="pbypasslist", description="List roles with pillory bypass privilege")
@app_commands.guild_only
async def slash_pbypasslist(interaction: discord.Interaction):
    await interaction.response.defer()
    class MockCtx:
        def __init__(self, interaction):
            self.author = interaction.user
            self.guild = interaction.guild
            self.send = interaction.followup.send
    ctx = MockCtx(interaction)
    await list_pillory_bypass_roles_cmd(ctx)
@tree.command(name="pallowlist", description="List roles allowed to use pillory commands")
@app_commands.guild_only
async def slash_pallowlist(interaction: discord.Interaction):
    await interaction.response.defer()
    class MockCtx:
        def __init__(self, interaction):
            self.author = interaction.user
            self.guild = interaction.guild
            self.send = interaction.followup.send
    ctx = MockCtx(interaction)
    await list_pillory_allowed_roles_cmd(ctx)
@tree.command(name="pillories", description="View active pillories in the realm")
@app_commands.guild_only
async def slash_pillories(interaction: discord.Interaction):
    await interaction.response.defer()
    class MockCtx:
        def __init__(self, interaction):
            self.author = interaction.user
            self.guild = interaction.guild
            self.send = interaction.followup.send
    ctx = MockCtx(interaction)
    await list_pillories(ctx)
@tree.command(name="pardon", description="Show mercy and end a pillory early")
@app_commands.describe(pillory_id="The ID of the pillory to end")
@app_commands.guild_only
async def slash_pardon(interaction: discord.Interaction, pillory_id: int):
    await interaction.response.defer()
    class MockCtx:
        def __init__(self, interaction):
            self.author = interaction.user
            self.guild = interaction.guild
            self.send = interaction.followup.send
    ctx = MockCtx(interaction)
    await pardon_cmd(ctx, pillory_id)
@tree.command(name="warn", description="Issue a warning to a miscreant")
@app_commands.describe(member="The member to warn", reason="The reason for the warning")
@app_commands.guild_only
async def slash_warn(interaction: discord.Interaction, member: discord.Member, reason: str):
    await interaction.response.defer()
    class MockCtx:
        def __init__(self, interaction):
            self.author = interaction.user
            self.guild = interaction.guild
            self.send = interaction.followup.send
    ctx = MockCtx(interaction)
    await warn_cmd(ctx, member, reason=reason)
@tree.command(name="warnings", description="Check warnings for a subject")
@app_commands.describe(member="The member to check (optional)")
@app_commands.guild_only
async def slash_warnings(interaction: discord.Interaction, member: discord.Member = None):
    await interaction.response.defer()
    class MockCtx:
        def __init__(self, interaction):
            self.author = interaction.user
            self.guild = interaction.guild
            self.send = interaction.followup.send
    ctx = MockCtx(interaction)
    await warnings_cmd(ctx, member=member)
@tree.command(name="kick", description="Banish a knave from the realm")
@app_commands.describe(member="The member to kick", reason="The reason for banishment")
@app_commands.guild_only
async def slash_kick(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    await interaction.response.defer()
    class MockCtx:
        def __init__(self, interaction):
            self.author = interaction.user
            self.guild = interaction.guild
            self.send = interaction.followup.send
    ctx = MockCtx(interaction)
    await kick_cmd(ctx, member, reason=reason)
@tree.command(name="ban", description="Permanently exile a criminal")
@app_commands.describe(member="The member to ban", reason="The reason for exile")
@app_commands.guild_only
async def slash_ban(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    await interaction.response.defer()
    class MockCtx:
        def __init__(self, interaction):
            self.author = interaction.user
            self.guild = interaction.guild
            self.send = interaction.followup.send
    ctx = MockCtx(interaction)
    await ban_cmd(ctx, member, reason=reason)
@tree.command(name="mute", description="Silence a chatterer for a time")
@app_commands.describe(member="The member to mute", duration="Duration in minutes", reason="The reason for silence")
@app_commands.guild_only
async def slash_mute(interaction: discord.Interaction, member: discord.Member, duration: int, reason: str = None):
    await interaction.response.defer()
    class MockCtx:
        def __init__(self, interaction):
            self.author = interaction.user
            self.guild = interaction.guild
            self.send = interaction.followup.send
    ctx = MockCtx(interaction)
    await mute_cmd(ctx, member, duration, reason=reason)
@tree.command(name="purge", description="Cleanse the chat of messages")
@app_commands.describe(amount="Number of messages to purge (1-100)")
@app_commands.guild_only
async def slash_purge(interaction: discord.Interaction, amount: int):
    await interaction.response.defer()
    class MockCtx:
        def __init__(self, interaction):
            self.author = interaction.user
            self.guild = interaction.guild
            self.send = interaction.followup.send
    ctx = MockCtx(interaction)
    await purge_cmd(ctx, amount)
@tree.command(name="seal", description="🔒 Seal a channel to prevent sending messages")
@app_commands.describe(reason="The reason for sealing this chamber")
@app_commands.guild_only
async def slash_seal(interaction: discord.Interaction, reason: str = "By royal decree"):
    await interaction.response.defer()
    class MockCtx:
        def __init__(self, interaction):
            self.author = interaction.user
            self.guild = interaction.guild
            self.channel = interaction.channel
            self.send = interaction.followup.send
    ctx = MockCtx(interaction)
    await seal_channel_cmd(ctx, reason=reason)
@tree.command(name="unseal", description="🔓 Unseal a channel to restore sending messages")
@app_commands.describe(reason="The reason for unsealing this chamber")
@app_commands.guild_only
async def slash_unseal(interaction: discord.Interaction, reason: str = "By royal mercy"):
    await interaction.response.defer()
    class MockCtx:
        def __init__(self, interaction):
            self.author = interaction.user
            self.guild = interaction.guild
            self.channel = interaction.channel
            self.send = interaction.followup.send
    ctx = MockCtx(interaction)
    await unseal_channel_cmd(ctx, reason=reason)
@tree.command(name="sealed", description="📋 View all sealed channels in the realm")
@app_commands.guild_only
async def slash_sealed(interaction: discord.Interaction):
    await interaction.response.defer()
    class MockCtx:
        def __init__(self, interaction):
            self.author = interaction.user
            self.guild = interaction.guild
            self.send = interaction.followup.send
    ctx = MockCtx(interaction)
    await list_sealed_channels_cmd(ctx)
# ---------- ON READY ----------
@bot.event
async def on_ready():
    try:
        print(f'⚔️ Medieval Moderator Bot hath awakened as {bot.user} (ID: {bot.user.id})')
        print('🎯 Enhanced pillory system ready for dramatic public shaming!')
        print('📜 Royal
