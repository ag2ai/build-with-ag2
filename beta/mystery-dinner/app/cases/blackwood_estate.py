"""The Blackwood Estate — hand-authored case for Slice 3.

Ground truth: Julian (the nephew) strangled Arthur in the study at ~21:45
for the inheritance. Every other suspect lies about something unrelated to
the murder.

Data sources use HH:MM 24-hour timestamps. GPS coordinates are fictional but
internally consistent: the study is at 40.8100,-73.9500; the kitchen at
40.8101,-73.9501; the gardens at 40.8105,-73.9505; the gate at
40.8099,-73.9499. Anyone *outside* the estate has very different coordinates.

Victim's Manhattan apartment (Eleanor's alibi-breaker, unrelated to murder):
40.7580,-73.9855.
Eleanor's own apartment: 40.7128,-74.0060.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SuspectProfile:
    name: str  # Lowercase key used in routing and context keys
    display_name: str
    occupation: str
    emoji: str
    public_alibi: str
    private_truth: str
    image: str = ""  # filename under /images (set by case module)
    dossier: dict[str, list[tuple]] = field(default_factory=dict)


CASE_TITLE = "The Blackwood Estate"
CASE_BANNER = "loc_estate.png"
VICTIM = "Arthur Blackwood"
MURDER_WINDOW = ("21:30", "22:00")
MURDER_LOCATION = "study"
KILLER = "julian"

ELEANOR = SuspectProfile(
    name="eleanor",
    display_name="Eleanor Price",
    occupation="Librarian · victim's colleague",
    emoji="📚",
    image="ppl_librarian.png",
    public_alibi="Home all evening, reading a novel. Thursday routine.",
    private_truth=(
        "I left home at 21:35, went to the VICTIM'S MANHATTAN APARTMENT "
        "(not the estate) at 21:40 to return a rare book I had borrowed, "
        "stayed until 22:15, and returned home by 22:22. I was not at "
        "the estate. I am NOT the killer."
    ),
    dossier={
        "smart_home": [
            ("19:30", "front_door", "locked"),
            ("19:32", "living_room", "lights_on"),
            ("21:35", "front_door", "unlocked"),
            ("21:36", "front_door", "locked"),
            ("22:21", "front_door", "unlocked"),
            ("22:22", "front_door", "locked"),
            ("23:10", "bedroom", "lights_off"),
        ],
        # NOTE: 40.7580,-73.9855 is VICTIM'S MANHATTAN APARTMENT (not estate).
        # The estate is 40.81xx,-73.95xx. Detective must spot this.
        "gps": [
            ("19:32", 40.7128, -74.0060),
            ("20:15", 40.7128, -74.0060),
            ("21:40", 40.7580, -73.9855),  # victim's apartment — not estate
            ("21:55", 40.7580, -73.9855),
            ("22:22", 40.7128, -74.0060),
        ],
        "phone_log": [
            ("18:45", "outgoing", "bookstore", 180),
            ("20:02", "incoming", "mother", 420),
            ("22:30", "outgoing", "unknown_number", 45),
        ],
    },
)

MARCO = SuspectProfile(
    name="marco",
    display_name="Marco Vasile",
    occupation="Chef · hired for the dinner",
    emoji="👨‍🍳",
    image="ppl_chef.png",
    public_alibi="Working the kitchen all night — canapés, main, dessert service.",
    private_truth=(
        "I was in the pantry doing a line of cocaine at 21:40 — total of "
        "about 6 minutes. I did NOT leave the kitchen wing. I am NOT the "
        "killer but will lie to hide the drug use."
    ),
    dossier={
        # CCTV camera IDs: 'kitchen', 'pantry', 'hall_east', 'study_door'
        "cctv": [
            ("20:00", "kitchen", "marco_visible"),
            ("20:30", "kitchen", "marco_visible"),
            ("21:00", "kitchen", "marco_visible"),
            ("21:15", "kitchen", "marco_visible"),
            ("21:38", "pantry", "marco_enters"),
            ("21:44", "pantry", "marco_exits"),
            ("21:45", "kitchen", "marco_visible"),
            ("22:00", "kitchen", "marco_visible"),
            ("22:30", "kitchen", "marco_visible"),
        ],
        "gps": [
            ("19:00", 40.8101, -73.9501),  # kitchen
            ("20:30", 40.8101, -73.9501),
            ("21:40", 40.8101, -73.9501),
            ("22:00", 40.8101, -73.9501),
        ],
    },
)

JULIAN = SuspectProfile(  # <-- KILLER
    name="julian",
    display_name="Julian Blackwood",
    occupation="Nephew · sole heir",
    emoji="🎩",
    image="ppl_heir_1.png",
    public_alibi=(
        "On the patio from 21:15 to 22:00, on a phone call with my lawyer "
        "about estate paperwork. Came inside only after hearing screams."
    ),
    private_truth=(
        "I AM THE KILLER. I entered the study at 21:42, strangled my "
        "uncle, and left at 21:50. My 'lawyer call' is a fiction — no "
        "such call exists in my records. My GPS puts me inside the house "
        "near the study, not on the patio. I will lie aggressively."
    ),
    dossier={
        # No call to a lawyer exists. Julian will either invent one (lie
        # without forced truth) or be caught by phone_log showing nothing.
        "phone_log": [
            ("17:30", "outgoing", "art_dealer", 600),
            ("19:15", "incoming", "mother", 180),
            ("22:18", "outgoing", "police_dispatch", 120),
        ],
        # Patio = 40.8108,-73.9504 (fictionally).
        # Study  = 40.8100,-73.9500.
        # Julian's GPS shows he was NEAR THE STUDY during murder window.
        "gps": [
            ("20:30", 40.8108, -73.9504),  # patio (genuine, earlier)
            ("21:15", 40.8108, -73.9504),  # patio
            ("21:40", 40.8100, -73.9500),  # STUDY — entering
            ("21:45", 40.8100, -73.9500),  # STUDY — during murder
            ("21:50", 40.8100, -73.9500),  # STUDY — leaving
            ("22:00", 40.8108, -73.9504),  # back on patio before alarm
        ],
        "keycard": [
            ("18:00", "main_entrance", "entered"),
            ("21:42", "study_door", "entered"),  # damning
            ("21:50", "study_door", "exited"),  # damning
            ("22:17", "main_entrance", "exited_rejoined_group"),
        ],
    },
)

DR_CHEN = SuspectProfile(
    name="dr_chen",
    display_name="Dr. Iris Chen",
    occupation="Family physician",
    emoji="🩺",
    image="ppl_doctor.png",
    public_alibi="In the library the whole evening, catching up on medical journals.",
    private_truth=(
        "Telling the truth entirely. I was in the library reading from "
        "20:15 to 22:10. I am innocent. My GPS, keycard, and health-watch "
        "all corroborate this perfectly. I have nothing to hide."
    ),
    dossier={
        "gps": [
            ("20:15", 40.8103, -73.9502),  # library
            ("21:00", 40.8103, -73.9502),
            ("21:45", 40.8103, -73.9502),
            ("22:10", 40.8103, -73.9502),
        ],
        "keycard": [
            ("20:14", "library_door", "entered"),
            ("22:12", "library_door", "exited"),
        ],
        "smart_watch": [
            ("20:00", 62, 0),
            ("21:00", 58, 0),
            ("21:45", 60, 0),  # resting heart rate during murder
            ("22:15", 68, 42),  # mild activity after leaving library
        ],
    },
)

RHEA = SuspectProfile(
    name="rhea",
    display_name="Rhea Alder",
    occupation="Gardener · lives on the estate",
    emoji="🌿",
    image="ppl_gardener.png",
    public_alibi="Tending the greenhouse until 22:30, as I do every Thursday.",
    private_truth=(
        "I was in the east gardens between 21:20 and 22:15, but not "
        "alone — I was meeting my lover (a married villager). I will "
        "lie to hide the affair. I am NOT the killer."
    ),
    dossier={
        "gps": [
            ("20:00", 40.8106, -73.9507),  # greenhouse
            ("21:00", 40.8106, -73.9507),
            ("21:25", 40.8109, -73.9510),  # EAST GARDENS (not greenhouse)
            ("21:45", 40.8109, -73.9510),
            ("22:10", 40.8109, -73.9510),
            ("22:30", 40.8106, -73.9507),  # back at greenhouse
        ],
        "phone_log": [
            ("19:45", "outgoing", "villager_E", 40),
            ("22:00", "incoming", "villager_E", 25),
        ],
    },
)

TOMAS = SuspectProfile(
    name="tomas",
    display_name="Tomás Reyes",
    occupation="Driver · 12 years with the family",
    emoji="🚗",
    image="ppl_driver.png",
    public_alibi="Running errands in town from 20:00 to 23:30, as logged.",
    private_truth=(
        "I finished the errands at 21:30 and spent the rest of the "
        "evening at my girlfriend's apartment. I'll lie about the "
        "timestamps to keep the overtime pay. I am NOT the killer."
    ),
    dossier={
        "gps": [
            ("20:15", 40.7550, -73.9800),  # town
            ("21:10", 40.7550, -73.9800),
            ("21:45", 40.7200, -74.0000),  # girlfriend's (NOT town, NOT estate)
            ("22:30", 40.7200, -74.0000),
            ("23:15", 40.7550, -73.9800),
        ],
        "phone_log": [
            ("21:30", "outgoing", "girlfriend", 60),
            ("22:50", "outgoing", "dispatch", 120),  # fake timesheet call
        ],
    },
)


ALL_PROFILES: list[SuspectProfile] = [
    ELEANOR,
    MARCO,
    JULIAN,
    DR_CHEN,
    RHEA,
    TOMAS,
]


def profile_by_name(name: str) -> SuspectProfile | None:
    key = name.lower().strip()
    for p in ALL_PROFILES:
        if p.name == key:
            return p
    return None


def format_suspect_summary() -> list[dict[str, Any]]:
    """Public info the Detective can see (no private truths)."""
    return [
        {
            "name": p.name,
            "display_name": p.display_name,
            "occupation": p.occupation,
            "public_alibi": p.public_alibi,
            "data_sources": list(p.dossier.keys()),
            "emoji": p.emoji,
            "image": p.image,
        }
        for p in ALL_PROFILES
    ]
