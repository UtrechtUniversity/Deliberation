from otree.api import *
import random
import time
import csv
import re
from pathlib import Path
from settings import GROUP_SIZE as group_size

# dictionary of forbidden words
# source: https://github.com/GamerSafer/word-blocklist/blob/main/full-word-list.csv
BLOCKLIST_FILE = Path(__file__).parent / "full-word-list.csv"

with open(BLOCKLIST_FILE, newline="", encoding="utf-8") as f:
    BANNED_WORDS = {
        row[0].strip().lower()
        for row in csv.reader(f)
        if row
    }

# censoring function
def censor_text(text):
    pattern = re.compile(
        r'\b(' + '|'.join(map(re.escape, BANNED_WORDS)) + r')\b',
        flags=re.IGNORECASE
    )
    return pattern.sub('***', text)

# load vignette

VIGNETTE_DIR = Path(__file__).parent / "vignettes"
def load_vignette(session):
    vignette_name = session.config['vignette']
    path = VIGNETTE_DIR / f"{vignette_name}.txt"

    with open(path, encoding="utf-8") as f:
        return f.read().strip()

doc = """
1. demographics
2. reading task
3. writing task
4. waiting lobby and group formation
5a. group deliberation 
5b. quasi-groups
6. update opinion
"""

class Constants(BaseConstants):
    name_in_url = 'experiment'
    players_per_group = None
    num_rounds = 1
    demographics_timeout_seconds = 60
    reading_timeout_seconds = 180
    writing_timeout_seconds = 300
    chat_time = 360
    max_chars = 500 # maximum number of characters for motivation


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass

# scale from -10 (no discrimination) to 10 (discrimination)
scale_choices = [(i, str(i)) for i in range(-10, 11)]

class Player(BasePlayer):
    # demographics
    gender = models.StringField(
        choices=[
            "Woman",
            "Man",
            "X / other"
        ],
        widget=widgets.RadioSelect,
        label="What is your gender?"
    )

    #interpretation of the scenario
    vignette_problematic = models.IntegerField(
        choices=scale_choices,
        widget=widgets.RadioSelect,
        label="To what extent do you think the hiring decision is problematic?"
    )

    vignette_discriminatory = models.IntegerField(
        choices=scale_choices,
        widget=widgets.RadioSelect,
        label="To what extent do you think discrimination played a role in the hiring decision?"
    )

    vignette_imagine = models.IntegerField(
        choices=scale_choices,
        widget=widgets.RadioSelect,
        label="To what extent do you think the other committee members will believe that discrimination played a role in the hiring decision?"
    )

    #and fields for updated assessment after discussion:
    update_problematic = models.IntegerField(
        choices=scale_choices,
        widget=widgets.RadioSelect,
        label="To what extent do you think the hiring decision is problematic?"
    )

    update_discriminatory = models.IntegerField(
        choices=scale_choices,
        widget=widgets.RadioSelect,
        label="To what extent do you think discrimination played a role in the hiring decision?"
    )

    #field for vote
    formal_review_vote = models.StringField(
        choices=[
            ['proceed', 'Yes, proceed to formal review'],
            ['do_not_proceed', 'No, do not proceed to formal review'],
        ]
    )

    # argumentation in own words
    motivation = models.LongStringField(
        label=f"Please explain why you chose your answers (max {Constants.max_chars} characters)."
    )

    arrived_grouppage = models.BooleanField(initial=False) # keep track of who reached the group formation phase

    #rules of behavior for deliberation phase
    waiver_accepted = models.BooleanField(
        label="I have read and agree to the terms above.",
        initial=False
    )

    # fields for the 'estimation' task (optional)
    #author1_score = models.IntegerField(min=-10, max=10)
    #author2_score = models.IntegerField(min=-10, max=10)
    #author3_score = models.IntegerField(min=-10, max=10)

    #evaluating players:
    #like_1 = models.IntegerField()
    #like_2 = models.IntegerField()
    #like_3 = models.IntegerField()
    #strength_1 = models.IntegerField()
    #strength_2 = models.IntegerField()
    #strength_3 = models.IntegerField()
    #trust_1 = models.IntegerField()
    #trust_2 = models.IntegerField()
    #trust_3 = models.IntegerField()

