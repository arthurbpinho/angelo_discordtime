# PomoAllos Discord Bot

A Discord bot that automatically tracks focus time with Pomodoro cycles and stopwatch functionality based on voice channel presence.

## Features

- **Automatic Session Detection**: Bot automatically detects when users join/leave specific voice channels
- **Pomodoro Timer**: 25-minute focus sessions with 5-minute breaks in automatic cycles
- **Stopwatch Mode**: Continuous time tracking for flexible work sessions
- **Real-time Updates**: Live message updates showing current session progress
- **User-specific Sessions**: Multiple users can run sessions concurrently
- **Rich Portuguese Embeds**: Beautiful Discord embeds with user avatars and motivational messages in Portuguese
- **Session Management**: Automatic cleanup when users leave channels
- **Custom Motivational Messages**: Personalized progress and completion messages

## Setup

1. **Environment Variable**: Set your Discord bot token as `DISCORD_BOT_TOKEN`
   ```bash
   export DISCORD_BOT_TOKEN="your_bot_token_here"
   ```

2. **Channel Configuration**: Update the channel IDs in `bot.py`:
   - `POMODORO_VOICE_ID`: Voice channel for Pomodoro sessions
   - `STOPWATCH_VOICE_ID`: Voice channel for stopwatch sessions
   - `POMODORO_ANNOUNCE_CHANNEL_ID`: Text channel for Pomodoro announcements
   - `STOPWATCH_ANNOUNCE_CHANNEL_ID`: Text channel for stopwatch announcements

3. **Bot Permissions**: Ensure your bot has these permissions:
   - View Channels
   - Send Messages
   - Embed Links
   - Read Message History
   - Connect (for voice channel monitoring)

## Usage

### Pomodoro Mode
1. Join the designated Pomodoro voice channel
2. Bot automatically starts a 25-minute focus session
3. After 25 minutes, bot announces a 5-minute break
4. Cycles continue automatically while you remain in the channel
5. Leave the channel to end your session

### Stopwatch Mode
1. Join the designated stopwatch voice channel
2. Bot starts counting time immediately
3. Time updates every second in real-time
4. Leave the channel to stop the stopwatch

### Commands
- `!status` - View all active sessions
- `!info` - Display help information and usage instructions

## Configuration

### Timing Settings
```python
POMODORO_FOCUS = 25 * 60        # 25 minutes focus time
POMODORO_BREAK = 5 * 60         # 5 minutes break time
POMODORO_UPDATE_INTERVAL = 10   # Update progress every 10 seconds for Pomodoro
STOPWATCH_UPDATE_INTERVAL = 1   # Update progress every 1 second for Stopwatch
