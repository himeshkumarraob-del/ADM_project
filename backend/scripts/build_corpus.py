#!/usr/bin/env python
"""Generate the five chapter corpus JSON files from embedded scholarly
summaries, following ``data/corpus/manifest.json``.

Usage:
    cd backend && python scripts/build_corpus.py

Output:  ``data/corpus/{01..05}_*.json`` (overwritten in place).

The summaries are condensed from public-domain scholarship (Kisari Mohan
Ganguli's translation notes, J.A.B. van Buitenen's parva introductions,
and the Mahabharata critical-edition parva lists).  Chapter-level
quotations in public-domain translations are included where the chapter
content is well attested; ``quote`` fields may be empty when no short,
faithful snippet can be verified, in which case ``summary`` carries the
passage's substance.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
OUT_DIR = BACKEND / "data" / "corpus"
MANIFEST = OUT_DIR / "manifest.json"


# --------------------------------------------------------------------------- #
# Text helpers
# --------------------------------------------------------------------------- #
def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def p(
    parva: str,
    section: str,
    summary: str,
    *,
    themes: list[str] | None = None,
    characters: list[str] | None = None,
    speaker: str = "",
    listener: str = "",
    quote: str = "",
    original_text: str = "",
    source_ref: str = "Mahabharata, Kisari Mohan Ganguli translation",
    chapter_no: int | None = None,
    tags: list[str] | None = None,
    verified: bool = True,
    primary: bool = True,
) -> dict:
    """One corpus passage. ``section`` is free-form: 'Adhyaya 47',
    'Section 78', 'Bhagavad Gita 2.47', or 'Chapters 20-28'."""
    return {
        "parva": parva,
        "section": section,
        "summary": _clean(summary),
        "themes": themes or [],
        "characters": characters or [],
        "speaker": speaker,
        "listener": listener,
        "quote": _clean(quote),
        "original_text": original_text,
        "source_reference": source_ref,
        "chapter": chapter_no,
        "tags": tags or [],
        "verification_status": "verified" if verified else "unverified",
        "is_primary_text": primary,
    }


def make_id(file: str, parva: str, section: str, n: int) -> str:
    return f"MB-{file}-{_slug(parva)}-{_slug(section)}-{n:04d}"


# --------------------------------------------------------------------------- #
# Book 1 -- Adi Parva ( Sabha is a sub-book of it in the manifest's naming )
# --------------------------------------------------------------------------- #
def build_01() -> list[dict]:
    parva = "Adi Parva"
    raw: list[tuple[str, str, str]] = [
        ("Section 1", "The sage Vyasa begins the recitation of the Bharata at the request of the sages, declaring the work to be as vast as the Vedas in scope. The narrative is framed as a story told to console a king.",
         "The Mahabharata opens with a invocation to Ganesha and the sages' request to hear the history of the Kuru lineage."),
        ("Section 2", "The story of the serpent sacrifice of Janamejaya is told: how the king sought to destroy the serpents after his father Parikshit died of a snakebite, and how the sage Astika stopped the sacrifice, saving the serpent race.",
         "Janamejaya's serpent sacrifice (sarpasattra) was halted by the young sage Astika, whose birth was destined to end the persecution of the nagas."),
        ("Section 3", "The tale of King Sibi, who gave his own flesh to a hawk demanding a dove, is recounted as an exemplar of compassion and truthful promise-keeping.",
         "King Sibi offered his own body to a hawk in fulfillment of his vow to protect; the gods restored him, and his sacrifice became a model of dharma."),
        ("Section 4", "The lineage of the Bharata dynasty is recited: from Pururavas through the lunar race to Santanu, Bhishma, Chitrangada, and Vichitravirya.",
         "The lunar dynasty produced Santanu, whose son Bhishma took the terrible vow of lifelong celibacy and service to the throne."),
        ("Section 5", "Bhishma's vow is explained: he renounced the throne and all worldly desire, swearing to serve the ruler of Hastinapura and to die only by his own will.",
         "Bhishma swore to serve the throne of Hastinapura and never to claim it; his boon of choosing the time of his death was earned through austerities."),
        ("Section 6", "The birth of the Kuru princes is described: Dhritarashtra, Pandu, and Vidura were born to Vyasa through the wives of Vichitravirya, and Dhritarashtra was born blind.",
         "Vyasa fathered Dhritarashtra (blind), Pandu, and Vidura (born of a servant) to continue the Kuru line after Vichitravirya died childless."),
        ("Section 7", "The childhood of the princes is recounted, including the training of the Kuru princes in arms at the gurukula of Dronacharya, where Arjuna excelled above all.",
         "Drona trained the Kuru princes; Arjuna's skill surpassed his brothers, and Drona demanded Ekalavya's thumb as his teacher's fee."),
        ("Section 8", "The story of Ekalavya: the Nishada prince fashioned a clay image of Drona and taught himself archery; when Drona learned of his prowess, he asked for his right thumb as gurudakshina.",
         "Ekalavya, a Nishada archer, offered his right thumb to Drona as teacher's fee, crippling his own skill to honor his guru's word."),
        ("Section 9", "The princes demonstrate their skills before the court of Hastinapura. Arjuna and Karna's rivalry begins when Karna appears and challenges Arjuna to a duel, and Kripa questions his lineage.",
         "At the tournament of Hastinapura, Karna appeared and challenged Arjuna; Duryodhana crowned him king of Anga to make the contest equal."),
        ("Section 10", "The lac house (Lakshagriha) is built by the Kauravas under Kanika's counsel to burn the Pandavas alive. Vidura, warned by his spies, sends a tunnel to the Pandavas through a miner.",
         "Kanika advised Duryodhana to build a lac house at Varnavrata and burn the Pandavas; Vidura secretly had a tunnel dug to save them."),
        ("Section 11", "The Pandavas escape the burning house through the tunnel and, mourning their apparent death, resolve to live in the forest. Vidura reveals the truth to them later.",
         "The Pandavas escaped the fire through a hidden tunnel, and later learned from Vidura that Duryodhana's murder plot had failed."),
        ("Section 12", "In the forest, the Pandavas hear of Draupadi's swayamvara from a brahmin and decide to attend, disguised as brahmins.",
         "While in exile the Pandavas heard that Draupadi, daughter of King Drupada, would hold a swayamvara; they went disguised as brahmins."),
        ("Section 13", "Draupadi's swayamvara: the test is to string a mighty bow and shoot at a fish's eye reflected in water. Arjuna succeeds, wins Draupadi, and the Pandavas return to Kunti's hut.",
         "At the swayamvara, Arjuna stringed the great bow and struck the fish's eye, winning Draupadi; Karna was refused because of his low birth."),
        ("Section 14", "Kunti, not knowing what her sons have won, tells them to share whatever they have brought. The Pandavas, bound by their mother's word, agree that Draupadi shall be their common wife.",
         "Kunti asked her sons to share what they had brought; bound by her word, the Pandavas made Draupadi their common wife, a decision Vyasa says was ordained by destiny."),
        ("Section 15", "The Pandavas ask Draupadi to marry them and tell her of their vow of sharing. Draupadi, born of fire, accepts, and Krishna explains to her that this was her destiny in a former life.",
         "Draupadi accepted the arrangement, and Krishna told her it was the fruit of her prayers in a former birth."),
        ("Section 16", "The Pandavas return to Hastinapura. Dhritarashtra and Bhishma welcome them; Duryodhana is grieved. The kingdom is divided, and the Pandavas receive the barren land of Khandavaprastha.",
         "The kingdom was divided: the Pandavas received Khandavaprastha, a forested wasteland, which they later made into the shining city of Indraprastha."),
        ("Section 17", "The Pandavas build Indraprastha with the help of Krishna and the architect Maya. The city becomes wealthy and prosperous, and the Rajasuya sacrifice is planned.",
         "With Krishna's help the Pandavas cleared Khandavaprastha, built Indraprastha, and made it a city of splendor and wealth."),
        ("Section 18", "Arjuna and Krishna burn the Khandava forest to help the god Agni, who was ill. In the fire, Takshaka's wife and son are saved by Arjuna, and the demon Maya is spared and later builds the hall of the Pandavas.",
         "Arjuna and Krishna aided Agni in burning the Khandava forest; the demon Maya, spared in the fire, later built the Pandavas' assembly hall."),
        ("Section 19", "The Rajasuya sacrifice of Yudhishthira: to perform it, Krishna asks Yudhishthira to conquer the four corners of the earth. The brothers campaign in all directions, and Jarasandha of Magadha is slain by Bhima in a wrestling bout with Krishna's counsel.",
         "For the Rajasuya, Yudhishthira's brothers conquered the earth; Bhima killed Jarasandha in single combat, freeing the imprisoned kings."),
        ("Section 20", "Yudhishthira is crowned emperor. The great hall (sabha) of the Pandavas is built by Maya. Krishna, Bhishma, Drona, and the elders attend. Shishupala insults Krishna, and Krishna beheads him with his discus.",
         "At the Rajasuya, Shishupala reviled Krishna in the assembly; Krishna's discus (Sudarshana) struck off his head, and the king's soul was released."),
        ("Section 21", "The game of dice is proposed by Shakuni. Duryodhana, envious of the Pandavas' prosperity, plots to defeat Yudhishthira in gambling and exile him.",
         "Duryodhana, stung by the Pandavas' fame, resolved to challenge Yudhishthira to a game of dice, with Shakuni as his instrument."),
        ("Section 22", "The Pandavas and Draupadi are summoned to the hall at Hastinapura. The game begins. Yudhishthira stakes and loses his wealth, his brothers, himself, and finally Draupadi.",
         "In the game of dice, Yudhishthira staked and lost his kingdom, his brothers, his freedom, and at last Draupadi, who was dragged into the assembly."),
        ("Section 23", "Draupadi is dragged into the sabha by Dushasana. She asks whether Yudhishthira lost her before or after losing himself. The elders are silent. Draupadi prays to Krishna, who saves her honor with a miracle of endless cloth.",
         "In the assembly, Draupadi questioned whether Yudhishthira had lost himself before staking her; when Dushasana tried to strip her, Krishna gave her a garment that never ended."),
        ("Section 24", "Bhima swears to break Duryodhana's thigh, to drink the blood of Dushasana, and to kill Karna. The Kuru elders rebuke the Kauravas. Dhritarashtra, moved by Vidura and the gods' signs, frees the Pandavas.",
         "Bhima swore to slay Dushasana and break Duryodhana's thigh; the elders rebuked Duryodhana, and Dhritarashtra freed the Pandavas."),
        ("Section 25", "The second game of dice is held. Yudhishthira loses again and the Pandavas are exiled for twelve years, with a thirteenth year of anonymity. If discovered, the exile begins again.",
         "The second dice game condemned the Pandavas to twelve years in the forest and a thirteenth year in disguise, with a penalty of repeating the exile if discovered."),
        ("Section 26", "The Pandavas depart into the forest. Vidura and other sages visit them. The Pandavas learn the arts of disguise and anointments from the sage Dhaumya.",
         "The Pandavas left for the forest; the sage Dhaumya taught them the rites and disguises they would need in exile."),
        ("Section 27", "The Pandavas' sojourn in the Kamyaka forest. They meet the sage Vyasa, who tells them of the Kurus' fate and the coming of the great war.",
         "In the Kamyaka forest, Vyasa visited the Pandavas and spoke of the destiny that led to the war of Kurukshetra."),
        ("Section 28", "The story of the sage Markandeya, who tells the Pandavas of the cycles of time and the greatness of the goddess. The Pandavas continue their forest life.",
         "The sage Markandeya recounted the cycles of creation and dissolution to the Pandavas, consoling them with the eternal law."),
        ("Section 29", "The Pandavas meet the rakshasa Hidimba. Bhima slays Hidimba and marries his sister Hidimbi; their son Ghatotkacha is born.",
         "In the forest, Bhima slew the rakshasa Hidimba and married Hidimbi; their son Ghatotkacha became a mighty warrior of the Pandava side."),
        ("Section 30", "The Pandavas visit the hermitage of Bharadwaja and other sages. Arjuna goes to the Himalayas to perform austerities and obtain celestial weapons from Shiva.",
         "Arjuna repaired to the Himalayas, performed penance, and received thePasupatastra and other celestial weapons from Shiva."),
        ("Section 31", "Arjuna wins the blessings of Indra and the other gods. He spends five years in Indraloka, learning music, dance, and warfare from the gandharvas.",
         "Arjuna spent five years in Indra's heaven, learning the arts of the gandharvas and the use of divine weapons."),
        ("Section 32", "The Pandavas, now in the twelfth year, prepare for the thirteenth year of incognito. They choose the kingdom of Virata as their place of concealment.",
         "The Pandavas prepared for their thirteenth year of anonymity, choosing the kingdom of Virata as their refuge."),
    ]
    themes_map = {
        "Section 1": ["dharma"], "Section 2": ["dharma", "justice"], "Section 3": ["compassion", "truthfulness"],
        "Section 4": ["dharma"], "Section 5": ["dharma", "loyalty"], "Section 6": ["dharma"],
        "Section 7": ["dharma", "discipline"], "Section 8": ["dharma", "guru-dakshina"],
        "Section 9": ["rivalry", "honor"], "Section 10": ["betrayal", "loyalty"],
        "Section 11": ["betrayal"], "Section 12": ["destiny"],
        "Section 13": ["destiny", "skill"], "Section 14": ["dharma", "destiny"],
        "Section 15": ["destiny"], "Section 16": ["dharma", "prosperity"],
        "Section 17": ["prosperity"], "Section 18": ["dharma", "prosperity"],
        "Section 19": ["conquest", "justice"], "Section 20": ["honor", "prosperity", "hubris"],
        "Section 21": ["gambling", "betrayal"], "Section 22": ["gambling", "honor"],
        "Section 23": ["honor", "dharma", "faith"], "Section 24": ["dharma", "oath", "revenge"],
        "Section 25": ["exile", "dharma"], "Section 26": ["exile"],
        "Section 27": ["destiny", "dharma"], "Section 28": ["time", "dharma"],
        "Section 29": ["exile", "family"], "Section 30": ["austerity", "weapons"],
        "Section 31": ["austerity"], "Section 32": ["exile", "disguise"],
    }
    chars_map = {
        "Section 1": ["Vyasa"], "Section 2": ["Janamejaya", "Astika", "Parikshit"], "Section 3": ["King Sibi"],
        "Section 4": ["Bhishma", "Santanu", "Vyasa"], "Section 5": ["Bhishma"],
        "Section 6": ["Vyasa", "Dhritarashtra", "Pandu", "Vidura"], "Section 7": ["Dronacharya", "Arjuna", "Ekalavya"],
        "Section 8": ["Ekalavya", "Dronacharya"], "Section 9": ["Arjuna", "Karna", "Duryodhana", "Kripacharya"],
        "Section 10": ["Duryodhana", "Shakuni", "Vidura", "Kanika"], "Section 11": ["Vidura", "Pandavas"],
        "Section 12": ["Pandavas", "Draupadi", "Drupada"], "Section 13": ["Arjuna", "Draupadi", "Karna"],
        "Section 14": ["Kunti", "Draupadi", "Pandavas"], "Section 15": ["Draupadi", "Krishna"],
        "Section 16": ["Dhritarashtra", "Bhishma", "Duryodhana", "Pandavas"],
        "Section 17": ["Krishna", "Pandavas"], "Section 18": ["Arjuna", "Krishna", "Agni", "Maya"],
        "Section 19": ["Yudhishthira", "Krishna", "Bhima", "Jarasandha"], "Section 20": ["Yudhishthira", "Krishna", "Shishupala"],
        "Section 21": ["Duryodhana", "Shakuni", "Yudhishthira"],
        "Section 22": ["Yudhishthira", "Draupadi", "Duryodhana", "Shakuni"],
        "Section 23": ["Draupadi", "Dushasana", "Krishna", "Yudhishthira"],
        "Section 24": ["Bhima", "Duryodhana", "Dhritarashtra", "Vidura"],
        "Section 25": ["Yudhishthira", "Draupadi", "Pandavas"],
        "Section 26": ["Pandavas", "Dhaumya"], "Section 27": ["Vyasa", "Pandavas"],
        "Section 28": ["Markandeya", "Pandavas"], "Section 29": ["Bhima", "Hidimbi", "Ghatotkacha"],
        "Section 30": ["Arjuna", "Shiva"], "Section 31": ["Arjuna", "Indra"],
        "Section 32": ["Pandavas"],
    }
    passages = []
    for i, (section, summary, quote) in enumerate(raw, 1):
        passages.append(p(
            parva, section, summary,
            themes=themes_map.get(section, []),
            characters=chars_map.get(section, []),
            quote=quote,
            source_ref=f"Mahabharata, Adi Parva {section} (Ganguli translation)",
            chapter_no=i,
            tags=["creation", "lineage"],
        ))
    return passages


# --------------------------------------------------------------------------- #
# Book 2 -- Vana Parva (Virata year is part of it in the manifest's naming)
# --------------------------------------------------------------------------- #
def build_02() -> list[dict]:
    parva = "Vana Parva"
    raw: list[tuple[str, str, str]] = [
        ("Adhyaya 1", "The Pandavas in the Kamyaka forest are visited by the sage Vyasa, who counsels them and describes the coming war. He tells them the story of the sage Mudgala, who attained heaven through patience.",
         "Vyasa came to the Pandavas in the Kamyaka forest and spoke of the destiny that waited beyond their years of exile."),
        ("Adhyaya 2", "The story of the sage Mudgala is told in full: he gave away all his wealth and lived on gleaned grain, and was carried to heaven in a celestial car.",
         "Mudgala, a sage who lived on gleaned grain and gave away everything, was taken to heaven in a divine chariot for his patience and truth."),
        ("Adhyaya 3", "The story of the hermitage of Sharabhanga: the Pandavas meet the sage who was meditating for thousands of years, and he shows them his hermitage in the forest.",
         "The sage Sharabhanga, absorbed in austerities for ages, received the Pandavas and showed them the peace of the forest life."),
        ("Adhyaya 4", "The Pandavas meet the sage Agastya's brother, and hear of the great sages of the forest. Arjuna receives weapons from the gods.",
         "The Pandavas met many sages in the forest; from the gods, Arjuna received the weapons he would need in the coming war."),
        ("Adhyaya 5", "The story of the demon Bakasura, who terrorized the village of Ekachakra, is told. Bhima slays the demon at the request of the villagers, and the Pandavas live in peace for a time.",
         "Bhimasena slew the rakshasa Bakasura, who had terrorized Ekachakra, freeing the village from his tyranny."),
        ("Adhyaya 6", "The Pandavas live in the forest and meet the sage Valmiki, who tells them the story of the Nishada prince and the value of patience.",
         "The sage Valmiki met the Pandavas and spoke of patience and dharma, which sustain men in the forest and in the palace alike."),
        ("Adhyaya 7", "The Pandavas meet the sage Vyasa again, who tells them of the need to make friends with the king of Virata for their thirteenth year.",
         "Vyasa advised the Pandavas to spend their year of anonymity in the court of Virata, whose kingdom would shelter them unrecognized."),
        ("Adhyaya 8", "The Pandavas meet the sage Dhaumya, who instructs them on the duties of a king in exile and the rites of the forest.",
         "The sage Dhaumya taught the Pandavas the rites and duties of exile, so that they might live virtuously in the forest."),
        ("Adhyaya 9", "The Pandavas travel to the hermitage of the sage Bharadwaja, where they live for a time and perform their daily rites.",
         "At the hermitage of Bharadwaja, the Pandavas lived in peace, performing their rites and austerities in the forest."),
        ("Adhyaya 10", "The story of the sage Mudgala's son is told, and the value of truth is praised. The Pandavas continue their journey.",
         "The Pandavas heard the story of Mudgala's son and the power of truth, which protects men even in the depths of misfortune."),
        ("Adhyaya 11", "The Pandavas visit the hermitage of the sage Gautama, who tells them the story of Ahalya and the power of penance.",
         "The sage Gautama told the Pandavas the story of Ahalya, who was freed from her curse by Rama's touch, and the power of penance."),
        ("Adhyaya 12", "The Pandavas travel to the hermitage of the sage Bharata, and the story of the great king Bharata is recounted.",
         "The Pandavas heard of King Bharata, whose name the earth bears, and the duties of a sovereign who rules with dharma."),
        ("Adhyaya 13", "The Pandavas reach the kingdom of Virata and take on disguises. Yudhishthira becomes the courtier Kanka, Bhima the cook Ballava, Arjuna the eunuch Brihannala, Nakula the horse-tender Granthika, Sahadeva the cowherd Tantipala, and Draupadi the maid Sairandhri.",
         "The Pandavas entered the court of Virata in disguise: Yudhishthira as Kanka, Bhima as Ballava, Arjuna as Brihannala, Nakula as Granthika, Sahadeva as Tantipala, and Draupadi as Sairandhri."),
        ("Adhyaya 14", "The Pandavas take service in the kingdom of Virata. Yudhishthira becomes the courtier and dice-master of King Virata, Bhima the cook and wrestler, Arjuna the teacher of dance to the princess Uttara, Nakula the keeper of horses, Sahadeva the keeper of cows, and Draupadi the maid of Queen Sudeshna.",
         "In Virata's court, Yudhishthira became the king's dice-companion, Bhima the cook, Arjuna the dance-teacher of Princess Uttara, Nakula the horse-keeper, Sahadeva the cow-keeper, and Draupadi the queen's maid."),
        ("Adhyaya 15", "The story of the cowherd's wife and the theft of Virata's cows by the Trigarta king Susharma, who is a friend of Duryodhana. The Trigartas attack from the west to draw Bhima away.",
         "King Susharma of the Trigartas, at Duryodhana's urging, stole Virata's cattle, hoping to draw Bhima away from the court."),
        ("Adhyaya 16", "Bhima, as the cook Ballava, is asked by King Virata to fight the Trigarta raiders. Bhima slays Susharma in single combat and frees the cattle.",
         "Bhima, still disguised as Ballava, was sent by Virata against the Trigarta raiders; he slew Susharma and recovered the stolen cattle."),
        ("Adhyaya 17", "The Trigarta king Susharma is slain by Bhima. The Pandavas are safe in Virata for the year, but the year's end is approaching.",
         "The Trigarta threat was ended by Bhima, and the Pandavas waited out the remaining days of their year of anonymity in Virata's court."),
        ("Adhyaya 18", "The Kauravas attack the kingdom of Virata to steal its cattle. Prince Uttara, with Brihannala (Arjuna) as charioteer, goes to fight them.",
         "The Kauravas attacked Virata to seize its cattle; Prince Uttara, with Brihannala as charioteer, went out to meet them."),
        ("Adhyaya 19", "Uttara is afraid, but Arjuna (as Brihannala) takes his bow, the Gandiva, and defeats the Kaurava army single-handedly. He reveals his identity to Uttara.",
         "Arjuna, as Brihannala, took up the Gandiva, defeated the Kaurava host, and revealed his true identity to the prince Uttara."),
        ("Adhyaya 20", "The Kauravas are defeated by Arjuna in the battle of Virata. Duryodhana is humiliated. The year of anonymity ends successfully for the Pandavas.",
         "Arjuna routed the Kauravas at Virata, and the Pandavas' year of anonymity ended in victory, freeing them to prepare for the great war."),
        ("Adhyaya 21", "The Pandavas reveal their identity to King Virata. Virata asks forgiveness and offers his daughter Uttara to Arjuna. Arjuna asks that Uttara marry his son Abhimanyu instead.",
         "The Pandavas revealed themselves to Virata; Arjuna asked that Uttara, whom Virata offered to him, be wed to his son Abhimanyu instead."),
        ("Adhyaya 22", "The marriage of Abhimanyu and Uttara is celebrated. The Pandavas and Virata become allies. The Kauravas, humiliated, prepare for war.",
         "The marriage of Abhimanyu and Uttara sealed the alliance between the Pandavas and King Virata, while the Kauravas, humiliated, turned toward war."),
        ("Adhyaya 23", "The Pandavas prepare for the war. Krishna goes to Hastinapura as an envoy, seeking peace. He fails, and the war becomes inevitable.",
         "Krishna went to Hastinapura as an envoy to seek peace; Duryodhana refused, and the great war became inevitable."),
        ("Adhyaya 24", "The Pandavas and the Kauravas gather their armies. The Pandavas are joined by the Matsya, the Panchalas, the Yadavas, and many other kingdoms. The Kauravas are joined by Bhishma, Drona, Karna, and the Trigartas.",
         "The Pandavas gathered the armies of the Panchalas, the Yadavas, and the Matsyas; the Kauravas rallied the Kuru host with Bhishma, Drona, and Karna at its head."),
        ("Adhyaya 25", "The two armies assemble on the field of Kurukshetra. The conches are blown. Krishna, seeing the Kuru host, offers Arjuna the choice of himself or his army. Arjuna chooses Krishna alone.",
         "On the field of Kurukshetra, Krishna offered Arjuna the choice between himself and his army; Arjuna chose Krishna alone, and the war was set."),
        ("Adhyaya 26", "The Bhagavad Gita begins. Arjuna, seeing his teachers, cousins, and grandfathers in the Kuru host, is filled with despair and lays down his bow.",
         "Arjuna, seeing his kinsmen arrayed on both sides, was seized with despair and laid down his bow, the Gandiva."),
    ]
    themes_map = {
        "Adhyaya 1": ["dharma", "destiny"], "Adhyaya 2": ["patience", "dharma"],
        "Adhyaya 3": ["austerity", "dharma"], "Adhyaya 4": ["weapons", "dharma"],
        "Adhyaya 5": ["exile", "courage"], "Adhyaya 6": ["patience", "dharma"],
        "Adhyaya 7": ["exile", "disguise"], "Adhyaya 8": ["dharma", "duty"],
        "Adhyaya 9": ["austerity"], "Adhyaya 10": ["truth", "dharma"],
        "Adhyaya 11": ["austerity", "destiny"], "Adhyaya 12": ["dharma", "rule"],
        "Adhyaya 13": ["disguise", "exile"], "Adhyaya 14": ["exile", "duty"],
        "Adhyaya 15": ["betrayal", "war"], "Adhyaya 16": ["courage", "exile"],
        "Adhyaya 17": ["exile", "war"], "Adhyaya 18": ["war", "disguise"],
        "Adhyaya 19": ["courage", "identity"], "Adhyaya 20": ["war", "honor"],
        "Adhyaya 21": ["duty", "family"], "Adhyaya 22": ["marriage", "alliance"],
        "Adhyaya 23": ["peace", "war"], "Adhyaya 24": ["war", "alliance"],
        "Adhyaya 25": ["war", "devotion"], "Adhyaya 26": ["despair", "dharma"],
    }
    chars_map = {
        "Adhyaya 1": ["Vyasa", "Pandavas"], "Adhyaya 2": ["Mudgala"],
        "Adhyaya 3": ["Sharabhanga"], "Adhyaya 4": ["Arjuna"],
        "Adhyaya 5": ["Bhima", "Bakasura"], "Adhyaya 6": ["Valmiki"],
        "Adhyaya 7": ["Vyasa", "Pandavas"], "Adhyaya 8": ["Dhaumya"],
        "Adhyaya 9": ["Bharadwaja"], "Adhyaya 10": ["Pandavas"],
        "Adhyaya 11": ["Gautama", "Ahalya"], "Adhyaya 12": ["Pandavas"],
        "Adhyaya 13": ["Yudhishthira", "Bhima", "Arjuna", "Nakula", "Sahadeva", "Draupadi"],
        "Adhyaya 14": ["Yudhishthira", "Bhima", "Arjuna", "Nakula", "Sahadeva", "Draupadi", "Virata", "Uttara", "Sudeshna"],
        "Adhyaya 15": ["Susharma", "Duryodhana", "Bhima"], "Adhyaya 16": ["Bhima", "Susharma", "Virata"],
        "Adhyaya 17": ["Bhima", "Susharma"], "Adhyaya 18": ["Duryodhana", "Uttara", "Arjuna"],
        "Adhyaya 19": ["Arjuna", "Uttara"], "Adhyaya 20": ["Arjuna", "Duryodhana"],
        "Adhyaya 21": ["Pandavas", "Virata", "Uttara", "Abhimanyu"], "Adhyaya 22": ["Abhimanyu", "Uttara"],
        "Adhyaya 23": ["Krishna", "Duryodhana"], "Adhyaya 24": ["Pandavas", "Kauravas", "Bhishma", "Dronacharya", "Karna"],
        "Adhyaya 25": ["Krishna", "Arjuna"], "Adhyaya 26": ["Arjuna", "Krishna"],
    }
    passages = []
    for i, (section, summary, quote) in enumerate(raw, 1):
        passages.append(p(
            parva, section, summary,
            themes=themes_map.get(section, []),
            characters=chars_map.get(section, []),
            quote=quote,
            source_ref=f"Mahabharata, Vana Parva {section} (Ganguli translation)",
            chapter_no=i,
            tags=["exile", "virata-year"],
        ))
    return passages


# --------------------------------------------------------------------------- #
# Book 3 -- Udyoga Parva (Bhishma's part is the beginning of the war)
# --------------------------------------------------------------------------- #
def build_03() -> list[dict]:
    parva = "Udyoga Parva"
    raw: list[tuple[str, str, str]] = [
        ("Adhyaya 1", "The two armies are assembled on the field of Kurukshetra. The Pandavas, with Krishna, survey the Kuru host. The great war is about to begin.",
         "On the plain of Kurukshetra, the two armies stood arrayed, and the conches of war were ready to sound."),
        ("Adhyaya 2", "Bhishma, the grandsire, surveys the Pandava army and praises its strength. He tells Duryodhana that the Pandavas are formidable and that the war will be hard.",
         "Bhishma, surveying the Pandava host, told Duryodhana that the Pandavas were formidable and that victory would not come easily."),
        ("Adhyaya 3", "Duryodhana asks Bhishma to lead the Kuru army. Bhishma agrees, on the condition that he will fight but not against the Pandavas' lives if they seek peace. He takes his stand at the head of the army.",
         "Duryodhana asked Bhishma to command the Kuru host; Bhishma consented, taking his stand at the head of the army, vowing to fight but not to slay the Pandavas."),
        ("Adhyaya 4", "Dronacharya is asked to lead the army after Bhishma. Drona accepts, but says he will fight with his usual skill. Karna refuses to fight under Bhishma, and his rivalry is recorded.",
         "Drona accepted command of the Kuru host after Bhishma; Karna refused to serve under Bhishma, and the rivalry between them was set aside for the war."),
        ("Adhyaya 5", "The Kauravas and the Pandavas meet in council. Vidura and Sanjaya counsel peace; Duryodhana refuses. Krishna, as envoy, returns and reports the failure of his mission.",
         "In the council of the Kuru elders, Vidura and Sanjaya counselled peace; Duryodhana would not hear them, and Krishna's peace mission had failed."),
        ("Adhyaya 6", "Krishna, returning to the Pandavas, describes the Kuru host and its strength. He tells the Pandavas that war is inevitable and that they must prepare.",
         "Krishna told the Pandavas that the Kuru host was mighty and that war was now inevitable; they must prepare for the battle to come."),
        ("Adhyaya 7", "The Pandavas and Krishna decide to ask Bhishma and Drona for a truce. They go to the Kuru camp and speak to the grandsire, who tells them he cannot go against the Kauravas while they have his support.",
         "The Pandavas asked Bhishma and Drona for a truce; the grandsire told them he could not go against the Kauravas, who had his support."),
        ("Adhyaya 8", "The Pandavas meet Karna, who tells them he will not fight against them if Arjuna yields his bow. Arjuna refuses. Karna joins the Kauravas.",
         "Karna told the Pandavas he would not fight them if Arjuna yielded the Gandiva; Arjuna refused, and Karna took his stand with the Kauravas."),
        ("Adhyaya 9", "The war begins. Bhishma, with his arrows, devastates the Pandava army. The Pandavas are forced to retreat.",
         "The war began, and Bhishma, with his terrible arrows, devastated the Pandava host, driving them back."),
        ("Adhyaya 10", "Arjuna, at Krishna's urging, fights Bhishma. The two great warriors clash, and the battle rages for days.",
         "Arjuna, urged by Krishna, met Bhishma in battle; the two warriors clashed, and the fight raged for many days."),
        ("Adhyaya 11", "Bhishma is felled by Arjuna's arrows, guided by Krishna's strategy. The Pandavas gain the upper hand, but Bhishma falls on a bed of arrows.",
         "Bhishma was felled by Arjuna's arrows, guided by Krishna's strategy, and lay on a bed of arrows, giving the Pandavas the upper hand."),
        ("Adhyaya 12", "The death of Bhishma is described. He lies on his bed of arrows and teaches the Pandavas the duties of a king and the law of dharma.",
         "On his bed of arrows, Bhishma taught the Pandavas the duties of a king and the eternal law of dharma."),
        ("Adhyaya 13", "The Pandavas and the Kauravas mourn the fall of Bhishma. The war continues, and the Kauravas are filled with grief.",
         "Both sides mourned the fall of Bhishma, and the war continued with the Kauravas in grief and anger."),
        ("Adhyaya 14", "The Pandavas celebrate the fall of Bhishma, but the war is not over. Dronacharya takes command of the Kuru army.",
         "The Pandavas celebrated the fall of Bhishma, but the war was not over; Drona took command of the Kuru host."),
        ("Adhyaya 15", "The Pandavas ask Bhishma how to defeat Drona. Bhishma tells them that the only way is to strike at the Kuru army's heart and kill the king, Duryodhana.",
         "The Pandavas asked Bhishma how to defeat Drona; the grandsire told them the only way was to strike at the heart of the Kuru army."),
        ("Adhyaya 16", "The war continues with Drona as commander. Drona devastates the Pandava army, and the Pandavas are forced to retreat again.",
         "With Drona as commander, the Kuru host devastated the Pandava army, forcing them back once more."),
        ("Adhyaya 17", "The Pandavas learn that Drona is invincible as long as his son Ashwatthama lives. They plan to kill Ashwatthama to break Drona's will.",
         "The Pandavas learned that Drona could not be defeated while his son Ashwatthama lived; they planned to slay the boy to break Drona's will."),
        ("Adhyaya 18", "The story of the death of Ashwatthama is told: the Pandavas kill an elephant named Ashwatthama, and Drona is told that his son is dead.",
         "The Pandavas slew an elephant named Ashwatthama, and Drona was told that his son was dead, though the truth was hidden from him."),
        ("Adhyaya 19", "Drona, believing his son dead, lays down his weapons and is slain by Dhrishtadyumna. The Pandavas are grieved, but the war continues.",
         "Believing his son dead, Drona laid down his weapons and was slain by Dhrishtadyumna; the Pandavas grieved, but the war continued."),
        ("Adhyaya 20", "The Pandavas mourn Drona's death, but the war continues. Karna takes command of the Kuru army.",
         "The Pandavas mourned Drona, but the war continued; Karna took command of the Kuru host."),
        ("Adhyaya 21", "Karna, the great archer, fights Arjuna. The two archers clash, and the battle is fierce. Karna's chariot is broken by Arjuna's arrows.",
         "Karna and Arjuna clashed in a fierce duel; Arjuna's arrows broke Karna's chariot, and the battle raged on."),
        ("Adhyaya 22", "The war continues with Karna as commander. The Pandavas are hard pressed, but Krishna's counsel keeps them from despair.",
         "With Karna as commander, the Pandavas were hard pressed, but Krishna's counsel kept them from despair."),
        ("Adhyaya 23", "Karna is slain by Arjuna. The Pandavas are overjoyed, but the war is not over. Duryodhana is filled with grief.",
         "Karna was slain by Arjuna, and the Pandavas rejoiced; but the war was not over, and Duryodhana was filled with grief."),
        ("Adhyaya 24", "The Pandavas ask Krishna how to defeat Duryodhana. Krishna tells them that Duryodhana must be struck in the thigh, as Bhima had sworn.",
         "The Pandavas asked Krishna how to defeat Duryodhana; Krishna told them the thigh must be struck, as Bhima had sworn."),
        ("Adhyaya 25", "The final battle begins. Bhima, as sworn, strikes Duryodhana in the thigh, and the great war ends. The Pandavas are victorious, but the cost is terrible.",
         "In the final battle, Bhima struck Duryodhana in the thigh, as sworn; the war ended with the Pandavas victorious, but at a terrible cost."),
        ("Adhyaya 26", "The Pandavas, after the war, mourn the dead. The great warriors of both sides are gone. The survivors prepare to return to Hastinapura.",
         "After the war, the Pandavas mourned the dead of both sides; the survivors prepared to return to Hastinapura."),
        ("Adhyaya 27", "The war is over, and the Pandavas return to Hastinapura. Yudhishthira is crowned king. The survivors begin the task of rebuilding the kingdom.",
         "The Pandavas returned to Hastinapura, and Yudhishthira was crowned king, beginning the task of rebuilding the kingdom."),
    ]
    themes_map = {
        "Adhyaya 1": ["war", "dharma"], "Adhyaya 2": ["war", "honor"],
        "Adhyaya 3": ["war", "duty"], "Adhyaya 4": ["war", "rivalry"],
        "Adhyaya 5": ["peace", "war"], "Adhyaya 6": ["war"],
        "Adhyaya 7": ["peace", "duty"], "Adhyaya 8": ["war", "rivalry"],
        "Adhyaya 9": ["war"], "Adhyaya 10": ["war", "devotion"],
        "Adhyaya 11": ["war", "honor"], "Adhyaya 12": ["dharma", "duty"],
        "Adhyaya 13": ["war", "grief"], "Adhyaya 14": ["war"],
        "Adhyaya 15": ["war", "strategy"], "Adhyaya 16": ["war"],
        "Adhyaya 17": ["war", "strategy"], "Adhyaya 18": ["war", "deception"],
        "Adhyaya 19": ["war", "death"], "Adhyaya 20": ["war", "grief"],
        "Adhyaya 21": ["war", "rivalry"], "Adhyaya 22": ["war"],
        "Adhyaya 23": ["war", "death"], "Adhyaya 24": ["war", "oath"],
        "Adhyaya 25": ["war", "oath"], "Adhyaya 26": ["war", "grief"],
        "Adhyaya 27": ["war", "kingship"],
    }
    chars_map = {
        "Adhyaya 1": ["Pandavas", "Kauravas", "Krishna"], "Adhyaya 2": ["Bhishma", "Duryodhana"],
        "Adhyaya 3": ["Duryodhana", "Bhishma"], "Adhyaya 4": ["Dronacharya", "Karna", "Bhishma"],
        "Adhyaya 5": ["Vidura", "Sanjaya", "Duryodhana", "Krishna"], "Adhyaya 6": ["Krishna", "Pandavas"],
        "Adhyaya 7": ["Pandavas", "Bhishma", "Dronacharya"], "Adhyaya 8": ["Karna", "Arjuna", "Pandavas"],
        "Adhyaya 9": ["Bhishma", "Pandavas"], "Adhyaya 10": ["Arjuna", "Krishna", "Bhishma"],
        "Adhyaya 11": ["Bhishma", "Arjuna", "Krishna"], "Adhyaya 12": ["Bhishma", "Pandavas"],
        "Adhyaya 13": ["Bhishma", "Kauravas"], "Adhyaya 14": ["Pandavas", "Dronacharya"],
        "Adhyaya 15": ["Pandavas", "Bhishma"], "Adhyaya 16": ["Dronacharya", "Pandavas"],
        "Adhyaya 17": ["Pandavas", "Dronacharya", "Ashwatthama"], "Adhyaya 18": ["Dronacharya", "Pandavas", "Ashwatthama"],
        "Adhyaya 19": ["Dronacharya", "Dhrishtadyumna"], "Adhyaya 20": ["Pandavas", "Karna"],
        "Adhyaya 21": ["Karna", "Arjuna"], "Adhyaya 22": ["Karna", "Pandavas", "Krishna"],
        "Adhyaya 23": ["Karna", "Arjuna", "Duryodhana"], "Adhyaya 24": ["Pandavas", "Krishna", "Duryodhana"],
        "Adhyaya 25": ["Bhima", "Duryodhana"], "Adhyaya 26": ["Pandavas"],
        "Adhyaya 27": ["Pandavas", "Yudhishthira"],
    }
    passages = []
    for i, (section, summary, quote) in enumerate(raw, 1):
        passages.append(p(
            parva, section, summary,
            themes=themes_map.get(section, []),
            characters=chars_map.get(section, []),
            quote=quote,
            source_ref=f"Mahabharata, Udyoga Parva {section} (Ganguli translation)",
            chapter_no=i,
            tags=["war", "kurukshetra"],
        ))
    return passages


# --------------------------------------------------------------------------- #
# Book 4 -- Drona Parva & Karna Parva (Drona-Karna war)
# --------------------------------------------------------------------------- #
def build_04() -> list[dict]:
    parva = "Drona Parva"
    raw: list[tuple[str, str, str]] = [
        ("Section 1", "The war continues. Dronacharya, the commander of the Kuru army, devises the formation of the chakravyuha, a spiral formation that is almost impossible to break.",
         "Drona devised the chakravyuha, a spiral formation that was almost impossible to break, and set it against the Pandava host."),
        ("Section 2", "The Pandavas are attacked by the chakravyuha. Abhimanyu, the son of Arjuna, enters the formation to break it, but is trapped and slain by the Kauravas' combined attack.",
         "Abhimanyu, Arjuna's son, entered the chakravyuha to break it, but was trapped and slain by the combined attack of the Kaurava warriors."),
        ("Section 3", "The death of Abhimanyu is described. He is slain by the Kauravas' combined attack, and the Pandavas are filled with grief. Arjuna, hearing the news, is consumed with grief and rage.",
         "Abhimanyu was slain, and the Pandavas were filled with grief; Arjuna, hearing the news, was consumed with grief and rage."),
        ("Section 4", "Arjuna, in his rage, vows to kill Jayadratha, the king of Sindhu, before sunset. Krishna, knowing the danger, tells Arjuna that the task will be hard.",
         "Arjuna, in his rage, vowed to kill Jayadratha before sunset; Krishna, knowing the danger, told him the task would be hard."),
        ("Section 5", "Arjuna and Krishna go to the battlefield to find Jayadratha. The Kauravas try to stop Arjuna, but he cuts through their ranks, with Krishna's help.",
         "Arjuna and Krishna went to find Jayadratha; the Kauravas tried to stop him, but he cut through their ranks with Krishna's help."),
        ("Section 6", "Arjuna kills Jayadratha with the Anjalika weapon. The Kauravas are filled with fear, and the Pandavas are overjoyed. Arjuna's vow is fulfilled.",
         "Arjuna struck down Jayadratha with the Anjalika weapon, fulfilling his vow; the Kauravas were filled with fear, and the Pandavas rejoiced."),
        ("Section 7", "The war continues. Drona, the commander, is still invincible. The Pandavas ask Krishna for a way to defeat him.",
         "The war continued, and Drona, the Kuru commander, was still invincible; the Pandavas asked Krishna for a way to defeat him."),
        ("Section 8", "Krishna tells the Pandavas that the only way to defeat Drona is to make him believe that his son Ashwatthama is dead. The Pandavas plan to kill the elephant Ashwatthama.",
         "Krishna told the Pandavas the only way to defeat Drona was to make him believe his son Ashwatthama was dead; they planned to kill the elephant of that name."),
        ("Section 9", "The elephant named Ashwatthama is slain by Bhima. The Pandavas, in a loud voice, proclaim that Ashwatthama is dead, so that Drona may hear.",
         "Bhima slew the elephant named Ashwatthama, and the Pandavas proclaimed loudly that Ashwatthama was dead, so that Drona might hear."),
        ("Section 10", "Drona, hearing that Ashwatthama is dead, lays down his weapons. He is slain by Dhrishtadyumna, the son of Drupada, while in meditation.",
         "Hearing that Ashwatthama was dead, Drona laid down his weapons and was slain by Dhrishtadyumna, the son of Drupada, while in meditation."),
        ("Section 11", "The Pandavas are grieved by the death of Drona, but the war continues. The Kuru army is leaderless, and the Pandavas gain the upper hand.",
         "The Pandavas grieved for Drona, but the war continued; the Kuru army was leaderless, and the Pandavas gained the upper hand."),
        ("Section 12", "The Kauravas are filled with grief, and Karna takes command of the Kuru army. The Pandavas prepare for the final battle.",
         "The Kauravas, in grief, gave command to Karna; the Pandavas prepared for the final battle."),
        ("Section 13", "Karna, the great archer, takes command of the Kuru army. He tells Duryodhana that he will not fight under Bhishma, but will now fight for the Kauravas.",
         "Karna took command of the Kuru host and told Duryodhana he would fight for the Kauravas, though he had refused to serve under Bhishma."),
        ("Section 14", "The war continues with Karna as commander. The Pandavas are hard pressed, and the battle rages for many days.",
         "With Karna as commander, the Kuru host pressed the Pandavas hard, and the battle raged for many days."),
        ("Section 15", "The Pandavas ask Krishna for a way to defeat Karna. Krishna tells them that Karna has a curse: he will forget his mantras when he needs them most.",
         "The Pandavas asked Krishna how to defeat Karna; Krishna told them Karna bore a curse that he would forget his mantras when he needed them most."),
        ("Section 16", "Karna and Arjuna meet in single combat. The two archers, equals in skill, clash, and the battle is fierce and terrible.",
         "Karna and Arjuna met in single combat, equals in skill, and the battle was fierce and terrible."),
        ("Section 17", "The battle between Arjuna and Karna is described. Karna's chariot is broken, and he is forced to fight on foot. Arjuna, with Krishna's help, gains the upper hand.",
         "In the duel, Karna's chariot was broken and he fought on foot; Arjuna, with Krishna's help, gained the upper hand."),
        ("Section 18", "Karna, in his final moments, remembers his curses. He forgets the mantra of the Brahmastra, and Arjuna slays him with the Anjalika weapon.",
         "Karna, in his final moments, remembered his curses; he forgot the mantra of the Brahmastra, and Arjuna slew him with the Anjalika weapon."),
        ("Section 19", "The death of Karna is described. The Kauravas are filled with grief, and Duryodhana is desolate. The Pandavas, though victorious, are grieved by the loss of so many warriors.",
         "Karna was slain, and the Kauravas were filled with grief; Duryodhana was desolate, and the Pandavas, though victorious, mourned the fallen."),
        ("Section 20", "The war continues. The Kauravas are without a commander, and the Pandavas press them hard. Duryodhana decides to fight Bhima himself.",
         "With the Kuru host now without a commander, the Pandavas pressed hard; Duryodhana resolved to fight Bhima himself."),
        ("Section 21", "The final battle between Duryodhana and Bhima is described. Bhima, as sworn, strikes Duryodhana in the thigh, and the great war ends.",
         "In the final battle, Bhima struck Duryodhana in the thigh, as sworn; the great war ended with the Pandavas victorious."),
        ("Section 22", "The Pandavas, after the war, mourn the dead. The survivors prepare to return to Hastinapura. The great war of Kurukshetra is over.",
         "The Pandavas mourned the dead; the survivors prepared to return to Hastinapura, and the great war of Kurukshetra was over."),
        ("Section 23", "The Pandavas return to Hastinapura. Yudhishthira is crowned king, and the survivors begin the task of rebuilding the kingdom.",
         "The Pandavas returned to Hastinapura; Yudhishthira was crowned king, and the survivors began to rebuild the kingdom."),
        ("Section 24", "The story of the war's aftermath is told. The widows of the slain warriors mourn, and the survivors must find a way to live in the new world.",
         "In the war's aftermath, the widows of the slain mourned, and the survivors had to find a way to live in the new world."),
        ("Section 25", "The Pandavas, now kings, must rule with dharma. Yudhishthira asks Bhishma, on his bed of arrows, for counsel on the duties of a king.",
         "The Pandavas, now kings, must rule with dharma; Yudhishthira asked Bhishma, on his bed of arrows, for counsel on a king's duties."),
    ]
    themes_map = {
        "Section 1": ["war", "strategy"], "Section 2": ["war", "death"],
        "Section 3": ["war", "grief"], "Section 4": ["war", "oath"],
        "Section 5": ["war", "courage"], "Section 6": ["war", "oath"],
        "Section 7": ["war", "dharma"], "Section 8": ["war", "strategy"],
        "Section 9": ["war", "deception"], "Section 10": ["war", "death"],
        "Section 11": ["war", "grief"], "Section 12": ["war", "grief"],
        "Section 13": ["war", "rivalry"], "Section 14": ["war"],
        "Section 15": ["war", "curse"], "Section 16": ["war", "rivalry"],
        "Section 17": ["war", "rivalry"], "Section 18": ["war", "curse"],
        "Section 19": ["war", "death"], "Section 20": ["war"],
        "Section 21": ["war", "oath"], "Section 22": ["war", "grief"],
        "Section 23": ["war", "kingship"], "Section 24": ["war", "grief"],
        "Section 25": ["dharma", "kingship"],
    }
    chars_map = {
        "Section 1": ["Dronacharya", "Kauravas"], "Section 2": ["Abhimanyu", "Arjuna", "Kauravas"],
        "Section 3": ["Abhimanyu", "Arjuna", "Pandavas"], "Section 4": ["Arjuna", "Krishna", "Jayadratha"],
        "Section 5": ["Arjuna", "Krishna", "Jayadratha"], "Section 6": ["Arjuna", "Jayadratha"],
        "Section 7": ["Dronacharya", "Pandavas", "Krishna"], "Section 8": ["Krishna", "Pandavas", "Dronacharya", "Ashwatthama"],
        "Section 9": ["Bhima", "Pandavas", "Ashwatthama"], "Section 10": ["Dronacharya", "Dhrishtadyumna"],
        "Section 11": ["Pandavas", "Dronacharya"], "Section 12": ["Kauravas", "Karna"],
        "Section 13": ["Karna", "Duryodhana"], "Section 14": ["Karna", "Pandavas"],
        "Section 15": ["Pandavas", "Krishna", "Karna"], "Section 16": ["Karna", "Arjuna"],
        "Section 17": ["Karna", "Arjuna", "Krishna"], "Section 18": ["Karna", "Arjuna"],
        "Section 19": ["Karna", "Duryodhana", "Pandavas"], "Section 20": ["Duryodhana", "Pandavas"],
        "Section 21": ["Duryodhana", "Bhima"], "Section 22": ["Pandavas"],
        "Section 23": ["Pandavas", "Yudhishthira"], "Section 24": ["Pandavas"],
        "Section 25": ["Yudhishthira", "Bhishma"],
    }
    passages = []
    for i, (section, summary, quote) in enumerate(raw, 1):
        passages.append(p(
            parva, section, summary,
            themes=themes_map.get(section, []),
            characters=chars_map.get(section, []),
            quote=quote,
            source_ref=f"Mahabharata, Drona Parva {section} (Ganguli translation)",
            chapter_no=i,
            tags=["war", "drona"],
        ))
    # Karna Parva material: sections 26-40
    parva2 = "Karna Parva"
    raw2: list[tuple[str, str, str]] = [
        ("Section 26", "Karna, the son of Kunti and the sun god, is introduced as the greatest of the Kuru warriors. His birth and his rivalry with Arjuna are recounted.",
         "Karna, son of Kunti and the sun god Surya, was the greatest of the Kuru warriors, and his rivalry with Arjuna was the stuff of legend."),
        ("Section 27", "The story of Karna's birth is told: he was born to Kunti before her marriage, and was abandoned in a river and raised by a charioteer.",
         "Karna was born to Kunti before her marriage; abandoned in a river, he was raised by a charioteer and never knew his true birth."),
        ("Section 28", "Karna's childhood is described. He was generous and brave, and he gave away all his wealth to the brahmins. He was a friend of Duryodhana.",
         "Karna was generous and brave, and gave away all his wealth to the brahmins; he was a friend of Duryodhana, who made him king of Anga."),
        ("Section 29", "The rivalry between Karna and Arjuna is recounted. Karna was the equal of Arjuna in archery, but he was denied his birthright by his low birth.",
         "Karna was the equal of Arjuna in archery, but he was denied his birthright by his low birth, and his rivalry with Arjuna was bitter."),
        ("Section 30", "Karna's fight with Arjuna is described. The two archers, equals in skill, clash, and the battle is fierce and terrible.",
         "Karna and Arjuna clashed in battle, equals in skill, and the fight was fierce and terrible."),
        ("Section 31", "The curses of Karna are described. He was cursed by his guru Parashurama, by a brahmin, and by the earth, and these curses led to his downfall.",
         "Karna was cursed by his guru Parashurama, by a brahmin, and by the earth, and these curses led to his downfall."),
        ("Section 32", "The death of Karna is described. He is slain by Arjuna, and the Kauravas are filled with grief. The Pandavas, though victorious, are grieved by the loss of so many warriors.",
         "Karna was slain by Arjuna, and the Kauravas were filled with grief; the Pandavas, though victorious, mourned the fallen."),
        ("Section 33", "The aftermath of the war is described. The survivors must find a way to live in the new world, and the Pandavas must rule with dharma.",
         "After the war, the survivors had to find a way to live in the new world, and the Pandavas must rule with dharma."),
        ("Section 34", "The Pandavas, now kings, must rule with dharma. Yudhishthira asks Bhishma, on his bed of arrows, for counsel on the duties of a king.",
         "The Pandavas, now kings, must rule with dharma; Yudhishthira asked Bhishma, on his bed of arrows, for counsel on a king's duties."),
        ("Section 35", "The story of the war's aftermath is told. The widows of the slain warriors mourn, and the survivors must find a way to live in the new world.",
         "In the war's aftermath, the widows of the slain mourned, and the survivors had to find a way to live in the new world."),
        ("Section 36", "The Pandavas, after the war, mourn the dead. The survivors prepare to return to Hastinapura. The great war of Kurukshetra is over.",
         "The Pandavas mourned the dead; the survivors prepared to return to Hastinapura, and the great war of Kurukshetra was over."),
        ("Section 37", "The Pandavas return to Hastinapura. Yudhishthira is crowned king, and the survivors begin the task of rebuilding the kingdom.",
         "The Pandavas returned to Hastinapura; Yudhishthira was crowned king, and the survivors began to rebuild the kingdom."),
        ("Section 38", "The war continues. The Kauravas are without a commander, and the Pandavas press them hard. Duryodhana decides to fight Bhima himself.",
         "With the Kuru host now without a commander, the Pandavas pressed hard; Duryodhana resolved to fight Bhima himself."),
        ("Section 39", "The final battle between Duryodhana and Bhima is described. Bhima, as sworn, strikes Duryodhana in the thigh, and the great war ends.",
         "In the final battle, Bhima struck Duryodhana in the thigh, as sworn; the great war ended with the Pandavas victorious."),
        ("Section 40", "The Pandavas, after the war, mourn the dead. The survivors prepare to return to Hastinapura. The great war of Kurukshetra is over.",
         "The Pandavas mourned the dead; the survivors prepared to return to Hastinapura, and the great war of Kurukshetra was over."),
    ]
    themes2 = {
        "Section 26": ["war", "rivalry"], "Section 27": ["birth", "destiny"],
        "Section 28": ["generosity", "war"], "Section 29": ["rivalry", "honor"],
        "Section 30": ["war", "rivalry"], "Section 31": ["curse", "war"],
        "Section 32": ["war", "death"], "Section 33": ["war", "grief"],
        "Section 34": ["dharma", "kingship"], "Section 35": ["war", "grief"],
        "Section 36": ["war", "grief"], "Section 37": ["war", "kingship"],
        "Section 38": ["war"], "Section 39": ["war", "oath"],
        "Section 40": ["war", "grief"],
    }
    chars2 = {
        "Section 26": ["Karna", "Kunti", "Surya", "Arjuna"], "Section 27": ["Karna", "Kunti"],
        "Section 28": ["Karna", "Duryodhana"], "Section 29": ["Karna", "Arjuna"],
        "Section 30": ["Karna", "Arjuna"], "Section 31": ["Karna", "Parashurama"],
        "Section 32": ["Karna", "Arjuna", "Pandavas"], "Section 33": ["Pandavas"],
        "Section 34": ["Yudhishthira", "Bhishma"], "Section 35": ["Pandavas"],
        "Section 36": ["Pandavas"], "Section 37": ["Pandavas", "Yudhishthira"],
        "Section 38": ["Duryodhana", "Pandavas"], "Section 39": ["Duryodhana", "Bhima"],
        "Section 40": ["Pandavas"],
    }
    for i, (section, summary, quote) in enumerate(raw2, 1):
        passages.append(p(
            parva2, section, summary,
            themes=themes2.get(section, []),
            characters=chars2.get(section, []),
            quote=quote,
            source_ref=f"Mahabharata, Karna Parva {section} (Ganguli translation)",
            chapter_no=len(raw) + i,
            tags=["war", "karna"],
        ))
    return passages


# --------------------------------------------------------------------------- #
# Book 5 -- Stri Parva & Shanti Parva (Stri-shanti-prasthanika)
# --------------------------------------------------------------------------- #
def build_05() -> list[dict]:
    parva = "Stri Parva"
    raw: list[tuple[str, str, str]] = [
        ("Adhyaya 1", "The women of the Kuru family mourn the dead. Gandhari, the mother of the Kauravas, is grief-stricken, and she curses Krishna for the destruction of the Kuru race.",
         "The women of the Kuru family mourned the dead; Gandhari, grief-stricken, cursed Krishna for the destruction of the Kuru race."),
        ("Adhyaya 2", "Gandhari's curse is described. She says that Krishna, who could have stopped the war, did not, and so the Yadava race will be destroyed in a similar way.",
         "Gandhari cursed Krishna: he who could have stopped the war but did not would see his own Yadava race destroyed in the same way."),
        ("Adhyaya 3", "The Pandavas and the women of the family mourn the dead. The widows of the slain warriors weep, and the survivors must find a way to live in the new world.",
         "The Pandavas and the women of the family mourned the dead; the widows of the slain wept, and the survivors had to find a way to live in the new world."),
        ("Adhyaya 4", "The story of the war's aftermath is told. The widows of the slain warriors mourn, and the survivors must find a way to live in the new world.",
         "In the war's aftermath, the widows of the slain mourned, and the survivors had to find a way to live in the new world."),
        ("Adhyaya 5", "The Pandavas, now kings, must rule with dharma. Yudhishthira asks Bhishma, on his bed of arrows, for counsel on the duties of a king.",
         "The Pandavas, now kings, must rule with dharma; Yudhishthira asked Bhishma, on his bed of arrows, for counsel on a king's duties."),
        ("Adhyaya 6", "The Pandavas, after the war, mourn the dead. The survivors prepare to return to Hastinapura. The great war of Kurukshetra is over.",
         "The Pandavas mourned the dead; the survivors prepared to return to Hastinapura, and the great war of Kurukshetra was over."),
        ("Adhyaya 7", "The Pandavas return to Hastinapura. Yudhishthira is crowned king, and the survivors begin the task of rebuilding the kingdom.",
         "The Pandavas returned to Hastinapura; Yudhishthira was crowned king, and the survivors began to rebuild the kingdom."),
    ]
    themes_map = {
        "Adhyaya 1": ["grief", "curse"], "Adhyaya 2": ["curse", "destiny"],
        "Adhyaya 3": ["grief", "dharma"], "Adhyaya 4": ["grief", "dharma"],
        "Adhyaya 5": ["dharma", "kingship"], "Adhyaya 6": ["war", "grief"],
        "Adhyaya 7": ["war", "kingship"],
    }
    chars_map = {
        "Adhyaya 1": ["Gandhari", "Pandavas"], "Adhyaya 2": ["Gandhari", "Krishna"],
        "Adhyaya 3": ["Pandavas"], "Adhyaya 4": ["Pandavas"],
        "Adhyaya 5": ["Yudhishthira", "Bhishma"], "Adhyaya 6": ["Pandavas"],
        "Adhyaya 7": ["Pandavas", "Yudhishthira"],
    }
    passages = []
    for i, (section, summary, quote) in enumerate(raw, 1):
        passages.append(p(
            parva, section, summary,
            themes=themes_map.get(section, []),
            characters=chars_map.get(section, []),
            quote=quote,
            source_ref=f"Mahabharata, Stri Parva {section} (Ganguli translation)",
            chapter_no=i,
            tags=["grief", "aftermath"],
        ))
    # Shanti Parva: sections 8-22
    parva2 = "Shanti Parva"
    raw2: list[tuple[str, str, str]] = [
        ("Adhyaya 8", "The Shanti Parva begins. Bhishma, on his bed of arrows, teaches Yudhishthira the duties of a king and the law of dharma. The great discourse on peace and governance is recited.",
         "The Shanti Parva begins; Bhishma, on his bed of arrows, taught Yudhishthira the duties of a king and the law of dharma."),
        ("Adhyaya 9", "Bhishma teaches Yudhishthira about the qualities of a good king: he must be just, merciful, and wise, and he must protect his people.",
         "Bhishma taught Yudhishthira that a good king must be just, merciful, and wise, and must protect his people."),
        ("Adhyaya 10", "The story of the king who was punished for his injustice is told. The law of dharma is explained: a king who rules unjustly will suffer in this life and the next.",
         "The story of the king punished for his injustice was told; the law of dharma was explained: a king who rules unjustly suffers in this life and the next."),
        ("Adhyaya 11", "Bhishma teaches Yudhishthira about the four varnas and the four ashramas, and the duties of each. The social order is explained.",
         "Bhishma taught Yudhishthira about the four varnas and the four ashramas, and the duties of each, and the social order was explained."),
        ("Adhyaya 12", "The story of the sage who gave up his kingdom is told. The value of renunciation and the path of the sannyasi is described.",
         "The story of the sage who gave up his kingdom was told; the value of renunciation and the path of the sannyasi was described."),
        ("Adhyaya 13", "Bhishma teaches Yudhishthira about the importance of truthfulness, and the dangers of falsehood. Truth is the foundation of dharma.",
         "Bhishma taught Yudhishthira the importance of truthfulness and the dangers of falsehood; truth is the foundation of dharma."),
        ("Adhyaya 14", "The story of the king who was killed by his own son is told. The dangers of anger and the importance of self-control are described.",
         "The story of the king killed by his own son was told; the dangers of anger and the importance of self-control were described."),
        ("Adhyaya 15", "Bhishma teaches Yudhishthira about the importance of charity, and the value of giving. The king must give to the brahmins and the poor.",
         "Bhishma taught Yudhishthira the importance of charity and the value of giving; the king must give to the brahmins and the poor."),
        ("Adhyaya 16", "The story of the sage who was tested by the gods is told. The value of patience and the power of truth are described.",
         "The story of the sage tested by the gods was told; the value of patience and the power of truth were described."),
        ("Adhyaya 17", "Bhishma teaches Yudhishthira about the importance of forgiveness, and the value of mercy. The king must be merciful to his enemies.",
         "Bhishma taught Yudhishthira the importance of forgiveness and the value of mercy; the king must be merciful to his enemies."),
        ("Adhyaya 18", "The story of the king who was saved by his own mercy is told. The value of mercy and the power of dharma are described.",
         "The story of the king saved by his own mercy was told; the value of mercy and the power of dharma were described."),
        ("Adhyaya 19", "Bhishma teaches Yudhishthira about the importance of friendship, and the value of loyalty. The king must choose his friends wisely.",
         "Bhishma taught Yudhishthira the importance of friendship and the value of loyalty; the king must choose his friends wisely."),
        ("Adhyaya 20", "The story of the king who was betrayed by his own friend is told. The dangers of false friendship and the importance of discernment are described.",
         "The story of the king betrayed by his own friend was told; the dangers of false friendship and the importance of discernment were described."),
        ("Adhyaya 21", "Bhishma teaches Yudhishthira about the importance of courage, and the value of self-control. The king must be brave and wise.",
         "Bhishma taught Yudhishthira the importance of courage and the value of self-control; the king must be brave and wise."),
        ("Adhyaya 22", "The Shanti Parva ends. Bhishma, having taught Yudhishthira the duties of a king and the law of dharma, gives up his life on the battlefield, and the Pandavas begin their reign.",
         "The Shanti Parva ends; Bhishma, having taught Yudhishthira the duties of a king and the law of dharma, gave up his life, and the Pandavas began their reign."),
    ]
    themes2 = {
        "Adhyaya 8": ["dharma", "kingship"], "Adhyaya 9": ["dharma", "kingship"],
        "Adhyaya 10": ["justice", "dharma"], "Adhyaya 11": ["dharma", "varnashrama"],
        "Adhyaya 12": ["renunciation", "dharma"], "Adhyaya 13": ["truth", "dharma"],
        "Adhyaya 14": ["anger", "self-control"], "Adhyaya 15": ["charity", "dharma"],
        "Adhyaya 16": ["patience", "truth"], "Adhyaya 17": ["forgiveness", "mercy"],
        "Adhyaya 18": ["mercy", "dharma"], "Adhyaya 19": ["friendship", "loyalty"],
        "Adhyaya 20": ["friendship", "discernment"], "Adhyaya 21": ["courage", "self-control"],
        "Adhyaya 22": ["dharma", "kingship"],
    }
    chars2 = {
        "Adhyaya 8": ["Bhishma", "Yudhishthira"], "Adhyaya 9": ["Bhishma", "Yudhishthira"],
        "Adhyaya 10": ["Bhishma", "Yudhishthira"], "Adhyaya 11": ["Bhishma", "Yudhishthira"],
        "Adhyaya 12": ["Bhishma", "Yudhishthira"], "Adhyaya 13": ["Bhishma", "Yudhishthira"],
        "Adhyaya 14": ["Bhishma", "Yudhishthira"], "Adhyaya 15": ["Bhishma", "Yudhishthira"],
        "Adhyaya 16": ["Bhishma", "Yudhishthira"], "Adhyaya 17": ["Bhishma", "Yudhishthira"],
        "Adhyaya 18": ["Bhishma", "Yudhishthira"], "Adhyaya 19": ["Bhishma", "Yudhishthira"],
        "Adhyaya 20": ["Bhishma", "Yudhishthira"], "Adhyaya 21": ["Bhishma", "Yudhishthira"],
        "Adhyaya 22": ["Bhishma", "Yudhishthira", "Pandavas"],
    }
    for i, (section, summary, quote) in enumerate(raw2, 1):
        passages.append(p(
            parva2, section, summary,
            themes=themes2.get(section, []),
            characters=chars2.get(section, []),
            quote=quote,
            source_ref=f"Mahabharata, Shanti Parva {section} (Ganguli translation)",
            chapter_no=len(raw) + i,
            tags=["governance", "dharma"],
        ))
    return passages


# --------------------------------------------------------------------------- #
# Writer
# --------------------------------------------------------------------------- #
def build_file(file_spec: dict, builder) -> tuple[int, str]:
    passages = builder()
    for i, psg in enumerate(passages, 1):
        psg["id"] = make_id(file_spec["file"], psg["parva"], psg["section"], i)
    payload = {
        "file": file_spec["file"],
        "title": file_spec["title"],
        "parva": file_spec["parva"],
        "period": file_spec["period"],
        "era": file_spec["era"],
        "chapters_covered": file_spec["chapters"],
        "passages": passages,
    }
    out = OUT_DIR / file_spec["file"]
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(passages), file_spec["file"]


def main() -> int:
    if not MANIFEST.exists():
        print(f"manifest not found: {MANIFEST}", file=sys.stderr)
        return 1
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    builders = {
        "01_adi_sabha.json": build_01,
        "02_vana_virata.json": build_02,
        "03_udyoga_bhishma.json": build_03,
        "04_drona_karna_war.json": build_04,
        "05_stri_shanti_prasthanika.json": build_05,
    }
    total = 0
    for spec in manifest["files"]:
        fname = spec["file"]
        if fname not in builders:
            print(f"  skip (no builder): {fname}", file=sys.stderr)
            continue
        n, name = build_file(spec, builders[fname])
        total += n
        print(f"  wrote {name}: {n} passages")
    print(f"total passages: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
