# Discord Behavioral Analysis Bot

A Discord bot that analyzes how people communicate in a server. It examines a user’s recent messages and builds a behavioral profile across multiple dimensions — chaos, toxicity, eloquence, social behavior, and more. It then assigns an archetype, generates a radar chart, and can optionally produce a roast based on actual conversation context.

By default, it uses a locally hosted LLM through Ollama (Mistral by default). Messages are processed locally and are not stored or used for model training.

For testing purposes, a Groq-powered version is available. If using Groq, ensure that all users in the server have consented, since message data is sent to a third-party API.

Groq would ideally not be used but due to device limitations, for testing we had to use groq.

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

-A Discord bot token
-Ollama installed and running locally
or
-A Groq API key (if using the Groq backend)

### Install dependencies

```bash
pip install discord.py python-dotenv matplotlib
```
If using ollama:
```bash
pip install ollama
```
If using groq:
```bash
pip install groq
```

### Install Ollama
Download and install Ollama from [ollama.com](https://ollama.com)

Then pull a model (mistral used by default in code):
```bash
ollama pull mistral
```

Make sure Ollama is running before starting the bot:
```bash
ollama serve
```

> You can use any model you want — just update `model` variable in in `config.json` to match.


### Environment variables

Create a `.env` file in the root folder:

```
DISCORD_TOKEN=your_discord_bot_token_here
GROQ_API_KEY=your_groq_api_key
```

`GROQ_API_KEY` is only required if using the Groq backend.

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
├── bot.py                    # Entry point, loads slash commands
├── config.json               # Runtime config (min_messages, provider, model choice, etc.)
├── get_vars.py               # Environment/config loader
├── .env                      # Secrets (DO NOT COMMIT)
├── README.md
├── LICENSE
│
└── src/
    │
    ├── commands/             # Slash command implementations
    │   ├── analyze.py        # /analyze
    │   ├── compare.py        # /compare
    │   ├── leaderboard.py    # /leaderboard
    │   ├── roast.py          # /roast
    │   └── shared_funs.py    # Shared logic for commands
    │
    ├── helpers/              # Core logic layer
    │   ├── archetype_classifier.py  # Maps metrics → archetype
    │   ├── bot_instance.py          # Bot creation/setup abstraction
    │   ├── metric_engine.py         # Local LLM scoring logic
    │   ├── metric_engine_groq.py    # Groq API scoring logic
    │   └── radar_chart.py           # Radar chart generation
```

---

## Notes

- The bot needs at least **10 messages** (can be changed in `config.json`) from a user in the current channel to analyze them. If there aren't enough it'll say so.
- It only reads messages from the channel where you run the command 
- Message history and scores are not stored anywhere. Every command re-analyzes from scratch.
- The leaderboard makes one call per active user, so it can be slow in busy channels.
