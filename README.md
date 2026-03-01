# Discord Behavioral Analysis Bot

A Discord bot that analyzes how people talk in a server. It looks at someone's messages and figures out their "communication style" - things like how chaotic they are, how toxic, how eloquent, etc. Then it gives them an archetype, a radar chart, and if you want, a roast.

It uses Groq (which runs Llama 3.3 70B) to do the actual analysis, so it's not just counting words - it reads the conversations in context and tries to understand what people actually meant.

---

## What it does

- **/analyze** - Picks a user and analyzes their last X messages. Gives them a behavioral profile with scores across 6 dimensions and a radar chart image.
- **/roast** - Same analysis but Dr. Unhinged writes a personalized roast based on their actual messages and conversation history.
- **/compare** - Puts two users head to head with a side-by-side radar chart and score comparison.
- **/leaderboard** - Ranks everyone active in the channel by a chosen metric (chaos, toxicity, eloquence, social score).

---

## How the analysis works

For each user it collects their recent messages, but it also grabs the 5 messages before each of theirs so it knows what they were responding to. If someone sends 3 messages in a row, those get grouped into one "turn" so the AI understands it as one continuous thought.

The AI then scores them on:

| Score | What it measures |
|---|---|
| Chaos | How erratic and unpredictable their messages are |
| Toxicity | How hostile or aggressive (in context - jokes don't count) |
| Eloquence | How articulate and vocabulary-rich |
| Expressiveness | Emojis, exclamation marks, emotional intensity |
| Social | How conversational - mentions, questions, back-and-forth |
| Consistency | How uniform their style is across messages |

Based on those scores it assigns one of 8 archetypes:

- 🌪️ The Chaos Goblin
- ☠️ The Toxic Oracle
- 🧠 The Discord Philosopher
- 🦖 The Emoji Archaeologist
- 👁️ The Lurker Lord
- 🦋 The Social Butterfly
- 📖 The Consistent Narrator
- 😐 The Average Enjoyer

---

## Setup

### Requirements

- Python 3.10+
- A Discord bot token
- A Groq API key (free at [console.groq.com](https://console.groq.com))

### Install dependencies

```bash
pip install discord.py groq python-dotenv matplotlib
```

### Environment variables

Create a `.env` file in the root folder:

```
DISCORD_TOKEN=your_discord_bot_token_here
GROQ_API_KEY=your_groq_api_key_here
```

### Discord bot permissions

When creating your bot at [discord.com/developers](https://discord.com/developers/applications), make sure to enable:

- `Message Content Intent` (under Privileged Gateway Intents)
- `Server Members Intent`

The bot needs these OAuth2 scopes: `bot`, `applications.commands`

And these permissions: `Read Messages`, `Read Message History`

### Run it

```bash
python bot.py
```

The slash commands will sync automatically when the bot comes online. It might take a minute for them to show up in Discord.

---

## File structure

```
├── bot.py                  # Main bot file, all the slash commands
├── src/
│   ├── metric_engine.py    # Groq API calls, scoring logic, roast generation
│   ├── archetype_classifier.py  # Maps scores to archetypes
│   └── radar_chart.py      # Generates the radar chart images with matplotlib
├── .env                    # Your tokens (don't commit this)
└── README.md
```

---

## Notes

- The bot needs at least **10 messages** (can be changed in bot.py) from a user in the current channel to analyze them. If there aren't enough it'll say so.
- It only reads messages from the channel where you run the command - it doesn't have access to other channels.
- Message history and scores are not stored anywhere. Every command re-analyzes from scratch.
- The leaderboard makes one Groq API call per active user, so it can be slow in busy channels.
