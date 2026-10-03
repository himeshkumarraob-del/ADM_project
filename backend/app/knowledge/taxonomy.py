"""Canonical domain taxonomy.

Single source of truth for modes, themes, values-in-conflict, emotions,
characters and safety lexicons. The rule-based analyst, the retrieval layer,
the API and the frontend all read from here, so a new theme only has to be
added once.
"""

from __future__ import annotations

from typing import TypedDict


class ModeInfo(TypedDict):
    id: str
    label: str
    emoji: str
    tagline: str
    placeholder: str


# --------------------------------------------------------------------------- #
# 12. "Ask the Mahabharata" modes
# --------------------------------------------------------------------------- #
MODES: dict[str, ModeInfo] = {
    "situation_advice": {
        "id": "situation_advice",
        "label": "Situation Advice",
        "emoji": "\U0001f9ed",  # compass
        "tagline": "Describe a real dilemma and explore it through the text.",
        "placeholder": "Describe the situation you are facing...",
    },
    "episode": {
        "id": "episode",
        "label": "Ask About an Episode",
        "emoji": "\U0001f4dc",  # scroll
        "tagline": "Ask what actually happens in the Mahabharata.",
        "placeholder": "Which episode or event do you want to explore?",
    },
    "character_wisdom": {
        "id": "character_wisdom",
        "label": "Character Wisdom",
        "emoji": "\U0001f464",  # bust
        "tagline": "Explore how a character acted and why.",
        "placeholder": "Ask about a character's decisions or conduct...",
    },
    "moral_dilemma": {
        "id": "moral_dilemma",
        "label": "Moral Dilemma",
        "emoji": "\u2696\ufe0f",  # scales
        "tagline": "Two conflicting duties, both defensible.",
        "placeholder": "State both options you are torn between...",
    },
    "source_explorer": {
        "id": "source_explorer",
        "label": "Source Explorer",
        "emoji": "\U0001f50d",  # magnifier
        "tagline": "Search the indexed source material directly.",
        "placeholder": "Search the indexed passages...",
    },
    "daily_reflection": {
        "id": "daily_reflection",
        "label": "Daily Reflection",
        "emoji": "\U0001fab7",  # lotus
        "tagline": "A verified passage to sit with today.",
        "placeholder": "Optional: what is on your mind today?",
    },
    "perspectives": {
        "id": "perspectives",
        "label": "See Different Perspectives",
        "emoji": "\u2696\ufe0f",
        "tagline": "How would different characters read this dilemma?",
        "placeholder": "Describe the dilemma you want viewed from several angles...",
    },
}

DEFAULT_MODE = "situation_advice"


# --------------------------------------------------------------------------- #
# Themes (knowledge-base tags) — slug, display name, description, kind
# --------------------------------------------------------------------------- #
class ThemeDef(TypedDict):
    slug: str
    name: str
    kind: str
    description: str