def timeout_check(player, timeout_happened):
    participant = player.participant
    if timeout_happened and not participant.vars.get('is_dropout', False):
        participant.vars['is_dropout'] = True

def timeout_time(player, timeout_seconds):
    participant = player.participant
    if participant.vars.get('exit', False):
        return 1
    else:
        return timeout_seconds

#########################################################
# PAGES

class Welcome(Page):
    @staticmethod
    def get_timeout_seconds(player):
        return timeout_time(player, 100)


# participants first provide some background/demographic information
class Demographics(Page):
    form_model = 'player'
    form_fields = ['gender']

    @staticmethod
    def get_timeout_seconds(player):
        return timeout_time(player, Constants.demographics_timeout_seconds)

    @staticmethod
    def before_next_page(player, timeout_happened):
        player.participant.vars['gender'] = player.gender #save as participant var (to, potentially, use across apps)
        timeout_check(player, timeout_happened)

#########################################################
# then they proceed to a reading task, where they are presented a scenario and must evaluate this using a score
class Vignette(Page):
    form_model = "player"
    form_fields = ["vignette_problematic", "vignette_discriminatory", "vignette_imagine" ] #multiple dimensions

    @staticmethod
    def vars_for_template(player: Player):
        return dict(vignette=load_vignette(player.session))

    @staticmethod
    def get_timeout_seconds(player):
        return timeout_time(player, Constants.reading_timeout_seconds)

    def before_next_page(player: Player, timeout_happened):
        score = player.vignette_discriminatory
        gender = player.gender
        timeout_check(player, timeout_happened)

        #put players into categories:
        category = None

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
        print(f"Participant {player.participant.id_in_session} category: {category}")

#########################################################
# after this they are asked to give a brief written argumentation
class Motivation(Page):
    form_model = "player"
    form_fields = ["motivation"]

    #everyone gives motivation (also those with non-binary gender and neutral discrimination attribution)
    #@staticmethod
    #def is_displayed(player):
    #    return player.participant.vars.get("category") is not None

    @staticmethod
    def get_timeout_seconds(player):
        return timeout_time(player, Constants.writing_timeout_seconds)

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            max_chars=Constants.max_chars,
            vignette = load_vignette(player.session),
            values = {
                "problematic": player.vignette_problematic,
                "discriminatory": player.vignette_discriminatory,
            }
        )

    @staticmethod
    def error_message(player: Player, values):
        text = (values.get("motivation") or "").strip()

        if not text:
            return "Please provide an explanation."

        if len(text) > Constants.max_chars:
            return (
                f"Please keep your explanation to {Constants.max_chars} characters or fewer."
            )

    def before_next_page(player: Player, timeout_happened):
        timeout_check(player, timeout_happened)

#########################################################
# after completing these tasks, players wait on a waiting page until all N players have arrived,
# and then (sets of) groups are constructed

########### some helper functions ###########
# retrieve the category of a player (M+, M-, W+, W-)
def get_category(p):
    return p.participant.vars.get("category")

# and the raw score [-10; 10]
def get_score(p):
    return p.participant.vars.get("vignette_discriminatory")

# and the sign from the category (+ / -)
def get_sign(p):
    cat = get_category(p)
    if cat is None:
        return None
    return cat[-1]

# compute absolute distance between 2 players' scores
# used for nearest-neighbor matching
def dist(p1, p2):
    v1 = get_score(p1)
    v2 = get_score(p2)
    if v1 is None or v2 is None:
        return float("inf")
    return abs(v1 - v2)

