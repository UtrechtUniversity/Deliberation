from otree.api import *
import random
import time
import csv
import re
from pathlib import Path
from settings import GROUP_SIZE as group_size


# =========================================================
# FORBIDDEN WORDS
# =========================================================

# Source:
# https://github.com/GamerSafer/word-blocklist/blob/main/full-word-list.csv

BLOCKLIST_FILE = Path(__file__).parent / "full-word-list.csv"

with open(BLOCKLIST_FILE, newline="", encoding="utf-8") as f:
    BANNED_WORDS = {
        row[0].strip().lower()
        for row in csv.reader(f)
        if row and row[0].strip()
    }


def censor_text(text):
    if not BANNED_WORDS:
        return text

    pattern = re.compile(
        r'\b(' + '|'.join(map(re.escape, BANNED_WORDS)) + r')\b',
        flags=re.IGNORECASE,
    )
    return pattern.sub('***', text)


# =========================================================
# VIGNETTE
# =========================================================

VIGNETTE_DIR = Path(__file__).parent / "vignettes"


def load_vignette(session):
    vignette_name = session.config['vignette']
    path = VIGNETTE_DIR / f"{vignette_name}.txt"

    with open(path, encoding="utf-8") as f:
        return f.read().strip()


doc = """
1. Demographics
2. Reading task
3. Writing task
4. Waiting lobby and group formation
   - Matched A-B-C sets
   - Opinion-homogeneous groups for remaining eligible participants
5. Group deliberation
6. Update opinion
7. Final vote
"""


# =========================================================
# MODELS
# =========================================================

class Constants(BaseConstants):
    name_in_url = 'experiment'
    players_per_group = None
    num_rounds = 1

    demographics_timeout_seconds = 60
    reading_timeout_seconds = 180
    writing_timeout_seconds = 300

    chat_time = 360
    max_chars = 750


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


scale_choices = [(i, str(i)) for i in range(-10, 11)]


class Player(BasePlayer):

    # Demographics
    gender = models.StringField(
        choices=[
            "Woman",
            "Man",
            "X / other",
        ],
        widget=widgets.RadioSelect,
        label="What is your gender?",
    )

    # Initial interpretation of the scenario
    vignette_problematic = models.IntegerField(
        choices=scale_choices,
        widget=widgets.RadioSelect,
        label=(
            "To what extent do you think the hiring decision "
            "is problematic?"
        ),
    )

    vignette_discriminatory = models.IntegerField(
        choices=scale_choices,
        widget=widgets.RadioSelect,
        label=(
            "To what extent do you think discrimination played "
            "a role in the hiring decision?"
        ),
    )

    vignette_imagine = models.IntegerField(
        choices=scale_choices,
        widget=widgets.RadioSelect,
        label=(
            "To what extent do you think the other committee "
            "members will believe that discrimination played "
            "a role in the hiring decision?"
        ),
    )

    # Updated assessment after discussion
    update_problematic = models.IntegerField(
        choices=scale_choices,
        widget=widgets.RadioSelect,
        label=(
            "To what extent do you think the hiring decision "
            "is problematic?"
        ),
    )

    update_discriminatory = models.IntegerField(
        choices=scale_choices,
        widget=widgets.RadioSelect,
        label=(
            "To what extent do you think discrimination played "
            "a role in the hiring decision?"
        ),
    )

    # Final vote
    formal_review_vote = models.StringField(
        choices=[
            ['proceed', 'Yes, proceed to formal review'],
            ['do_not_proceed', 'No, do not proceed to formal review'],
        ],
    )

    # Written argumentation
    motivation = models.LongStringField(
        label=(
            "Please explain why you chose your answers "
            f"(max {Constants.max_chars} characters)."
        ),
    )

    # Track arrival at the group formation page
    arrived_grouppage = models.BooleanField(initial=False)

    # Rules of behavior for deliberation
    waiver_accepted = models.BooleanField(
        label="I have read and agree to the terms above.",
        initial=False,
    )


# =========================================================
# TIMEOUT HELPERS
# =========================================================

def timeout_check(player, timeout_happened):
    participant = player.participant

    if timeout_happened and not participant.vars.get('is_dropout', False):
        participant.vars['is_dropout'] = True


