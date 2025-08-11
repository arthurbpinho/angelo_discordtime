# bot_pomoallos.py
import discord
from discord.ext import commands
import asyncio
import datetime
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv() # Carrega as variáveis do arquivo .env

TOKEN = os.getenv('DISCORD_TOKEN')

# O resto do seu código que usa a variável TOKEN...
# client.run(TOKEN)

# IDs conforme solicitado
POMODORO_VOICE_ID = 1403754766240190534    # canal de voz que ativa Pomodoro (ciclos)
POMODORO_ANNOUNCE_CHANNEL_ID = 1403769071887061165  # canal de texto para mensagens do Pomodoro

STOPWATCH_VOICE_ID = 1403761579736043593   # canal de voz que ativa Cronômetro
STOPWATCH_ANNOUNCE_CHANNEL_ID = 1403769071887061165  # canal de texto para mensagens do Cronômetro

# Tempo (em segundos)
POMODORO_FOCUS = 25 * 60
POMODORO_BREAK = 5 * 60


# Intervals
POMODORO_UPDATE_INTERVAL = 10   # atualiza a cada 10s durante Pomodoro
STOPWATCH_UPDATE_INTERVAL = 1   # atualiza a cada 1s no cronômetro

BOT_DISPLAY_NAME = "PomoAllos"
# -----------------------------------

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.guild_messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

# controle de sessões ativas
user_tasks = {}   # member.id -> asyncio.Task
user_data = {}    # member.id -> dict com info (start_time, focused_seconds, mode, message, ...)

# --- utilitários ---
def make_embed(title: str, description: str, color: int, member: Optional[discord.Member] = None, footer_text: Optional[str] = None):
    e = discord.Embed(title=f"{BOT_DISPLAY_NAME} — {title}", description=description, color=color)
    if member:
        try:
            e.set_thumbnail(url=str(member.display_avatar.url))
        except Exception:
            pass
    if footer_text:
        e.set_footer(text=footer_text)
    return e

def fmt_hms(total_seconds: int):
    m = total_seconds // 60
    s = total_seconds % 60
    return f"{m}m {s}s"

def get_announcement_channel(guild: discord.Guild, channel_id: int) -> Optional[discord.TextChannel]:
    """Get the text channel for announcements - try the channel ID first, then find a suitable text channel"""
    # First try the exact channel ID if it's a text channel
    ch = guild.get_channel(channel_id)
    print(f"DEBUG: Channel {channel_id} found: {ch}, type: {type(ch)}")
    
    if ch and isinstance(ch, discord.TextChannel):
        print(f"DEBUG: Using specified text channel: {ch.name}")
        return ch
    
    # If the channel ID points to a voice channel, look for a text channel in the same category
    if ch and hasattr(ch, 'category') and ch.category:
        for text_ch in ch.category.text_channels:
            if text_ch.permissions_for(guild.me).send_messages:
                print(f"DEBUG: Using text channel from same category: {text_ch.name}")
                return text_ch
    
    # Fallback to system channel or first available text channel
    if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
        print(f"DEBUG: Using system channel: {guild.system_channel.name}")
        return guild.system_channel
    
    # Last resort: find any text channel where bot can send messages
    for text_ch in guild.text_channels:
        if text_ch.permissions_for(guild.me).send_messages:
            print(f"DEBUG: Using fallback text channel: {text_ch.name}")
            return text_ch
    
    print("DEBUG: No suitable text channel found")
    return None