# =========================
# SELECT PLAYERS
# =========================

# randomly select and remove a player from a pool
# for constructing the initial "source" group
def take_random(pool, label=""):
    if not pool:
        return None
    p = pool.pop() #pop() removes and return the last element
    print(f"  🎲 RANDOM {label}: id={p.id_in_subsession}, cat={get_category(p)}, score={get_score(p)}")
    return p

# select the player from a pool whose score is closest to a reference player
def take_closest(pool, ref, label=""):
    if not pool:
        return None
    # compute distance of every candidate to ref. player
    scored = [(p, dist(p, ref)) for p in pool]
    # sort by distance
    scored.sort(key=lambda x: x[1])
    # take the best match (closest player)
    best, best_dist = scored[0]
    # and remove from the pool
    pool.remove(best)

    print(
        f"  🔍 {label}: ref(id={ref.id_in_subsession}, score={get_score(ref)}) "
        f"-> selected(id={best.id_in_subsession}, dist={best_dist})"
    )

    return best

# =========================
# GROUP SCHEMAS
# =========================

# defines the required composition of each group type (A-C)
# Each tuple contains the category (e.g., M+) and sign to match against (e.g., +)
SCHEMA = {
    "A": [("M+", "+"), ("M+", "+"), ("W-", "-"), ("W-", "-")],
    "B": [("M+", "+"), ("M-", "-"), ("W+", "+"), ("W-", "-")],
    "C": [("M+", "+"), ("M-", "-"), ("M+", "+"), ("W-", "-")],
}

# =========================
# GROUP CONSTRUCTION
# =========================
def build_group(schema, refs_by_sign, bins):
    # create temporary working pools (copies of the category-bins)
    pools = {k: bins[k].copy() for k in bins}
    result = []

    # track which ref. player to use per sign
    ref_index = {"+": 0, "-": 0}

    # loop over the slots in the schema
    for cat, sign in schema:

        if ref_index[sign] >= len(refs_by_sign[sign]):
            return None

        # select next ref. player of the required sign
        ref_player = refs_by_sign[sign][ref_index[sign]]
        ref_index[sign] += 1

        #candidate pool for this category:
        pool = pools[cat]

        #pick the closest player in that category, to the reference.
        chosen = take_closest(pool, ref_player, f"{cat} ~ {sign}")

        if chosen is None:
            return None

        result.append(chosen)

    return result