def timeout_time(player, timeout_seconds):
    if player.participant.vars.get('exit', False):
        return 1

    return timeout_seconds


# =========================================================
# INITIAL PAGES
# =========================================================

class Welcome(Page):

    @staticmethod
    def get_timeout_seconds(player):
        return timeout_time(player, 100)


class Demographics(Page):
    form_model = 'player'
    form_fields = ['gender']

    @staticmethod
    def get_timeout_seconds(player):
        return timeout_time(
            player,
            Constants.demographics_timeout_seconds,
        )

    @staticmethod
    def before_next_page(player, timeout_happened):
        player.participant.vars['gender'] = player.field_maybe_none(
            "gender"
        )
        timeout_check(player, timeout_happened)


class Vignette(Page):
    form_model = 'player'
    form_fields = [
        'vignette_problematic',
        'vignette_discriminatory',
        'vignette_imagine',
    ]

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            vignette=load_vignette(player.session),
        )

    @staticmethod
    def get_timeout_seconds(player):
        return timeout_time(
            player,
            Constants.reading_timeout_seconds,
        )

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        score = player.field_maybe_none("vignette_discriminatory")
        gender = player.field_maybe_none("gender")

        timeout_check(player, timeout_happened)

        category = None

        if score is not None:
            if gender == "Man":
                if score < -2:
                    category = "M+"
                elif score > 2:
                    category = "M-"

            elif gender == "Woman":
                if score < -2:
                    category = "W+"
                elif score > 2:
                    category = "W-"

        player.participant.vars["category"] = category
        player.participant.vars["vignette_discriminatory"] = score

        print(
            f"Participant {player.participant.id_in_session} "
            f"category: {category}"
        )


class Motivation(Page):
    form_model = 'player'
    form_fields = ['motivation']

    # Everyone provides a motivation, including participants
    # with a neutral assessment or X / other gender.

    @staticmethod
    def get_timeout_seconds(player):
        return timeout_time(
            player,
            Constants.writing_timeout_seconds,
        )

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            max_chars=Constants.max_chars,
            vignette=load_vignette(player.session),
            values={
                "problematic": player.field_maybe_none(
                    "vignette_problematic"
                ),
                "discriminatory": player.field_maybe_none(
                    "vignette_discriminatory"
                ),
            },
        )

    @staticmethod
    def error_message(player: Player, values):
        text = (values.get("motivation") or "").strip()

        if not text:
            return "Please provide an explanation."

        if len(text) > Constants.max_chars:
            return (
                "Please keep your explanation to "
                f"{Constants.max_chars} characters or fewer."
            )

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        timeout_check(player, timeout_happened)


# =========================================================
# GROUPING HELPERS
# =========================================================

def get_category(player):
    return player.participant.vars.get("category")


def get_score(player):
    return player.participant.vars.get("vignette_discriminatory")


def get_sign(player):
    category = get_category(player)

    if category is None:
        return None

    return category[-1]


def dist(player1, player2):
    score1 = get_score(player1)
    score2 = get_score(player2)

    if score1 is None or score2 is None:
        return float("inf")

    return abs(score1 - score2)


def in_discussion(player):
    return player.participant.vars.get("in_discussion", False)


# =========================================================
# PLAYER SELECTION
# =========================================================

def take_random(pool, label=""):
    if not pool:
        return None

    # Pools are shuffled before selection.
    player = pool.pop()

    print(
        f"  RANDOM {label}: "
        f"id={player.id_in_subsession}, "
        f"cat={get_category(player)}, "
        f"score={get_score(player)}"
    )

    return player


def take_closest(pool, reference, label=""):
    if not pool:
        return None

    scored = [(player, dist(player, reference)) for player in pool]
    scored.sort(key=lambda item: item[1])

    best, best_distance = scored[0]
    pool.remove(best)

    print(
        f"  MATCH {label}: "
        f"ref(id={reference.id_in_subsession}, "
        f"score={get_score(reference)}) "
        f"-> selected(id={best.id_in_subsession}, "
        f"distance={best_distance})"
    )

    return best


# =========================================================
# MATCHED GROUP SCHEMAS
# =========================================================