# --- eventos ---
@bot.event
async def on_ready():
    print(f"{bot.user} online — {BOT_DISPLAY_NAME} pronto!")

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    # Ignora bots
    if member.bot:
        return

    before_id = before.channel.id if before.channel else None
    after_id = after.channel.id if after.channel else None
    
    print(f"DEBUG: Voice state update - {member.display_name}")
    print(f"DEBUG: Before channel: {before_id}, After channel: {after_id}")
    print(f"DEBUG: Pomodoro channel ID: {POMODORO_VOICE_ID}")
    print(f"DEBUG: Stopwatch channel ID: {STOPWATCH_VOICE_ID}")

    # Entrou no canal Pomodoro
    if after_id == POMODORO_VOICE_ID and before_id != POMODORO_VOICE_ID:
        if member.id in user_tasks:
            await stop_session(member, reason="mudou de canal")
        await start_pomodoro(member, after.channel)

    # Saiu do canal Pomodoro
    if before_id == POMODORO_VOICE_ID and after_id != POMODORO_VOICE_ID:
        if member.id in user_tasks and user_data.get(member.id, {}).get("mode") == "pomodoro":
            await stop_session(member, reason="saiu do canal")

    # Entrou no canal Cronômetro (stopwatch)
    if after_id == STOPWATCH_VOICE_ID and before_id != STOPWATCH_VOICE_ID:
        if member.id in user_tasks:
            await stop_session(member, reason="mudou de canal")
        await start_stopwatch(member, after.channel)

    # Saiu do canal Cronômetro
    if before_id == STOPWATCH_VOICE_ID and after_id != STOPWATCH_VOICE_ID:
        if member.id in user_tasks and user_data.get(member.id, {}).get("mode") == "stopwatch":
            await stop_session(member, reason="saiu do canal")

# ---------------- Pomodoro ----------------
async def start_pomodoro(member: discord.Member, voice_channel):
    announce = get_announcement_channel(member.guild, POMODORO_ANNOUNCE_CHANNEL_ID)
    print(f"DEBUG: Pomodoro announcement channel: {announce}")
    if announce is None:
        print(f"DEBUG: Could not find text channel with ID {POMODORO_ANNOUNCE_CHANNEL_ID}")
        # Try to find any text channel in the guild
        for channel in member.guild.text_channels:
            if channel.permissions_for(member.guild.me).send_messages:
                announce = channel
                print(f"DEBUG: Using fallback text channel: {announce.name} ({announce.id})")
                break
        if announce is None:
            print("DEBUG: No text channels found where bot can send messages")
            return

    start_time = datetime.datetime.utcnow()
    user_data[member.id] = {
        "start_time": start_time,
        "focused_seconds": 0,
        "mode": "pomodoro",
        "voice_channel": voice_channel.id,
        "cycle_phase": "focus"  # "focus" ou "break"
    }

    # Envia a mensagem de progresso inicial
    embed = make_embed(
        title="📚 Sessão de Foco Iniciada",
        description=f"Continue firme, {member.display_name}! Você está progredindo — mantenha o foco e aproveite ao máximo esta sessão!",
        color=0x0055AA,  # azul enquanto foca
        member=member,
        footer_text="Pomodoro em andamento"
    )
    try:
        msg = await announce.send(content=f"{member.mention}", embed=embed)
    except discord.Forbidden:
        return

    user_data[member.id]["message"] = msg
    task = asyncio.create_task(pomodoro_loop(member, announce))
    user_tasks[member.id] = task