# =========================
# WAIT PAGE: GROUP FORMATION
# =========================
class ShuffleWaitPage(WaitPage):
    template_name = "experiment/GroupFormationPage.html"
    wait_for_all_groups = True

   # hide from None (neutral/non-binary); these return to Prolific
    # @RF: and those without motivation (that is, who timed-out).

    @staticmethod
    def is_displayed(player):
        return player.participant.vars.get("category") is not None

    # keep track of the progress (% of players arrived at the waitpage)
    def vars_for_template(player):
        if not player.arrived_grouppage:
            player.arrived_grouppage = True

        waiting_players = player.subsession.get_players()
        total_needed = player.session.config.get("num_demo_participants")
        total_arrived = sum(p.arrived_grouppage for p in waiting_players)

        percent = (total_arrived / total_needed) * 100 if total_needed > 0 else 0
        percent = min(int(percent), 99)

        return dict(percent=percent,
                    category=player.participant.vars.get("category"))

    @staticmethod
    def after_all_players_arrive(subsession):

        players = subsession.get_players()

        print("\n==============================")
        print("GROUPING STARTED")
        print("==============================")

        real_groups = []

        # =========================================================
        # STEP 1: BINNING
        # =========================================================
        print("\n[STEP 1] BINNING PLAYERS")

        bins = {"M+": [], "M-": [], "W+": [], "W-": []}
        neutrals = []

        for p in players:
            cat = get_category(p)
            print(f"  Player {p.id_in_subsession} → category={cat}, score={get_score(p)}")

            if cat in bins:
                bins[cat].append(p)
            else:
                neutrals.append(p)

        for k, v in bins.items():
            print(f"  BIN {k}: {len(v)} players")
        print(f"  NEUTRALS: {len(neutrals)}")

        for b in bins.values():
            random.shuffle(b)

        # =========================================================
        # STEP 2: NUMBER OF SETS
        # =========================================================
        N = min(
            len(bins["M+"]) // 5,
            len(bins["M-"]) // 2,
            len(bins["W+"]) // 1,
            len(bins["W-"]) // 4
        )

        print(f"\n[STEP 2] NUMBER OF SETS POSSIBLE: {N}")

        group_matrix = []

        # =========================================================
        # STEP 3: BUILD SETS
        # =========================================================
        for i in range(N):

            print(f"\n================ SET {i+1} ================")

            types = ["A", "B", "C"]
            random.shuffle(types)

            print(f"Type order (randomized): {types}")

            order_map = {t: i + 1 for i, t in enumerate(types)}
            set_groups = {}

            source_type = types[0]

            print(f"\n[3A] SOURCE GROUP TYPE: {source_type}")

            if source_type == "A":
                g = [
                    take_random(bins["M+"], "A:M+ (1)"),
                    take_random(bins["M+"], "A:M+ (2)"),
                    take_random(bins["W-"], "A:W- (1)"),
                    take_random(bins["W-"], "A:W- (2)"),
                ]
            elif source_type == "B":
                g = [
                    take_random(bins["M+"], "B:M+"),
                    take_random(bins["M-"], "B:M-"),
                    take_random(bins["W+"], "B:W+"),
                    take_random(bins["W-"], "B:W-"),
                ]
            else:
                g = [
                    take_random(bins["M+"], "C:M+ (1)"),
                    take_random(bins["M-"], "C:M-"),
                    take_random(bins["M+"], "C:M+ (2)"),
                    take_random(bins["W-"], "C:W-"),
                ]

            if None in g:
                print("⚠️ Missing player → breaking set construction")
                break

            print("  Source group members:")
            for p in g:
                print(f"    {p.id_in_subsession} | {get_category(p)} | {get_score(p)}")

            set_groups[source_type] = g

            real_groups.append({
                "type": source_type,
                "members": [p.id_in_subsession for p in g]
            })

            # annotate players
            for p in g:
                p.participant.vars["set_id"] = i + 1
                p.participant.vars["group_type"] = source_type
                p.participant.vars["group_order"] = order_map[source_type]

            # =========================================================
            # STEP 3B: REFERENCES
            # =========================================================
            print("\n[3B] BUILDING REFERENCES")

            refs_by_sign = {"+": [], "-": []}

            for p in g:
                sign = get_sign(p)
                refs_by_sign[sign].append(p)

            for s in refs_by_sign:
                refs_by_sign[s].sort(key=get_score)
                print(f"  sign {s}:")
                for p in refs_by_sign[s]:
                    print(f"    ref {p.id_in_subsession} | score={get_score(p)}")

            # =========================================================
            # STEP 3C: MATCHED GROUPS
            # =========================================================
            for t in types[1:]:

                print(f"\n[3C] MATCHED GROUP TYPE {t}")

                g = build_group(SCHEMA[t], refs_by_sign, bins)

                if g is None:
                    print("  ⚠️ build_group returned None")
                    continue

                print("  Selected members:")
                for p in g:
                    print(f"    {p.id_in_subsession} | {get_category(p)} | {get_score(p)}")

                for p in g:
                    bins[get_category(p)].remove(p)

                set_groups[t] = g

                real_groups.append({
                    "type": t,
                    "members": [p.id_in_subsession for p in g]
                })

                for p in g:
                    p.participant.vars["set_id"] = i + 1
                    p.participant.vars["group_type"] = t
                    p.participant.vars["group_order"] = order_map[t]

            for t in types:
                if t in set_groups:
                    group_matrix.append(set_groups[t])

        # =========================================================
        # STEP 4: LEFTOVERS
        # =========================================================
        print("\n[STEP 4] LEFTOVER GROUPING")

        remaining = []
        for v in bins.values():
            remaining.extend(v)
        remaining.extend(neutrals)

        print(f"Remaining before random grouping: {len(remaining)}")

        random.shuffle(remaining)

        while len(remaining) >= group_size:
            g = remaining[:group_size]
            remaining = remaining[group_size:]

            print("\n  RANDOM GROUP:")
            for p in g:
                print(f"    {p.id_in_subsession}")

            group_matrix.append(g)

            for p in g:
                p.participant.vars["set_id"] = None
                p.participant.vars["group_type"] = "RANDOM"
                p.participant.vars["group_order"] = None

        if remaining and group_matrix:
            print("\n  ADDING FINAL LEFTOVERS:")
            for p in remaining:
                print(f"    {p.id_in_subsession}")

            group_matrix[-1].extend(remaining)

        # =========================================================
        # STEP 5: FINALIZE
        # =========================================================
        print("\n[STEP 5] FINALIZING GROUPS")

        subsession.set_group_matrix(group_matrix)

        for group in subsession.get_groups():
            for p in group.get_players():
                p.participant.group_id = group.id

        subsession.session.vars["real_groups"] = real_groups

        print("\nFINAL REAL GROUPS:")
        for g in real_groups:
            print(g)

        # =========================================================
        # STEP 6A: PSEUDO GROUPS
        # =========================================================
        print("\n==============================")
        print("[STEP 6A] PSEUDO GROUP ASSIGNMENT")
        print("==============================")

        player_map = {p.id_in_subsession: p for p in players}

        leftovers = [
            p for p in players
            if (
                p.participant.vars.get("set_id") is None
                and get_category(p) is not None
            )
        ]

        # If no complete A-B-C set could be created, real_groups is empty.
        # In that case, pseudo participants cannot be matched to a real group,
        # so use three other eligible participants as a fallback source.
        fallback_candidates = [
            p for p in players
            if get_category(p) is not None
        ]

        for ego in leftovers:

            ego_cat = get_category(ego)
            ego_score = get_score(ego)

            print(f"\nEGO {ego.id_in_subsession} | {ego_cat} | {ego_score}")

            if not real_groups:
                candidates = [p for p in fallback_candidates if p != ego]

                if len(candidates) < 3:
                    print(
                        "  → skipped: fewer than 3 other eligible "
                        "participants available"
                    )
                    continue

                # No matched real group exists, so use a neutral random
                # fallback rather than imposing an additional matching rule.
                pseudo_group = random.sample(candidates, 3)

                print("  FALLBACK PSEUDO GROUP (no complete sets):")
                print([p.id_in_subsession for p in pseudo_group])

                ego.participant.vars["pseudo_group"] = [
                    {
                        "id": m.id_in_subsession,
                        "gender": m.gender,
                        "score": get_score(m),
                        "motivation": m.field_maybe_none("motivation"),
                        "category": get_category(m),
                    }
                    for m in pseudo_group
                ]

                ego.participant.vars["pseudo_type"] = "FALLBACK"
                ego.participant.vars["pseudo_distance"] = None
                continue

            valid_types = set()

            for g in real_groups:
                members = [player_map[pid] for pid in g["members"]]
                if any(get_category(m) == ego_cat for m in members):
                    valid_types.add(g["type"])

            print(f"  Valid group types for ego: {valid_types}")

            if not valid_types:
                print("  → skipped (no valid types)")
                continue

            chosen_type = random.choice(list(valid_types))
            print(f"  Chosen type: {chosen_type}")

            candidate_groups = [
                g for g in real_groups if g["type"] == chosen_type
            ]

            print(f"  Candidate groups: {len(candidate_groups)}")

            best_group = None
            best_target = None
            best_dist = float("inf")

            for g in candidate_groups:

                members = [player_map[pid] for pid in g["members"]]
                same_cat = [m for m in members if get_category(m) == ego_cat]

                print(f"    Checking group {g['type']} | same-cat members: {len(same_cat)}")

                if not same_cat:
                    continue

                target = min(same_cat, key=lambda m: abs(get_score(m) - ego_score))
                d = abs(get_score(target) - ego_score)

                print(f"      closest target: {target.id_in_subsession} dist={d}")

                if d < best_dist:
                    best_dist = d
                    best_group = members
                    best_target = target

            if best_group is None:
                print("  → no suitable pseudo-group found")
                continue

            pseudo_group = [m for m in best_group if m != best_target]

            print("  FINAL PSEUDO GROUP:")
            print([p.id_in_subsession for p in pseudo_group])

            ego.participant.vars["pseudo_group"] = [
                {
                    "id": m.id_in_subsession,
                    "gender": m.gender,
                    "score": get_score(m),
                    "motivation": m.field_maybe_none("motivation"),
                    "category": get_category(m),
                }
                for m in pseudo_group
            ]

            ego.participant.vars["pseudo_type"] = chosen_type
            ego.participant.vars["pseudo_distance"] = best_dist

        # =========================================================
        # STEP 6B: AUTHOR SAMPLING
        # =========================================================
        print("\n==============================")
        print("[STEP 6B] AUTHOR SAMPLING")
        print("==============================")

        set_players = [
            p for p in players
            if p.participant.vars.get("set_id") is not None
        ]

        print(f"Eligible authors: {len(set_players)}")

        sampled = random.sample(set_players, min(3, len(set_players)))

        print("Selected authors:")

        for p in sampled:
            print(f"  AUTHOR {p.id_in_subsession} | {get_category(p)} | {get_score(p)}")

        subsession.session.vars["sampled_author_ids"] = [
            p.id_in_subsession for p in sampled
        ]

        print("\nDONE")