THEMES: list[ThemeDef] = [
    {"slug": "dharma", "name": "Dharma", "kind": "value",
     "description": "Right conduct, duty, and the ordering of obligations."},
    {"slug": "duty-vs-interest", "name": "Duty vs personal interest", "kind": "conflict",
     "description": "What one is obliged to do against what one wants."},
    {"slug": "truth-vs-loyalty", "name": "Truth vs loyalty", "kind": "conflict",
     "description": "Honesty toward the facts against fidelity to a person or group."},
    {"slug": "family-vs-justice", "name": "Family vs justice", "kind": "conflict",
     "description": "Kinship obligations against fair dealing for others."},
    {"slug": "ambition-vs-ethics", "name": "Ambition vs ethics", "kind": "conflict",
     "description": "Advancement against moral limits."},
    {"slug": "forgiveness-vs-self-respect", "name": "Forgiveness vs self-respect", "kind": "conflict",
     "description": "Absorbing a wrong against defending one's dignity."},
    {"slug": "revenge-vs-restraint", "name": "Revenge vs restraint", "kind": "conflict",
     "description": "Retaliation against forbearance."},
    {"slug": "fear-vs-responsibility", "name": "Fear vs responsibility", "kind": "conflict",
     "description": "Self-preservation against a duty that must be faced."},
    {"slug": "attachment-vs-duty", "name": "Attachment vs duty", "kind": "conflict",
     "description": "Clinging to persons or outcomes against acting as one must."},
    {"slug": "friendship-vs-morality", "name": "Friendship vs morality", "kind": "conflict",
     "description": "Standing by a friend against refusing a wrong."},
    {"slug": "individual-vs-society", "name": "Individual desire vs social responsibility", "kind": "conflict",
     "description": "Personal wish against the good of the wider group."},
    {"slug": "revenge", "name": "Revenge", "kind": "value",
     "description": "Retaliation and its consequences."},
    {"slug": "anger", "name": "Anger", "kind": "emotion",
     "description": " Wrath and its governance."},
    {"slug": "forgiveness", "name": "Forgiveness", "kind": "value",
     "description": "Withholding retaliation, or granting it."},
    {"slug": "justice", "name": "Justice", "kind": "value",
     "description": "Fair consequence, adjudication, and redress."},
    {"slug": "self-control", "name": "Self-control", "kind": "value",
     "description": "Restraint of impulse, speech, and appetite."},
    {"slug": "consequences", "name": "Consequences", "kind": "value",
     "description": "The downstream effects of actions across time."},
    {"slug": "loyalty", "name": "Loyalty", "kind": "value",
     "description": "Fidelity to persons, promises, and parties."},
    {"slug": "gratitude", "name": "Gratitude", "kind": "value",
     "description": "Repayment of obligation received."},
    {"slug": "identity", "name": "Identity", "kind": "value",
     "description": "Who one is, and what that is taken to require."},
    {"slug": "recognition", "name": "Recognition", "kind": "value",
     "description": "Credit, visibility, and honour for one's work."},
    {"slug": "perseverance", "name": "Perseverance", "kind": "value",
     "description": "Continuing in the face of discouragement."},
    {"slug": "detachment", "name": "Detachment from results", "kind": "value",
     "description": "Committing to action without clinging to its fruit."},
    {"slug": "counsel", "name": "Counsel and counsel-giving", "kind": "value",
     "description": "How advice is offered, received, and refused."},
    {"slug": "silence", "name": "Silence and non-interference", "kind": "value",
     "description": "When speaking or acting is withheld."},
    {"slug": "responsibility", "name": "Responsibility", "kind": "value",
     "description": "Obligation arising from role, position, or capacity."},
    {"slug": "grief", "name": "Grief and loss", "kind": "emotion",
     "description": "Mourning, consolation, and mortality."},
    {"slug": "fear", "name": "Fear", "kind": "emotion",
     "description": "Dread and its effect on judgement."},
    {"slug": "ambition", "name": "Ambition", "kind": "value",
     "description": "Aspiration toward status, power, or achievement."},
    {"slug": "nonviolence", "name": "Non-violence", "kind": "value",
     "description": "Ahimsa and the limits placed on harm."},
    {"slug": "truth", "name": "Truth", "kind": "value",
     "description": "Veracity, oaths, and the cost of deception."},
    {"slug": "power", "name": "Power and governance", "kind": "value",
     "description": "Rule, authority, and their responsibilities."},
    {"slug": "duty", "name": "Duty", "kind": "value",
     "description": "Swadharma — the work one's position demands."},
    {"slug": "war", "name": "War and conflict", "kind": "value",
     "description": "Righteous war, its justification and its cost."},
    {"slug": "doubt", "name": "Doubt and hesitation", "kind": "emotion",
     "description": "Uncertainty before action."},
    # --- slugs used by corpus passages (validated against this list) ------ #
    {"slug": "shame", "name": "Shame and honour", "kind": "emotion",
     "description": "Public disgrace, dignity, and the face one keeps."},
    {"slug": "resistance", "name": "Resistance and protest", "kind": "value",
     "description": "Questioning, protesting, and refusing the unacceptable."},
    {"slug": "refusal-of-counsel", "name": "Refusal of counsel", "kind": "value",
     "description": "Advice offered and refused — and what follows."},
    {"slug": "gambling", "name": "Gambling and the stake", "kind": "value",
     "description": "The dice, the wager, and the loss of self-command."},
    {"slug": "dignity", "name": "Dignity", "kind": "value",
     "description": "The worth of a person that others may not strip away."},
    {"slug": "patience", "name": "Patience and forbearance", "kind": "value",
     "description": "Enduring without surrendering what is right."},
    {"slug": "vows", "name": "Vows and pledges", "kind": "value",
     "description": "Binding words and the burden they create."},
    {"slug": "hypocrisy", "name": "Hypocrisy", "kind": "value",
     "description": "The gap between professed virtue and actual conduct."},
    {"slug": "generosity", "name": "Generosity", "kind": "value",
     "description": "Giving, and giving away, against self-interest."},
    {"slug": "guilt", "name": "Guilt", "kind": "emotion",
     "description": "The weight of wrong one has done."},
    {"slug": "deception", "name": "Deception", "kind": "value",
     "description": "Stratagem, concealment, and their moral cost."},
]


