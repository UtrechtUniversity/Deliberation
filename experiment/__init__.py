from otree.api import *
import random

from settings import GROUP_SIZE as group_size

doc = """
1. demographics
2. reading task
3. writing task
4. waiting lobby and group formation
5a. group deliberation 
5b. quasi-groups
"""

class Constants(BaseConstants):
    name_in_url = 'experiment'
    players_per_group = None
    num_rounds = 1
    demographics_timeout_seconds = 10
    reading_timeout_seconds = 20
    writing_timeout_seconds = 15
    chat_time = 300
    max_chars = 500 # maximum number of characters for motivation


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass

# vignette text (reading task)
vignette_text = \
    "The company where you work is hiring a new department manager. "\
    "Two internal candidates apply: Mary and Paul. You know these candidates well. "\
    "Both have worked at the company for several years and have similar qualifications and performance evaluations. "\
    "In the end, Paul is selected for the position instead of Mary."

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
        label="To what extent do you think this situation is problematic?"
    )

    vignette_discriminatory = models.IntegerField(
        choices=scale_choices,
        widget=widgets.RadioSelect,
        label="To what extent do you think this situation is discriminatory?"
    )

    vignette_imagine = models.IntegerField(
        choices=scale_choices,
        widget=widgets.RadioSelect,
        label="To what extent can you imagine others would perceive this situation as discriminatory?"
    )

    # argumentation in own words
    motivation = models.LongStringField(
        label=f"Please explain why you chose your answers (max {Constants.max_chars} characters)."
    )

    arrived_grouppage = models.BooleanField(initial=False) # keep track of who reached the group formation phase

    # fields for the 'estimation' task
    author1_score = models.IntegerField(min=-10, max=10)
    author2_score = models.IntegerField(min=-10, max=10)
    author3_score = models.IntegerField(min=-10, max=10)

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
        return dict(vignette=vignette_text)

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

    @staticmethod
    def get_timeout_seconds(player):
        return timeout_time(player, Constants.writing_timeout_seconds)

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            max_chars=Constants.max_chars,
            vignette = vignette_text,
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

#@RF: can i here make sure that those 'neutrals' enter the waitpage and leave it immediately
# (does that stop further groups from forming)

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

    # keep track of the progress (% of players arrived at the waitpage)
    def vars_for_template(player):
        if not player.arrived_grouppage:
            player.arrived_grouppage = True

        waiting_players = player.subsession.get_players()
        total_needed = player.session.config.get("num_demo_participants")
        total_arrived = sum(p.arrived_grouppage for p in waiting_players)

        percent = (total_arrived / total_needed) * 100 if total_needed > 0 else 0
        percent = min(int(percent), 99)

        return dict(percent=percent)

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
            if p.participant.vars.get("set_id") is None
        ]

        for ego in leftovers:

            ego_cat = get_category(ego)
            ego_score = get_score(ego)

            print(f"\nEGO {ego.id_in_subsession} | {ego_cat} | {ego_score}")

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
                    "motivation": m.motivation,
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
    text = models.StringField()

def to_dict(msg: Message):
    return dict(sender=msg.sender.id_in_group, text=msg.text)

class ChatPage(Page):
    timer_text = 'Time remaining:'

    # only show to people assigned to a set of groups
    @staticmethod
    def is_displayed(player: Player):
        return player.participant.vars.get("set_id") is not None

    @staticmethod
    def get_timeout_seconds(player):
        return timeout_time(player, Constants.chat_time)

    @staticmethod
    def js_vars(player: Player):
        return dict(my_id=player.id_in_group)

    @staticmethod
    def live_method(player: Player, data):
        my_id = player.id_in_group
        group = player.group

        if 'text' in data:
            text = data['text']
            msg = Message.create(group=group, sender=player, text=text)
            return {0: [to_dict(msg)]}
        return {my_id: [to_dict(msg) for msg in Message.filter(group=group)]}

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
                msg.text,
            ]

#########################################################

# ungrouped players are placed on a 'pseudo-group':
# 1. select an (applicable) group type for ego;
# 2. find the group of that type with the nearest neighbor (within the same category as ego)
# 3. remove this players and keep the other 3.

class GroupPage(Page):


    @staticmethod
    def is_displayed(player):
        return player.participant.vars.get("set_id") is None

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
                    vignette = vignette_text)


page_sequence = [Demographics, Vignette, Motivation,
                 ShuffleWaitPage,
                 ChatPage, GroupPage,

                 Estimation,

                 ]

