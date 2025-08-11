# PomoAllos Discord Bot

## Overview

PomoAllos is a Discord bot designed to automatically track focus time using Pomodoro cycles and stopwatch functionality based on voice channel presence. The bot monitors when users join specific voice channels and automatically initiates time tracking sessions - either structured 25-minute Pomodoro cycles with breaks or continuous stopwatch sessions. The system supports multiple concurrent user sessions with real-time updates through Discord embeds and automatic cleanup when users leave channels.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Bot Framework
- **Discord.py Library**: Uses the discord.py library with command extensions for Discord API interaction
- **Event-driven Architecture**: Primarily operates through Discord event listeners (voice state changes) rather than traditional commands
- **Asynchronous Processing**: Built on asyncio for handling multiple concurrent user sessions without blocking

### Session Management
- **User Task Tracking**: Maintains two dictionaries (`user_tasks` and `user_data`) to track active sessions and user state
- **Automatic Session Detection**: Monitors voice channel join/leave events to start/stop sessions automatically
- **Concurrent Sessions**: Supports multiple users running different session types simultaneously
- **Session Cleanup**: Automatic cleanup when users disconnect from monitored channels

### Time Tracking Modes
- **Pomodoro Mode**: Implements traditional 25-minute focus/5-minute break cycles with automatic progression
- **Stopwatch Mode**: Continuous time tracking with real-time second-by-second updates
- **All Sessions Counted**: All sessions are tracked and celebrated regardless of duration

### User Interface
- **Portuguese Motivational Messages**: Custom Portuguese messages for progress and completion
- **Rich Discord Embeds**: Uses Discord's embed system for visually appealing status messages
- **Real-time Updates**: Different update intervals for each mode (10s for Pomodoro, 1s for Stopwatch)
- **User Avatar Integration**: Displays user avatars in status embeds for personalization
- **Text Channel Announcements**: Messages sent to appropriate text channels for accessibility
- **Progress Messages**: "Continue firme, {user}! Você está progredindo — mantenha o foco e aproveite ao máximo esta sessão!"
- **Completion Messages**: "Parabéns, {user}! Você manteve o foco por {tempo} — ótimo trabalho investindo em você mesmo(a)!"

### Configuration Management
- **Environment Variables**: Uses environment variables for sensitive bot token storage
- **Hardcoded Channel IDs**: Voice and text channel IDs are configured directly in the code
- **Configurable Time Intervals**: Separate constants for session durations and update frequencies

## External Dependencies

### Discord Platform
- **Discord API**: Core dependency through discord.py library for all bot functionality
- **Discord Gateway**: Real-time event streaming for voice state changes
- **Discord Permissions**: Requires specific permissions (View Channels, Send Messages, Embed Links, Read Message History, Connect)

### Runtime Environment
- **Python Runtime**: Requires Python environment with asyncio support
- **Environment Variables**: Depends on `DISCORD_BOT_TOKEN` environment variable
- **Discord.py Library**: Third-party library for Discord API interactions

### Voice Channel Integration
- **Voice State Monitoring**: Monitors user presence in specific voice channels
- **Channel-specific Triggers**: Different voice channels trigger different tracking modes
- **Real-time Voice Events**: Responds to join/leave events for automatic session management