SCHEMA = {
    "A": [
        ("M+", "+"),
        ("M+", "+"),
        ("W-", "-"),
        ("W-", "-"),
    ],
    "B": [
        ("M+", "+"),
        ("M-", "-"),
        ("W+", "+"),
        ("W-", "-"),
    ],
    "C": [
        ("M+", "+"),
        ("M-", "-"),
        ("M+", "+"),
        ("W-", "-"),
    ],
}


def build_group(schema, refs_by_sign, bins):
    pools = {
        category: pool.copy()
        for category, pool in bins.items()
    }

    result = []
    ref_index = {"+": 0, "-": 0}

    for category, sign in schema:
        if ref_index[sign] >= len(refs_by_sign[sign]):
            return None

        reference = refs_by_sign[sign][ref_index[sign]]
        ref_index[sign] += 1

        chosen = take_closest(
            pools[category],
            reference,
            f"{category} ~ {sign}",
        )

        if chosen is None:
            return None

        result.append(chosen)

    return result


# =========================================================
# WAIT PAGE: GROUP FORMATION
# =========================================================

class ShuffleWaitPage(WaitPage):
    template_name = "experiment/GroupFormationPage.html"
    wait_for_all_groups = True

    @staticmethod
    def is_displayed(player):
        return get_category(player) is not None

    @staticmethod
    def vars_for_template(player):
        if not player.arrived_grouppage:
            player.arrived_grouppage = True

        players = player.subsession.get_players()

        total_needed = (
            player.session.config.get("num_demo_participants")
            or len(players)
        )

        total_arrived = sum(
            p.arrived_grouppage
            for p in players
        )

        percent = (
            (total_arrived / total_needed) * 100
            if total_needed > 0
            else 0
        )

        return dict(
            percent=min(int(percent), 99),
            category=get_category(player),
        )

    @staticmethod
    def after_all_players_arrive(subsession):

        if group_size != 4:
            raise ValueError(
                "GROUP_SIZE must be 4 for the A-B-C schemas "
                "and homogeneous discussion groups."
            )

        players = subsession.get_players()
        group_matrix = []
        real_groups = []

        print("\n==============================")
        print("GROUPING STARTED")
        print("==============================")

        # Initialize assignment information.
        for player in players:
            player.participant.vars["set_id"] = None
            player.participant.vars["group_type"] = "UNGROUPED"
            player.participant.vars["group_order"] = None
            player.participant.vars["in_discussion"] = False

        # =================================================
        # STEP 1: BINNING
        # =================================================

        bins = {
            "M+": [],
            "M-": [],
            "W+": [],
            "W-": [],
        }

        for player in players:
            category = get_category(player)

            print(
                f"  Player {player.id_in_subsession}: "
                f"category={category}, score={get_score(player)}"
            )

            if category in bins:
                bins[category].append(player)

        for category, pool in bins.items():
            random.shuffle(pool)
            print(f"  BIN {category}: {len(pool)} players")

        # =================================================
        # STEP 2: NUMBER OF COMPLETE A-B-C SETS
        # =================================================

        # Each set requires:
        # 5 M+, 2 M-, 1 W+, and 4 W-.
        number_of_sets = min(
            len(bins["M+"]) // 5,
            len(bins["M-"]) // 2,
            len(bins["W+"]),
            len(bins["W-"]) // 4,
        )

        print(
            "\nNUMBER OF COMPLETE SETS POSSIBLE: "
            f"{number_of_sets}"
        )

        # =================================================
        # STEP 3: BUILD MATCHED A-B-C SETS
        # =================================================

        for set_index in range(number_of_sets):
            set_id = set_index + 1

            print(f"\n================ SET {set_id} ================")

            types = ["A", "B", "C"]
            random.shuffle(types)

            order_map = {
                group_type: position + 1
                for position, group_type in enumerate(types)
            }

            source_type = types[0]
            set_groups = {}

            print(f"Type order: {types}")
            print(f"Source group type: {source_type}")

            # Randomly select the source group.
            source_group = [
                take_random(
                    bins[category],
                    f"{source_type}:{category}",
                )
                for category, sign in SCHEMA[source_type]
            ]

            if any(player is None for player in source_group):
                raise RuntimeError(
                    "Insufficient players while building "
                    f"the source group for set {set_id}."
                )

            set_groups[source_type] = source_group

            # Build opinion references from the source group.
            refs_by_sign = {
                "+": [],
                "-": [],
            }

            for player in source_group:
                refs_by_sign[get_sign(player)].append(player)

            for references in refs_by_sign.values():
                references.sort(key=get_score)

            # Match the remaining two group types to the source.
            for group_type in types[1:]:
                matched_group = build_group(
                    SCHEMA[group_type],
                    refs_by_sign,
                    bins,
                )

                if matched_group is None:
                    raise RuntimeError(
                        f"Could not build group {group_type} "
                        f"for set {set_id}."
                    )

                for player in matched_group:
                    bins[get_category(player)].remove(player)

                set_groups[group_type] = matched_group

            # Record the completed set.
            for group_type in types:
                members = set_groups[group_type]
                group_matrix.append(members)

                real_groups.append({
                    "type": group_type,
                    "members": [
                        player.id_in_subsession
                        for player in members
                    ],
                })

                for player in members:
                    player.participant.vars["set_id"] = set_id
                    player.participant.vars["group_type"] = group_type
                    player.participant.vars["group_order"] = (
                        order_map[group_type]
                    )
                    player.participant.vars["in_discussion"] = True

        # =================================================
        # STEP 4: OPINION-HOMOGENEOUS GROUPS
        # =================================================

        # Combine genders within each remaining opinion pool.
        opinion_pools = {
            "+": bins["M+"] + bins["W+"],
            "-": bins["M-"] + bins["W-"],
        }

        for sign, pool in opinion_pools.items():
            random.shuffle(pool)

            while len(pool) >= group_size:
                members = pool[:group_size]
                del pool[:group_size]

                group_type = (
                    "HOMOG_PLUS"
                    if sign == "+"
                    else "HOMOG_MINUS"
                )

                group_matrix.append(members)

                real_groups.append({
                    "type": group_type,
                    "members": [
                        player.id_in_subsession
                        for player in members
                    ],
                })

                for player in members:
                    # Homogeneous groups do not belong
                    # to a matched A-B-C set.
                    player.participant.vars["set_id"] = None
                    player.participant.vars["group_type"] = group_type
                    player.participant.vars["group_order"] = None
                    player.participant.vars["in_discussion"] = True

                print(
                    f"  {group_type}: "
                    f"{[p.id_in_subsession for p in members]}"
                )

            print(
                f"  Ungrouped remainder for sign {sign}: "
                f"{[p.id_in_subsession for p in pool]}"
            )

        # =================================================
        # STEP 5: UNGROUPED PARTICIPANTS
        # =================================================

        assigned_ids = {
            player.id_in_subsession
            for members in group_matrix
            for player in members
        }

        # Neutrals and incomplete-group remainders receive
        # singleton bookkeeping groups. They skip discussion
        # and the follow-up questions.
        for player in players:
            if player.id_in_subsession not in assigned_ids:
                group_matrix.append([player])

        # =================================================
        # STEP 6: FINALIZE
        # =================================================

        subsession.set_group_matrix(group_matrix)

        for group in subsession.get_groups():
            for player in group.get_players():
                player.participant.group_id = group.id

        subsession.session.vars["real_groups"] = real_groups

        print("\nFINAL DISCUSSION GROUPS:")
        for group_info in real_groups:
            print(group_info)

        print("\nDONE")