#########################################################
# the grouped players (as part of a set) continue to the 'deliberation' task

# define an extramodel to store conversations in
class Message(ExtraModel):
    group = models.Link(Group)
    sender = models.Link(Player)
    raw_text = models.StringField() #uncensored
    text = models.StringField()

def to_dict(msg: Message):
    return dict(sender=msg.sender.id_in_group, text=msg.text)

class Instruction(Page):
    form_model = 'player'
    form_fields = ['waiver_accepted']

    @staticmethod
    def is_displayed(player: Player):
        return player.participant.vars.get("set_id") is not None

    @staticmethod
    def vars_for_template(player):
        return dict(
            timeout_seconds=90,
            vignette = load_vignette(player.session),
            discriminatory = player.vignette_discriminatory
            )


class ChatWaitPage(WaitPage):
    wait_for_all_groups = False

    title_text = "Preparing discussion"
    body_text = (
        "Please wait while the committee members get ready.<br>"
        "The discussion will begin automatically once everyone is ready."
    )

    @staticmethod
    def is_displayed(player: Player):
        return player.participant.vars.get("set_id") is not None


class ChatPage(Page):
    timer_text = 'Time remaining:'

    # only show to people assigned to a set of groups
    @staticmethod
    def is_displayed(player: Player):
        return player.participant.vars.get("set_id") is not None

    @staticmethod
    def get_timeout_seconds(player):
        return None  # manual-end

    @staticmethod
    def js_vars(player: Player):
        return dict(my_id=player.id_in_group,
                    time_limit=Constants.chat_time,
                    start_time=player.participant.vars["chat_start_time"]
                    )

    @staticmethod
    def vars_for_template(player: Player):

        if "chat_start_time" not in player.participant.vars:
            player.participant.vars["chat_start_time"] = time.time()

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
            raw_text = data['text']
            censored_text = censor_text(raw_text)

            msg = Message.create(
                group=group,
                sender=player,
                raw_text=raw_text,
                text=censored_text,
            )

            msg_dict = to_dict(msg)
            msg_dict["sender_gender"] = player.gender
            return {0: [msg_dict]}

        return {my_id: [to_dict(m) | {"sender_gender": m.sender.gender} for m in Message.filter(group=group)]}

