"""
Archetype classification maps behavioral metrics to user personas.
Each archetype includes visual (emoji, color) and textual (description, traits) metadata
for display in Discord embeds and ranking visualizations.
"""

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
    """
    Route metrics to archetype using prioritized decision tree.
    Order matters: higher-priority classifications (toxic, chaos) check first,
    avoiding mis-classification of users with mixed signals.

    Thresholds and requirements:
    - Toxicity only triggers for users with 20+ messages (avoid false positives on small samples)
    - Philosopher requires high eloquence AND long messages AND 20+ message sample
    - Lurker requires short messages AND low social engagement
    - Consistency requires very high stability (>80) AND 20+ messages
    - Social Butterfly only triggers if no other dominant archetype found

    Fallback to average_enjoyer if no threshold crossed (catch-all for balanced users).
    """
    # Priority 1: Toxicity (requires evidence across multiple messages)
    if metrics["toxicity_score"] > 55 and metrics["message_count"] >= 20:
        return ARCHETYPES["toxic_oracle"]

    # Priority 2: Chaos (unpredictability dominates other traits)
    if metrics["chaos_score"] > 35:
        return ARCHETYPES["chaos_goblin"]

    # Priority 3: Eloquence (requires reinforcement from message length and sample size)
    if (
        metrics["eloquence_score"] > 55
        and metrics["raw_avg_message_length"] >= 8
        and metrics["message_count"] >= 20
    ):
        return ARCHETYPES["philosopher"]

    # Priority 4: Expressiveness (emoji frequency is unambiguous signal)
    if metrics["raw_emoji_per_message"] > 3:
        return ARCHETYPES["emoji_archaeologist"]

    # Priority 5: Brevity + introversion (short AND quiet = lurker)
    if metrics["raw_avg_message_length"] < 5 and metrics["social_score"] < 50:
        return ARCHETYPES["lurker_lord"]

    # Priority 6: Social engagement (requires clear preference for interaction)
    if metrics["social_score"] > 55:
        return ARCHETYPES["social_butterfly"]

    # Priority 7: Consistency (strict threshold, requires sample size)
    if metrics["consistency_score"] > 80 and metrics["message_count"] >= 20:
        return ARCHETYPES["consistent_narrator"]

    # Fallback: no dominant trait
    return ARCHETYPES["average_enjoyer"]