# =========================================================
# CHAT MESSAGE MODEL
# =========================================================

class Message(ExtraModel):
    group = models.Link(Group)
    sender = models.Link(Player)

    raw_text = models.StringField()
    text = models.StringField()

    timestamp = models.FloatField()
    elapsed_seconds = models.FloatField()


def to_dict(message: Message):
    return dict(
        sender=message.sender.id_in_group,
        text=message.text,
    )


# =========================================================
# DISCUSSION PAGES
# =========================================================

class Instruction(Page):
    form_model = 'player'
    form_fields = ['waiver_accepted']

    @staticmethod
    def is_displayed(player: Player):
        return in_discussion(player)

    @staticmethod
    def vars_for_template(player):
        return dict(
            timeout_seconds=90,
            vignette=load_vignette(player.session),
            discriminatory=player.vignette_discriminatory,
        )


class ChatWaitPage(WaitPage):
    wait_for_all_groups = False

    title_text = "Preparing discussion"

    body_text = (
        "Please wait while the committee members get ready.<br>"
        "The discussion will begin automatically once everyone "
        "is ready."
    )

    @staticmethod
    def is_displayed(player: Player):
        return in_discussion(player)

    @staticmethod
    def after_all_players_arrive(group: Group):
        players = group.get_players()
        start_time = time.time()

        entry_order = [p.id_in_group for p in players]
        random.shuffle(entry_order)

        for player in players:
            player.participant.vars["chat_start_time"] = start_time
            player.participant.vars["chat_entry_order"] = entry_order