async def pomodoro_loop(member: discord.Member, announce_channel: discord.TextChannel):
    member_id = member.id
    focused = 0
    try:
        while True:
            # ===== FASE DE FOCO =====
            user_data[member_id]["cycle_phase"] = "focus"
            focus_start = datetime.datetime.utcnow()
            phase_end = focus_start + datetime.timedelta(seconds=POMODORO_FOCUS)
            msg = user_data[member_id].get("message")

            while True:
                now = datetime.datetime.utcnow()
                if now >= phase_end:
                    # ciclo completo
                    focused += POMODORO_FOCUS
                    user_data[member_id]["focused_seconds"] = focused
                    break

                remaining = int((phase_end - now).total_seconds())
                elapsed_focus_partial = int((now - focus_start).total_seconds())

                # Atualiza embed de progresso
                embed = make_embed(
                    title="📚 Foco em Andamento",
                    description=f"Continue firme, {member.display_name}! Você está progredindo — mantenha o foco e aproveite ao máximo esta sessão!",
                    color=0x0055AA,
                    member=member,
                    footer_text=f"Tempo de foco: {fmt_hms(elapsed_focus_partial)} · Restam: {fmt_hms(remaining)}"
                )
                try:
                    await msg.edit(content=f"{member.mention}", embed=embed)
                except (discord.NotFound, discord.Forbidden):
                    # Se a mensagem foi apagada ou não for possível editar, envia uma nova
                    msg = await announce_channel.send(content=f"{member.mention}", embed=embed)
                    user_data[member_id]["message"] = msg

                # espera UPDATE_INTERVAL ou até cancelamento
                try:
                    await asyncio.sleep(POMODORO_UPDATE_INTERVAL)
                except asyncio.CancelledError:
                    # saiu durante foco -> contabiliza parcial
                    now2 = datetime.datetime.utcnow()
                    elapsed_partial = int((now2 - focus_start).total_seconds())
                    focused += elapsed_partial
                    user_data[member_id]["focused_seconds"] = focused
                    raise

            # Ao completar foco -> notifica pausa
            user_data[member_id]["focused_seconds"] = focused
            try:
                embed = make_embed(
                    title="✅ Ciclo de Foco Concluído",
                    description=f"Hora de pausar por {POMODORO_BREAK//60} minutos, {member.display_name}!",
                    color=0x888888,
                    member=member,
                    footer_text="Pausa iniciada"
                )
                await announce_channel.send(content=f"{member.mention}", embed=embed)
            except discord.Forbidden:
                pass

            # ===== FASE DE PAUSA =====
            pause_start = datetime.datetime.utcnow()
            pause_end = pause_start + datetime.timedelta(seconds=POMODORO_BREAK)
            user_data[member_id]["cycle_phase"] = "break"

            while True:
                now = datetime.datetime.utcnow()
                if now >= pause_end:
                    break
                remaining_pause = int((pause_end - now).total_seconds())
                elapsed_pause = int((now - pause_start).total_seconds())

                embed = make_embed(
                    title="⏸️ Pausa em Andamento",
                    description=f"Descanse um pouco, {member.display_name}! Volta em {fmt_hms(remaining_pause)}",
                    color=0x888888,  # cinza para pausa
                    member=member,
                    footer_text=f"Tempo de pausa: {fmt_hms(elapsed_pause)} · Restam: {fmt_hms(remaining_pause)}"
                )
                msg = user_data[member_id].get("message")
                try:
                    await msg.edit(content=f"{member.mention}", embed=embed)
                except (discord.NotFound, discord.Forbidden):
                    msg = await announce_channel.send(content=f"{member.mention}", embed=embed)
                    user_data[member_id]["message"] = msg

                try:
                    await asyncio.sleep(POMODORO_UPDATE_INTERVAL)
                except asyncio.CancelledError:
                    # cancelado durante pausa: não contabiliza pausa
                    raise

            # pausa finalizada -> notifica retorno ao foco
            try:
                embed = make_embed(
                    title="⏰ Pausa Finalizada",
                    description=f"Hora de voltar ao foco, {member.display_name}!",
                    color=0x0055AA,
                    member=member,
                    footer_text="Novo ciclo de foco iniciado"
                )
                await announce_channel.send(content=f"{member.mention}", embed=embed)
            except discord.Forbidden:
                pass

            # loop continua para próximo ciclo automático

    except asyncio.CancelledError:
        # Sessão interrompida (usuário saiu do canal ou mudou)
        end_time = datetime.datetime.utcnow()
        total_focused = user_data.get(member_id, {}).get("focused_seconds", focused)

        # Envia mensagem de conclusão personalizada
        embed = make_embed(
            title="🎉 Sessão Finalizada",
            description=f"Parabéns, {member.display_name}! Você manteve o foco por {fmt_hms(total_focused)} — ótimo trabalho investindo em você mesmo(a)!",
            color=0x22AA55,  # verde final
            member=member,
            footer_text="Sessão de Pomodoro finalizada"
        )
        try:
            await announce_channel.send(content=f"{member.mention}", embed=embed)
        except discord.Forbidden:
            pass

        # limpeza
        user_tasks.pop(member_id, None)
        user_data.pop(member_id, None)
        return

