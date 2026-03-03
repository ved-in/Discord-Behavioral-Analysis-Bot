ARCHETYPES = {
    "chaos_goblin": {
        "name": "The Chaos Goblin",
        "emoji": "🌪️",
        "description": "You communicate like a caffeinated squirrel in a tornado. Your messages vary wildly in length, punctuation is your playground, and all-caps is your love language.",
        "color": 0xFF4500,
        "traits": ["High chaos", "Unpredictable rhythm", "Intense expression"],
    },
    "toxic_oracle": {
        "name": "The Toxic Oracle",
        "emoji": "☠️",
        "description": "You deliver your opinions like a medieval plague—fast, widespread, and hard to recover from. Your vocabulary punches downward.",
        "color": 0x8B0000,
        "traits": ["High toxicity", "Direct aggression", "Charged language"],
    },
    "philosopher": {
        "name": "The Discord Philosopher",
        "emoji": "🧠",
        "description": "You construct paragraphs when everyone else sends memes. Your lexical diversity is borderline suspicious. Do you have a thesaurus hotkey?",
        "color": 0x4169E1,
        "traits": ["High eloquence", "Rich vocabulary", "Long-form communication"],
    },
    "emoji_archaeologist": {
        "name": "The Emoji Archaeologist",
        "emoji": "🦖",
        "description": "You've rediscovered every emoji in the Unicode standard. Your emotional expression arrives before your words do. You communicate in hieroglyphics.",
        "color": 0xFFD700,
        "traits": ["High emoji use", "Visual communicator", "Expressive"],
    },
    "lurker_lord": {
        "name": "The Lurker Lord",
        "emoji": "👁️",
        "description": "Brief. Sparse. Watching. Your messages are surgical strikes of minimal effort. Every word is rationed like it costs you something.",
        "color": 0x708090,
        "traits": ["Short messages", "Low frequency", "Minimal expression"],
    },
    "social_butterfly": {
        "name": "The Social Butterfly",
        "emoji": "🦋",
        "description": "You tag everyone, respond to everything, and ask questions for sport. You are the Discord equivalent of a golden retriever.",
        "color": 0xFF69B4,
        "traits": ["High mentions", "Question heavy", "Conversational"],
    },
    "consistent_narrator": {
        "name": "The Consistent Narrator",
        "emoji": "📖",
        "description": "Your message lengths are eerily uniform. Your tone is stable. You are the metronome of this server—dependable, measured, slightly eerie.",
        "color": 0x32CD32,
        "traits": ["High consistency", "Stable tone", "Measured rhythm"],
    },
    "average_enjoyer": {
        "name": "The Average Enjoyer",
        "emoji": "😐",
        "description": "You are statistically normal in every behavioral dimension. Not chaotic, not eloquent, not particularly expressive. A linguistic beige.",
        "color": 0xD3D3D3,
        "traits": ["Balanced metrics", "No dominant traits", "Reliably average"],
    },
}


def classify(metrics):
    if metrics["toxicity_score"] > 55 and metrics["message_count"] >= 20:
        return ARCHETYPES["toxic_oracle"]
    if metrics["chaos_score"] > 35:
        return ARCHETYPES["chaos_goblin"]
    if metrics["eloquence_score"] > 55 and metrics["raw_avg_message_length"] >= 8 and metrics["message_count"] >= 20:
        return ARCHETYPES["philosopher"]
    if metrics["raw_emoji_per_message"] > 3:
        return ARCHETYPES["emoji_archaeologist"]
    if metrics["raw_avg_message_length"] < 5 and metrics["social_score"] < 50:
        return ARCHETYPES["lurker_lord"]
    if metrics["social_score"] > 55:
        return ARCHETYPES["social_butterfly"]
    if metrics["consistency_score"] > 80 and metrics["message_count"] >= 20:
        return ARCHETYPES["consistent_narrator"]
    return ARCHETYPES["average_enjoyer"]