# --------------------------------------------------------------------------- #
# Values-in-conflict pairs used by the situation analyst
# --------------------------------------------------------------------------- #
CONFLICT_PATTERNS: list[tuple[str, str, list[str]]] = [
    # (value_a, value_b, trigger words)
    ("duty", "personal interest", ["should i", "want to", "my career", "my benefit",
                                   "self interest", "give up", "quit"]),
    ("truth", "loyalty", ["lie", "cover up", "honest", "betray", "secret", "keep quiet",
                          "truth"]),
    ("family", "justice", ["family", "relative", "brother", "sister", "parents",
                           "inheritance", "fair"]),
    ("ambition", "ethics", ["promotion", "credit", "shortcut", "cheat", "advance",
                            "ambition", "cut corners"]),
    ("forgiveness", "self-respect", ["forgive", "apolog", "again and again", "dignity",
                                     "respect myself", "take advantage"]),
    ("revenge", "restraint", ["revenge", "retaliate", "payback", "get back", "hurt them",
                              "restrain", "forgive"]),
    ("fear", "responsibility", ["scared", "afraid", "afraid to", "risk", "speak up",
                                "responsibility", "dare"]),
    ("attachment", "duty", ["let go", "attached", "cannot leave", "loyal to", "move on",
                            "duty calls"]),
    ("friendship", "morality", ["friend is", "my friend", "friendship", "wrong",
                                "taking advantage", "stand by"]),
    ("individual desire", "social responsibility", ["myself only", "team", "others",
                                                    "society", "community", "fair to everyone"]),
]


# --------------------------------------------------------------------------- #
# Emotion lexicon (rule-based analyst)
# --------------------------------------------------------------------------- #
EMOTION_LEXICON: dict[str, list[str]] = {
    "anger": ["angry", "furious", "rage", "mad", "resent", "hatred", "irritated", "infuriated"],
    "hurt": ["hurt", "betray", "wounded", "heartbroken", "let down", "disappointed", "stung"],
    "fear": ["afraid", "scared", "fear", "anxious", "worried", "nervous", "dread", "panic"],
    "guilt": ["guilty", "guilt", "regret", "blame myself", "sorry", "remorse"],
    "shame": ["shame", "embarrass", "humiliat", "disgrace"],
    "sadness": ["sad", "depress", "unhappy", "miserable", "grief", "mourning", "lost"],
    "confusion": ["confused", "unsure", "uncertain", "don't know", "do not know", "torn",
                  "at a loss"],
    "frustration": ["frustrat", "stuck", "giving up", "give up", "hopeless", "exhausted",
                    "tired of"],
    "loneliness": ["alone", "lonely", "isolated", "no one", "nobody"],
    "injustice": ["unfair", "unjust", "cheated", "robbed", "exploit", "taken advantage",
                  "discriminat"],
}


# --------------------------------------------------------------------------- #
# 10. Characters
# --------------------------------------------------------------------------- #
class CharacterDef(TypedDict):
    slug: str
    name: str
    aliases: list[str]
    role: str
    description: str
    primary_themes: list[str]