# ---------------- Cronômetro (stopwatch) ----------------
async def start_stopwatch(member: discord.Member, voice_channel):
    announce = get_announcement_channel(member.guild, STOPWATCH_ANNOUNCE_CHANNEL_ID)
    print(f"DEBUG: Stopwatch announcement channel: {announce}")
    if announce is None:
        print(f"DEBUG: Could not find text channel with ID {STOPWATCH_ANNOUNCE_CHANNEL_ID}")
        # Try to find any text channel in the guild
        for channel in member.guild.text_channels:
            if channel.permissions_for(member.guild.me).send_messages:
                announce = channel
                print(f"DEBUG: Using fallback text channel: {announce.name} ({announce.id})")
                break
        if announce is None:
            print("DEBUG: No text channels found where bot can send messages")
            return

    start_time = datetime.datetime.utcnow()
    user_data[member.id] = {
        "start_time": start_time,
        "mode": "stopwatch",
        "voice_channel": voice_channel.id,
        "elapsed_seconds": 0
    }

    # Envia a mensagem inicial de progresso
    embed = make_embed(
        title="📚 Cronômetro Iniciado",
        description=f"Continue firme, {member.display_name}! Você está progredindo — mantenha o foco e aproveite ao máximo esta sessão!",
        color=0x0044AA,  # cor enquanto cronômetro roda
        member=member,
        footer_text="Cronômetro em andamento"
    )
    try:
        msg = await announce.send(content=f"{member.mention}", embed=embed)
    except discord.Forbidden:
        return
    user_data[member.id]["message"] = msg

    task = asyncio.create_task(stopwatch_loop(member, announce))
    user_tasks[member.id] = task

async def stopwatch_loop(member: discord.Member, announce_channel: discord.TextChannel):
    member_id = member.id
    try:
        while True:
            start_time = user_data[member_id]["start_time"]
            now = datetime.datetime.utcnow()
            elapsed_seconds = int((now - start_time).total_seconds())
            user_data[member_id]["elapsed_seconds"] = elapsed_seconds

            # Atualiza mensagem com tempo decorrido
            embed = make_embed(
                title="📚 Cronômetro em Andamento",
                description=f"Continue firme, {member.display_name}! Você está progredindo — mantenha o foco e aproveite ao máximo esta sessão!",
                color=0x0044AA,
                member=member,
                footer_text=f"Tempo decorrido: {fmt_hms(elapsed_seconds)}"
            )

            msg = user_data[member_id].get("message")
            try:
                await msg.edit(content=f"{member.mention}", embed=embed)
            except (discord.NotFound, discord.Forbidden):
                # Se a mensagem foi apagada ou não for possível editar, envia uma nova
                msg = await announce_channel.send(content=f"{member.mention}", embed=embed)
                user_data[member_id]["message"] = msg

            # Aguarda próxima atualização
            await asyncio.sleep(STOPWATCH_UPDATE_INTERVAL)

    except asyncio.CancelledError:
        # Cronômetro interrompido
        end_time = datetime.datetime.utcnow()
        start_time = user_data.get(member_id, {}).get("start_time", end_time)
        total_seconds = int((end_time - start_time).total_seconds())

        # Finaliza cronômetro com mensagem de conclusão personalizada
        embed = make_embed(
            title="🎉 Cronômetro Finalizado",
            description=f"Parabéns, {member.display_name}! Você manteve o foco por {fmt_hms(total_seconds)} — ótimo trabalho investindo em você mesmo(a)!",
            color=0x22AA55,  # verde final
            member=member,
            footer_text="Sessão de cronômetro finalizada"
        )
        try:
            await announce_channel.send(content=f"{member.mention}", embed=embed)
        except discord.Forbidden:
            pass

        # limpeza
        user_tasks.pop(member_id, None)
        user_data.pop(member_id, None)
        return