# function to export chat data
def custom_export(players):
    yield [
        'session_code',
        'participant_code',
        'group_id',
        'sender_id_in_group',
        'message_text',
    ]

    # avoid exporting the same message multiple times
    seen_groups = set()

    for player in players:
        group = player.group
        if group.id in seen_groups:
            continue
        seen_groups.add(group.id)

        messages = Message.filter(group=group)
        for msg in messages:
            yield [
                player.session.code,
                msg.sender.participant.code,
                msg.group.id,
                msg.sender.id_in_group,
                msg.raw_text,
            ]

#########################################################

# ungrouped players are placed on a 'pseudo-group':
# 1. select an (applicable) group type for ego;
# 2. find the group of that type with the nearest neighbor (within the same category as ego)
# 3. remove this players and keep the other 3.

class GroupPage(Page):
    @staticmethod
    def is_displayed(player):
        participant = player.participant
        return (
                participant.vars.get("set_id") is None
                and participant.vars.get("category") is not None
        )

    @staticmethod
    def vars_for_template(player):
        pseudo_group = player.participant.vars.get("pseudo_group", [])
        return dict(
            pseudo_group=pseudo_group,
            pseudo_type=player.participant.vars.get("pseudo_type"),
            pseudo_distance=player.participant.vars.get("pseudo_distance"),
        )