CHARACTERS: list[CharacterDef] = [
    {"slug": "krishna", "name": "Krishna", "aliases": ["Shri Krishna", "Kesava", "Vasudeva"],
     "role": "Charioteer, counsellor, king of Dwarka",
     "description": "Argues for right action without clinging to outcomes, and repeatedly "
                    "presses that a duty must be done even when it is painful.",
     "primary_themes": ["dharma", "duty", "detachment", "counsel", "consequences"]},
    {"slug": "yudhishthira", "name": "Yudhishthira", "aliases": ["Dharma-raja", "Ajatashatru"],
     "role": "Eldest Pandava, king",
     "description": "Holds to truth and non-violence even at severe cost, and is repeatedly "
                    "shown paying for his own compromises.",
     "primary_themes": ["dharma", "truth", "justice", "gambling", "responsibility"]},
    {"slug": "arjuna", "name": "Arjuna", "aliases": ["Partha", "Gudakesa", "Dhananjaya"],
     "role": "Pandava archer",
     "description": "Voices hesitation, doubt, and the crisis of acting when duty and "
                    "attachment collide.",
     "primary_themes": ["duty", "doubt", "attachment-vs-duty", "war"]},
    {"slug": "bhima", "name": "Bhima", "aliases": ["Vrikodara", "Bhimasena"],
     "role": "Pandava warrior",
     "description": "Impatient, physical, direct; insists on consequences being enforced "
                    "rather than deferred.",
     "primary_themes": ["revenge", "anger", "justice", "responsibility"]},
    {"slug": "draupadi", "name": "Draupadi", "aliases": ["Panchali", "Krishnaa", "Yajnaseni"],
     "role": "Queen of the Pandavas",
     "description": "Demands redress publicly, questions whether a decision was valid, and "
                    "turns humiliation into a claim for justice.",
     "primary_themes": ["justice", "dignity", "truth", "consequences", "resistance"]},
    {"slug": "vidura", "name": "Vidura", "aliases": ["Kshatta"],
     "role": "Chief counsellor of Hastinapura",
     "description": "Offers plain, unsparing counsel to a king who does not want to hear it; "
                    "stresses restraint, governance, and moral realism.",
     "primary_themes": ["counsel", "self-control", "power", "dharma", "silence"]},
    {"slug": "bhishma", "name": "Bhishma", "aliases": ["Gangaputra", "Bhagavan Bhishma",
                                                       "Devavrata"],
     "role": "Grand-uncle and protector of the throne",
     "description": "Bound by vows he chose; shows duty and personal loyalty producing "
                    "outcomes he himself judges to be wrong.",
     "primary_themes": ["duty", "loyalty", "vows", "consequences", "silence"]},
    {"slug": "karna", "name": "Karna", "aliases": ["Suryaputra", "Ratha", "Danveer Karna"],
     "role": "King of Anga, ally of Duryodhana",
     "description": "Loyal to a benefactor in the face of humiliation; caught between "
                    "gratitude, identity, and a duty he recognises.",
     "primary_themes": ["loyalty", "gratitude", "identity", "friendship-vs-morality"]},
    {"slug": "duryodhana", "name": "Duryodhana", "aliases": ["Suyodhana"],
     "role": "Eldest Kaurava",
     "description": "Refuses settlement even when it is offered, and interprets every "
                    "concession as weakness.",
     "primary_themes": ["ambition", "power", "refusal-of-counsel", "consequences"]},
    {"slug": "gandhari", "name": "Gandhari", "aliases": [],
     "role": "Queen of Dhritarashtra",
     "description": "Chooses loyalty to her sons over remonstrance, and later confronts the "
                    "cost of that choice.",
     "primary_themes": ["family-vs-justice", "loyalty", "silence", "consequences"]},
    {"slug": "kunti", "name": "Kunti", "aliases": ["Pritha"],
     "role": "Mother of the Pandavas",
     "description": "Carries a long-held secret whose consequences she cannot control.",
     "primary_themes": ["identity", "secrecy", "family-vs-justice", "consequences"]},
    {"slug": "nakula", "name": "Nakula", "aliases": [],
     "role": "Pandava prince",
     "description": "Associated with learning, beauty, and steady conduct in the exile.",
     "primary_themes": ["duty", "perseverance"]},
    {"slug": "sahadeva", "name": "Sahadeva", "aliases": [],
     "role": "Pandava prince",
     "description": "Known for counsel and for speaking before acting in matters of duty.",
     "primary_themes": ["counsel", "duty", "truth"]},
    {"slug": "sanjaya", "name": "Sanjaya", "aliases": [],
     "role": "Charioteer and messenger of Dhritarashtra",
     "description": "Reports the war to a blind king who authorised it; a study in "
                    "delivering unwelcome truth.",
     "primary_themes": ["counsel", "truth", "responsibility", "consequences"]},
    {"slug": "dhritarashtra", "name": "Dhritarashtra", "aliases": [],
     "role": "King of Hastinapura",
     "description": "Knows what is right and repeatedly chooses otherwise, while asking to "
                    "be reassured.",
     "primary_themes": ["attachment", "power", "refusal-of-counsel", "consequences"]},
    {"slug": "shakuni", "name": "Shakuni", "aliases": [],
     "role": "Prince of Gandhara",
     "description": "Engineers the trap at the dice game; represents deliberate cultivation "
                    "of grievance.",
     "primary_themes": ["revenge", "deception", "ambition"]},
    {"slug": "drona", "name": "Drona", "aliases": ["Dronacharya"],
     "role": "Teacher of both princes",
     "description": "Bound to the throne that raised him; shows a teacher's loyalty turning "
                    "into complicity.",
     "primary_themes": ["duty", "loyalty", "attachment", "consequences"]},
    {"slug": "ashwatthama", "name": "Ashwatthama", "aliases": [],
     "role": "Son of Drona",
     "description": "Turns grief into atrocity, then to a punishment he must carry.",
     "primary_themes": ["revenge", "anger", "consequences", "grief"]},
]


