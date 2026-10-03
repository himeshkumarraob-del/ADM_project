/**
 * UI strings for English and Hindi.
 *
 * Backend replies are localised by the API (`language` field); this file covers
 * the chrome around them.
 */

import type { SupportLevel } from "./api";

export type Locale = "en" | "hi";

export const SUPPORT_LABELS: Record<Locale, Record<SupportLevel, string>> = {
  en: {
    strong_textual_support: "Strong textual support",
    interpretive: "Interpretive",
    modern_application: "Modern application",
    insufficient_evidence: "Insufficient evidence",
  },
  hi: {
    strong_textual_support: "प्रबल पाठ-समर्थन",
    interpretive: "व्याख्यात्मक",
    modern_application: "आधुनिक अनुप्रयोग",
    insufficient_evidence: "अपर्याप्त प्रमाण",
  },
};

export const SUPPORT_DESCRIPTIONS: Record<Locale, Record<SupportLevel, string>> = {
  en: {
    strong_textual_support:
      "A verified passage in the source directly supports this.",
    interpretive:
      "Relevant passages exist; the link to your situation is a reading, not a statement in the text.",
    modern_application:
      "The textual basis is thin — mostly the application layer is carrying the answer.",
    insufficient_evidence:
      "I could not find a sufficiently direct passage in the source material to support this conclusion.",
  },
  hi: {
    strong_textual_support: "स्रोत में सत्यापित अंश सीधे इसका समर्थन करता है।",
    interpretive:
      "संबंधित अंश मौजूद हैं; आपकी स्थिति से संबंध व्याख्या है, पाठ में कथन नहीं।",
    modern_application: "पाठ-आधार कमज़ोर है — उत्तर मुख्यतः अनुप्रयोग पर टिका है।",
    insufficient_evidence:
      "स्रोत-सामग्री में इस निष्कर्ष को समर्थन देने वाला कोई पर्याप्त प्रत्यक्ष अंश नहीं मिला।",
  },
};

/** The seven response sections, in spec order. */
export const SECTIONS: Record<Locale, string[]> = {
  en: [
    "Your Situation",
    "From the Mahabharata",
    "What It Teaches",
    "Applying It",
    "A Different Perspective",
    "Practical Reflection",
    "Sources",
  ],
  hi: [
    "आपकी स्थिति",
    "महाभारत से",
    "यह क्या सिखाता है",
    "इसे अपनाना",
    "एक भिन्न दृष्टिकोण",
    "व्यावहारिक चिंतन",
    "स्रोत",
  ],
};

export const UI: Record<Locale, Record<string, string>> = {
  en: {
    app_name: "Saarathi AI",
    tagline: "Ancient wisdom. Modern guidance.",
    ask: "Ask",
    send: "Send",
    thinking: "Consulting the source…",
    new_chat: "New conversation",
    history: "History",
    explore: "Explore",
    characters: "Characters",
    themes: "Themes",
    sources: "Source Explorer",
    admin: "Admin",
    evaluation: "Evaluation",
    daily_reflection: "Daily Reflection",
    mode: "Mode",
    language: "Language",
    perspectives: "Perspectives",
    no_conversations: "No conversations yet. Ask your first question.",
    load_error: "Something went not quite right",
    empty_input: "Type a question first.",
    safety: "Safety",
    sources_section: "Sources",
    show_debug: "Show retrieval details",
    hide_debug: "Hide retrieval details",
    feedback_helpful: "Helpful",
    feedback_not_helpful: "Not helpful",
    refusals: "Refusals",
    canary: "Canary",
    run_eval: "Run evaluation",
    loading: "Loading…",
    search: "Search",
    verified: "Verified",
    unverified: "Unverified",
    rejected: "Rejected",
    back: "Back",
    question: "Question",
    expected: "Expected",
    got: "Got",
    about: "About this app",
    example_prompts_title: "Example Dilemmas & Questions",
    saarathi_meaning:
      "Saarathi (सारथी) means charioteer and guide, inspired by Krishna serving as Arjuna's charioteer. Ask any real-life situation or question to receive source-grounded reflection from the Mahabharata.",
    grounded_banner:
      "Grounded in verified Mahabharata & Bhagavad Gita source text. Interpretation is clearly separated from text.",
    disclaimer:
      "A study companion — not scripture, pastoral care, medical, legal or financial advice.",
  },
  hi: {
    app_name: "सारथी एआई",
    tagline: "प्राचीन ज्ञान। आधुनिक मार्गदर्शन।",
    ask: "पूछें",
    send: "भेजें",
    thinking: "स्रोत का अध्ययन हो रहा है…",
    new_chat: "नई बातचीत",
    history: "इतिहास",
    explore: "अन्वेषण",
    characters: "पात्र",
    themes: "विषय",
    sources: "स्रोत अन्वेषक",
    admin: "प्रशासन",
    evaluation: "मूल्यांकन",
    daily_reflection: "दैनिक चिंतन",
    mode: "मोड",
    language: "भाषा",
    perspectives: "दृष्टिकोण",
    no_conversations: "अभी कोई बातचीत नहीं। अपना पहला प्रश्न पूछें।",
    load_error: "कुछ ठीक नहीं चला",
    empty_input: "पहले प्रश्न लिखें।",
    safety: "सुरक्षा सूचना",
    sources_section: "स्रोत",
    show_debug: "पुनर्प्राप्ति विवरण देखें",
    hide_debug: "विवरण छिपाएँ",
    feedback_helpful: "उपयोगी",
    feedback_not_helpful: "उपयोगी नहीं",
    refusals: "अस्वीकृतियाँ",
    canary: "कैनरी",
    run_eval: "मूल्यांकन चलाएँ",
    loading: "लोड हो रहा है…",
    search: "खोजें",
    verified: "सत्यापित",
    unverified: "असत्यापित",
    rejected: "अस्वीकृत",
    back: "वापस",
    question: "प्रश्न",
    expected: "अपेक्षित",
    got: "प्राप्त",
    about: "इस ऐप के बारे में",
    example_prompts_title: "उदाहरण दुविधाएँ एवं प्रश्न",
    saarathi_meaning:
      "सारथी (Saarathi) का अर्थ है रथ खींचने वाला और मार्गदर्शक, जो अर्जुन के मार्गदर्शक श्री कृष्ण से प्रेरित है। अपनी व्यावहारिक दुविधा या प्रश्न दर्ज करें।",
    grounded_banner:
      "सत्यापित महाभारत और भगवद्गीता पाठ पर आधारित। व्याख्या को मूल पाठ से स्पष्ट रूप से अलग दिखाया जाता है।",
    disclaimer:
      "यह अध्ययन सहायक है — शास्त्र, चिकित्सा, विधि या वित्तीय सलाह नहीं।",
  },
};

export function t(locale: Locale, key: string): string {
  return UI[locale][key] ?? UI.en[key] ?? key;
}