# (OPTIONAL EXTENSION:) ungrouped players continue with the 'estimation' task
class Estimation(Page):
    form_model = "player"
    form_fields = ["author1_score", "author2_score", "author3_score"]

    @staticmethod
    def is_displayed(player: Player):
        return player.participant.vars.get("set_id") is None

    @staticmethod
    def vars_for_template(player: Player):
        ids = player.session.vars.get('sampled_author_ids', [])

        players = player.subsession.get_players()
        selected = [p for p in players if p.id_in_subsession in ids]

        authors = []
        for p in selected:
            authors.append({
                "id": f"P{p.participant.id_in_session}",
                "gender": p.gender,
                "motivation": p.motivation,
                "problematic": p.vignette_problematic,
                "discriminatory": p.vignette_discriminatory,
            })

        return dict(authors=authors,
                    vignette = load_vignette(player.session))


class UpdateOpinion(Page):
    form_model = "player"
    form_fields = ["update_discriminatory", "update_problematic"]

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            vignette=load_vignette(player.session),
            values={
                "problematic": player.vignette_problematic,
                "discriminatory": player.vignette_discriminatory,
            },
            condition="deliberation" if  player.participant.vars.get("set_id") is not None else "pseudo"
        )

    @staticmethod
    def is_displayed(player):
        return player.participant.vars.get("category") is not None


class FinalVote(Page):
    form_model = 'player'
    form_fields = ['formal_review_vote']

    @staticmethod
    def is_displayed(player):
        return player.participant.vars.get("category") is not None


page_sequence = [Welcome,
                 Demographics, Vignette, Motivation,
                 ShuffleWaitPage,
                 Instruction,
                 ChatWaitPage,
                 ChatPage, GroupPage,
                 UpdateOpinion,
                 FinalVote,
                 #EvaluateGroup
                 ]

page_sequence = [Welcome,
                 Demographics, Vignette, Motivation,
                 ShuffleWaitPage,
                 Instruction,
                 ChatWaitPage,
                 ChatPage, GroupPage,
                 UpdateOpinion,
                 FinalVote,
                 #EvaluateGroup
                 ]