# ---------------- Utilitário de parada de sessão ----------------
async def stop_session(member: discord.Member, reason: str = ""):
    """Para qualquer sessão ativa do usuário"""
    if member.id in user_tasks:
        task = user_tasks[member.id]
        task.cancel()
        # A limpeza será feita no except asyncio.CancelledError de cada loop
        try:
            await task
        except asyncio.CancelledError:
            pass

# ---------------- Comandos opcionais ----------------
@bot.command(name="status")
async def status_command(ctx):
    """Comando para verificar sessões ativas"""
    if not user_data:
        await ctx.send("Nenhuma sessão ativa no momento.")
        return
    
    active_sessions = []
    for member_id, data in user_data.items():
        member = ctx.guild.get_member(member_id)
        if member:
            mode = data.get("mode", "unknown")
            start_time = data.get("start_time")
            if start_time:
                elapsed = int((datetime.datetime.utcnow() - start_time).total_seconds())
                active_sessions.append(f"• {member.display_name}: {mode} ({fmt_hms(elapsed)})")
    
    if active_sessions:
        embed = make_embed(
            title="Sessões Ativas",
            description="\n".join(active_sessions),
            color=0x0055AA
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send("Nenhuma sessão ativa no momento.")

@bot.command(name="info")
async def info_command(ctx):
    """Comando de informações sobre o bot"""
    embed = make_embed(
        title="Como usar o PomoAllos",
        description=(
            "🍅 **Pomodoro**: Entre no canal de voz configurado para iniciar ciclos automáticos de 25min foco + 5min pausa\n"
            "⏱️ **Cronômetro**: Entre no outro canal de voz configurado para cronometrar tempo livre\n"
            "📊 **Comandos**:\n"
            "• `!status` - Ver sessões ativas\n"
            "• `!info` - Esta mensagem\n"
            "• `!debug` - Verificar configuração dos canais\n\n"
            "O bot detecta automaticamente quando você entra/sai dos canais!"
        ),
        color=0x0055AA
    )
    await ctx.send(embed=embed)

@bot.command(name="debug")
async def debug_command(ctx):
    """Comando para debugar configuração dos canais"""
    guild = ctx.guild
    
    # Check Pomodoro channels
    pomodoro_voice = guild.get_channel(POMODORO_VOICE_ID)
    pomodoro_announce = get_announcement_channel(guild, POMODORO_ANNOUNCE_CHANNEL_ID)
    
    # Check Stopwatch channels  
    stopwatch_voice = guild.get_channel(STOPWATCH_VOICE_ID)
    stopwatch_announce = get_announcement_channel(guild, STOPWATCH_ANNOUNCE_CHANNEL_ID)
    
    debug_info = []
    debug_info.append(f"**Configuração dos Canais:**")
    debug_info.append(f"Pomodoro Voice: {pomodoro_voice.name if pomodoro_voice else 'Não encontrado'} ({POMODORO_VOICE_ID})")
    debug_info.append(f"Pomodoro Text: {pomodoro_announce.name if pomodoro_announce else 'Não encontrado'} ({POMODORO_ANNOUNCE_CHANNEL_ID})")
    debug_info.append(f"Stopwatch Voice: {stopwatch_voice.name if stopwatch_voice else 'Não encontrado'} ({STOPWATCH_VOICE_ID})")  
    debug_info.append(f"Stopwatch Text: {stopwatch_announce.name if stopwatch_announce else 'Não encontrado'} ({STOPWATCH_ANNOUNCE_CHANNEL_ID})")
    
    debug_info.append(f"\n**Permissões do Bot:**")
    if pomodoro_announce:
        perms = pomodoro_announce.permissions_for(guild.me)
        debug_info.append(f"Send Messages (Pomodoro): {perms.send_messages}")
        debug_info.append(f"Embed Links (Pomodoro): {perms.embed_links}")
    
    await ctx.send("\n".join(debug_info))

# ---------------- Inicialização ----------------
if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("❌ Token inválido! Verifique a variável DISCORD_BOT_TOKEN")
    except Exception as e:
        print(f"❌ Erro ao iniciar o bot: {e}")