# --------------------------------------------------------------------------- #
# 17. Safety lexicons
# --------------------------------------------------------------------------- #
CRISIS_TERMS: list[str] = [
    "kill myself", "suicide", "end my life", "want to die", "hurt myself",
    "self harm", "self-harm", "cut myself", "no reason to live",
    "better off dead", "can't go on living", "cannot go on living",
]

PROFESSIONAL_DISCLAIMER_TOPICS: dict[str, str] = {
    "medical": ["i'm sick", "i am sick", "diagnos", "medication", "doctor", "symptoms",
                "cancer", "surgery", "pain in", "disease", "therapy for physical",
                "mental health", "depress", "anxi", "bipolar", "panic attack"],
    "legal": ["sue ", "lawsuit", "court", "arrest", "police", "divorce", "custody",
              "contract dispute", "charged with", "illegal", "lawyer"],
    "financial": ["investment", "stocks", "crypto", "loan", "mortgage", "bankrupt",
                  "tax return", "trading", "portfolio", "debt"],
    "crisis": CRISIS_TERMS,
}

# Question shapes the rule-based analyst recognises per mode.
MODE_INTENT_HINTS: dict[str, list[str]] = {
    "situation_advice": ["should i", "what should", "what do i", "what would", "help me",
                         "i am", "i'm", "my ", "we "],
    "episode": ["what happened", "why did", "how did", "tell me about", "describe",
                "episode", "war of", "battle of"],
    "character_wisdom": ["krishna", "yudhishthira", "arjuna", "bhima", "draupadi", "vidura",
                         "bhishma", "karna", "duryodhana", "gandhari", "kunti", "sanjaya",
                         "drona", "ashwatthama", "shakuni", "nakula", "sahadeva",
                         "dhritarashtra"],
    "moral_dilemma": ["or ", "either", "but also", "on the other hand", "versus", " vs ",
                      "conflict between"],
    "source_explorer": ["search", "find passage", "quote", "verse", "chapter", "parva"],
    "daily_reflection": [],
    "perspectives": ["perspective", "view", "how would", "see it"],
}


def theme_slugs() -> list[str]:
    return [t["slug"] for t in THEMES]


def character_slugs() -> list[str]:
    return [c["slug"] for c in CHARACTERS]
