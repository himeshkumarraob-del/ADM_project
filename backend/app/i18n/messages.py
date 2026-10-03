"""18. Language support.

Section headings, canned sentences and refusal wording for the response
template. English and Hindi ship by default; the architecture adds a language
by adding one dict here (and, for source material, a translation field on the
passage -- translations never replace ``original_text``).
"""

from __future__ import annotations

from typing import Any

DEFAULT_LANGUAGE = "en"

MESSAGES: dict[str, dict[str, Any]] = {
    "en": {
        "your_situation": "Your Situation",
        "from_mahabharata": "From the Mahabharata",
        "what_it_teaches": "What It Teaches",
        "applying": "Applying It to Your Situation",
        "different_perspective": "A Different Perspective",
        "practical_reflection": "Practical Reflection",
        "sources": "Sources",
        "textual_evidence": "Textual evidence",
        "interpretation": "Interpretation",
        "modern_application": "Modern application",
        "reading": (
            "This episode can be read as one in which {value}."
        ),
        "application_only": (
            "In a modern situation like yours, this could suggest {suggestion}."
        ),
        "application_reader": (
            "For a reader today, this could suggest {suggestion}."
        ),
        "analogy_caveat_episode": (
            "The source is drawn from a royal and dynastic world that differs "
            "substantially from a modern one, so the analogy is limited: what "
            "may carry over is the question it raises, not the circumstances."
        ),
        "analogy_caveat_teaching": (
            "This passage is counsel given inside the epic's narrative rather "
            "than advice about your circumstances, so the comparison stops at "
            "the principle."
        ),
        "insufficient": (
            "I could not find a sufficiently direct passage in the source material "
            "to support this conclusion."
        ),
        "no_evidence_body": (
            "The indexed source material did not return passages that speak directly "
            "to this question. Rather than offer something that only sounds "
            "authoritative, here is what I can honestly say: there is not enough "
            "textual evidence in the index right now to make that claim. "
            "Try naming a person, an episode, or a value in conflict, or use the "
            "Source Explorer to check what the corpus actually contains."
        ),
        "evidence_caveat": (
            "This episode can be read as emphasising {value}. Applied to your "
            "situation, it may suggest considering {suggestion}."
        ),
        "not_a_command": (
            "The Mahabharata does not state a single rule for this; it stages the "
            "tension and shows what each choice cost."
        ),
        "disclaimer": (
            "This is a source-grounded exploration of the Mahabharata, not "
            "professional advice."
        ),
        "reflection_default": [
            "What is your responsibility in this situation?",
            "Are you acting from anger or from principle?",
            "What consequence could your decision create?",
            "Are you protecting someone, or protecting your attachment to them?",
        ],
    },
    "hi": {
        "your_situation": "आपकी स्थिति",
        "from_mahabharata": "महाभारत से",
        "what_it_teaches": "इससे क्या सीख मिलती है",
        "applying": "आपकी स्थिति पर इसका लागू होना",
        "different_perspective": "एक भिन्न दृष्टिकोण",
        "practical_reflection": "विचार हेतु प्रश्न",
        "sources": "स्रोत",
        "textual_evidence": "पाठ-आधारित प्रमाण",
        "interpretation": "व्याख्या",
        "modern_application": "आधुनिक प्रयोग",
        "insufficient": "स्रोत सामग्री में इस निष्कर्ष का समर्थन करने वाला कोई पर्याप्त प्रत्यक्ष अंश मुझे नहीं मिला।",
        "no_evidence_body": (
            "अनुक्रमित स्रोत सामग्री में इस प्रश्न से सीधे संबंधित अंश नहीं मिले। "
            "केवल आधिकारिक लगने वाली कोई बात कहने के बजाय, मैं यही ईमानदारी से कह सकता हूँ: "
            "अभी इस दावे के लिए पर्याप्त पाठ-प्रमाण उपलब्ध नहीं है।"
        ),
        "evidence_caveat": (
            "इस प्रसंग को {value} पर बल देने के रूप में पढ़ा जा सकता है। आपकी स्थिति में इसका "
            "अर्थ {suggestion} विचार करना हो सकता है।"
        ),
        "reading": (
            "इस प्रसंग को ऐसे रूप में पढ़ा जा सकता है जिसमें {value}।"
        ),
        "application_only": (
            "आपकी जैसी आधुनिक स्थिति में इसका अर्थ {suggestion} हो सकता है।"
        ),
        "application_reader": (
            "आज के पाठक के लिए इसका अर्थ {suggestion} हो सकता है।"
        ),
        "analogy_caveat_episode": (
            "स्रोत एक राजवंशीय जगत से है जो आधुनिक स्थिति से भिन्न है, इसलिए "
            "तुलना सीमित है: यहाँ वही बात हस्तांतरित हो सकती है जो प्रश्न उठाती है, "
            "परिस्थितियाँ नहीं।"
        ),
        "analogy_caveat_teaching": (
            "यह अंश महाकाव्य की कथा के भीतर दी गई सलाह है, आपकी परिस्थिति के "
            "बारे में निर्देश नहीं; इसलिए तुलना सिद्धांत तक ही सीमित है।"
        ),
        "not_a_command": (
            "महाभारत इसके लिए कोई एक नियम नहीं बताता; यह तनाव को सामने रखता है और "
            "प्रत्येक विकल्प की कीमत दिखाता है।"
        ),
        "disclaimer": (
            "यह महाभारत का स्रोत-आधारित अन्वेषण है, कोई पेशेवर सलाह नहीं।"
        ),
        "reflection_default": [
            "इस स्थिति में आपकी ज़िम्मेदारी क्या है?",
            "आप क्रोध से काम ले रहे हैं या सिद्धांत से?",
            "आपका निर्णय कैसा परिणाम ला सकता है?",
            "आप किसी की रक्षा कर रहे हैं, या उससे अपनी आसक्ति की?",
        ],
    },
}


def get_messages(language: str) -> dict[str, Any]:
    return MESSAGES.get(language) or MESSAGES[DEFAULT_LANGUAGE]