class ChatPage(Page):
    timer_text = 'Time remaining:'

    @staticmethod
    def is_displayed(player: Player):
        return in_discussion(player)

    @staticmethod
    def get_timeout_seconds(player):
        return None  # Manual end through the existing template.

    @staticmethod
    def js_vars(player: Player):
        entry_order = player.participant.vars["chat_entry_order"]

        genders = {
            p.id_in_group: p.gender.lower()
            for p in player.group.get_players()
        }

        return dict(
            my_id=player.id_in_group,
            time_limit=Constants.chat_time,
            start_time=player.participant.vars["chat_start_time"],
            entry_messages=[
                f"Player {player_id} ({genders[player_id]}) "
                "has entered the chat."
                for player_id in entry_order
                if player_id != player.id_in_group
            ],
        )

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            vignette=load_vignette(player.session),
            problematic=player.vignette_problematic,
            discriminatory=player.vignette_discriminatory,
            start_time=player.participant.vars["chat_start_time"],
            my_id=player.id_in_group,
        )

    @staticmethod
    def live_method(player: Player, data):
        my_id = player.id_in_group
        group = player.group

        if 'text' in data:
            timestamp = time.time()
            start_time = player.participant.vars["chat_start_time"]

            raw_text = data['text']
            censored_text = censor_text(raw_text)

            message = Message.create(
                group=group,
                sender=player,
                raw_text=raw_text,
                text=censored_text,
                timestamp=timestamp,
                elapsed_seconds=timestamp - start_time,
            )

            message_dict = to_dict(message)
            message_dict["sender_gender"] = player.gender

            return {0: [message_dict]}

        return {
            my_id: [
                to_dict(message) | {
                    "sender_gender": message.sender.gender
                }
                for message in Message.filter(group=group)
            ]
        }


# =========================================================
# CHAT EXPORT
# =========================================================

def custom_export(players):
    yield [
        'session_code',
        'participant_code',
        'group_id',
        'sender_id_in_group',
        'message_text',
        'timestamp',
        'elapsed_seconds',
    ]

    seen_groups = set()

    for player in players:
        group = player.group

        if group.id in seen_groups:
            continue

        seen_groups.add(group.id)

        for message in Message.filter(group=group):
            yield [
                player.session.code,
                message.sender.participant.code,
                message.group.id,
                message.sender.id_in_group,
                message.raw_text,
                message.timestamp,
                message.elapsed_seconds,
            ]


# =========================================================
# FOLLOW-UP PAGES
# =========================================================

class UpdateOpinion(Page):
    form_model = 'player'
    form_fields = [
        'update_discriminatory',
        'update_problematic',
    ]

    @staticmethod
    def is_displayed(player: Player):
        return in_discussion(player)

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            vignette=load_vignette(player.session),
            values={
                "problematic": player.vignette_problematic,
                "discriminatory": player.vignette_discriminatory,
            },
            condition="deliberation",
        )


class FinalVote(Page):
    form_model = 'player'
    form_fields = ['formal_review_vote']

    @staticmethod
    def is_displayed(player: Player):
        return in_discussion(player)


# =========================================================
# PAGE SEQUENCE
# =========================================================

page_sequence = [
    #Welcome,
    Demographics,
    Vignette,
    #Motivation,
    ShuffleWaitPage,
    Instruction,
    ChatWaitPage,
    ChatPage,
    UpdateOpinion,
    FinalVote,
]