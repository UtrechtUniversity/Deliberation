from otree.api import *
import random

from settings import GROUP_SIZE as group_size

class Constants(BaseConstants):
    name_in_url = 'GroupFormation'
    players_per_group = group_size
    num_rounds = 1


class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass


class Player(BasePlayer):
    arrived_grouppage = models.BooleanField(initial=False) # keep track of who reached the group formation phase

# =========================
# HELPER FUNCTIONS
# =========================

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

    # create temporary working pools (copies of bins)
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
    template_name = "group_formation/GroupFormationPage.html"
    wait_for_all_groups = True

    # keep track of the progress (% of players arrived at the waitpage)
    def vars_for_template(player):
        if not player.arrived_grouppage:
            player.arrived_grouppage = True

        waiting_players = player.subsession.get_players()
        total_needed = player.session.config.get("num_demo_participants")
        total_arrived = sum(p.arrived_grouppage for p in waiting_players)

        if total_needed > 0:
            percent = (total_arrived / total_needed) * 100
        else:
            percent = 0

        percent = min(int(percent), 99)

        return dict(percent=percent)

    @staticmethod
    def after_all_players_arrive(subsession):

        players = subsession.get_players()

        print("\n==============================")
        print("GROUPING STARTED")
        print("==============================")

        #STEP 1: players into bins
        bins = {"M+": [], "M-": [], "W+": [], "W-": []}
        neutrals = []

        for p in players:
            cat = get_category(p)
            if cat in bins:
                bins[cat].append(p)
            else:
                # players without category (X or neutral) go to fallback pool
                neutrals.append(p)

        # shuffle each bin for randomness
        for b in bins.values():
            random.shuffle(b)

        print("\nBIN COUNTS:")
        for k, v in bins.items():
            print(k, len(v))
        print("other", len(neutrals))

        #STEP 2: how many sets can we make?
        N = min(
            len(bins["M+"]) // 5,
            len(bins["M-"]) // 2,
            len(bins["W+"]) // 1,
            len(bins["W-"]) // 4
        )

        print("\nNumber of sets:", N)

        group_matrix = []

        #STEP 3: build each set
        for i in range(N):

            print(f"\n========= SET {i + 1} =========")

            types = ["A", "B", "C"]
            # randomize order of group types within set
            random.shuffle(types)
            print("Type order:", types)
            order_map = {t: i + 1 for i, t in enumerate(types)}

            set_groups = {}

            #STEP 3A: first group is formed by drawing randomly from the (shuffled) bins
            source_type = types[0]

            print(f"\n➡️ SOURCE TYPE: {source_type}")

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
            else:  # C
                g = [
                    take_random(bins["M+"], "C:M+ (1)"),
                    take_random(bins["M-"], "C:M-"),
                    take_random(bins["M+"], "C:M+ (2)"),
                    take_random(bins["W-"], "C:W-"),
                ]

            if None in g:
                break

            set_groups[source_type] = g

            for p in g:
                p.participant.vars["set_id"] = i + 1
                p.participant.vars["group_type"] = source_type
                p.participant.vars["group_order"] = order_map[source_type]

            #STEP 3B: build references
            # split source group into signed-groups ("+" and "-" players).
            refs_by_sign = {"+": [], "-": []}

            for p in g:
                sign = get_sign(p)
                if sign in refs_by_sign:
                    refs_by_sign[sign].append(p)

            #sort references by score
            for s in refs_by_sign:
                refs_by_sign[s].sort(key=get_score)

            print("\nREFS BY SIGN:")
            for s in refs_by_sign:
                print(s, [(p.id_in_subsession, get_score(p)) for p in refs_by_sign[s]])

            #STEP 3C: matching groups
            #build remaining groups using nearest-neighbor matching
            for t in types[1:]:

                print(f"\n➡️ MATCHED GROUP {t}")

                g = build_group(SCHEMA[t], refs_by_sign, bins)

                if g is None:
                    continue

                # remove chosen players from bins
                for p in g:
                    if p in bins[get_category(p)]:
                        bins[get_category(p)].remove(p)

                set_groups[t] = g

                for p in g:
                    p.participant.vars["set_id"] = i + 1
                    p.participant.vars["group_type"] = t
                    p.participant.vars["group_order"] = order_map[t]

                print(
                    f"{t} matched:",
                    [(p.id_in_subsession, get_category(p), get_score(p)) for p in g],
                )

            # store the groups
            for t in types:
                if t in set_groups:
                    group_matrix.append(set_groups[t])

        #STEP 4: handle the remaining/ungrouped players
        remaining = []
        for v in bins.values():
            remaining.extend(v)
        remaining.extend(neutrals)

        random.shuffle(remaining)

        print("\nRemaining:", len(remaining))

        # form random groups from leftovers
        while len(remaining) >= group_size:
            g = remaining[:group_size]
            remaining = remaining[group_size:]
            group_matrix.append(g)

            for p in g:
                p.participant.vars["set_id"] = None
                p.participant.vars["group_type"] = "RANDOM"
                p.participant.vars["group_order"] = None

        # add any leftover players to the last group
        if remaining and group_matrix:
            group_matrix[-1].extend(remaining)

            for p in remaining:
                p.participant.vars["set_id"] = None
                p.participant.vars["group_type"] = "RANDOM"
                p.participant.vars["group_order"] = None

        #STEP 5: Finalize group formation
        subsession.set_group_matrix(group_matrix)
        print("\nGROUPING COMPLETE\n")

        for group in subsession.get_groups():
            for p in group.get_players():
                p.participant.group_id = group.id

class MyPage(Page):
    pass

page_sequence = [MyPage, ShuffleWaitPage]