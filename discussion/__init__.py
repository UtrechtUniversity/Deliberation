from otree.api import *

from settings import (
    GROUP_SIZE as group_size,)

doc = """
3. Form a group
4. Show one (random) statement + group members' opinions and motivations
5. Evaluate each other member (likability, argumentation, trustworthiness, ...)
6. Update opinion
7. Nominate discussion partner(s)
"""

class Constants(BaseConstants):
    name_in_url = 'discussion'
    players_per_group = group_size
    num_rounds = 1

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass

def make_rating_field(label):
    return models.IntegerField(
        min=-10,
        max=10,
        label=label,
        blank=False,
    )

class Player(BasePlayer):
    updated_opinion = models.IntegerField(
        min=-10,
        max=10,
        label="Do you want to update your opinion?",
        blank=False,
    )
    nominated_discussion_partner = models.IntegerField(blank=True)

# create fields for evaluating co-players
for i in range(1, Constants.players_per_group):
    setattr(Player, f"like_{i}", make_rating_field(f"Likability: Group member {i}"))
    setattr(Player, f"strength_{i}", make_rating_field(f"Argument strength: Group member {i}"))
    setattr(Player, f"trust_{i}", make_rating_field(f"Trustworthiness: Group member {i}"))

class GroupFormationPage(WaitPage):
    group_by_arrival_time = True

    @staticmethod #save group id to carry forward to the chatroom
    def after_all_players_arrive(group: Group):
        for p in group.get_players():
            p.participant.past_group_id = group.id


class GroupOverview(Page):

    @staticmethod
    def vars_for_template(player: Player):
        statement = player.participant.vars.get("statement", "")

        rows = [{
            "who": "You",
            "opinion": player.participant.vars.get("opinion", ""),
            "motivation": player.participant.vars.get("motivation", ""),
        }]

        for i, other in enumerate(player.get_others_in_group(), start=1):
            rows.append({
                "who": f"Group member {i}",
                "opinion": other.participant.vars.get("opinion", ""),
                "motivation": other.participant.vars.get("motivation", ""),
            })

        return dict(statement=statement, rows=rows)

class EvaluateGroup(Page):
    form_model = "player"
    form_fields = (
        [f"like_{i}" for i in range(1, Constants.players_per_group)]
        + [f"strength_{i}" for i in range(1, Constants.players_per_group)]
        + [f"trust_{i}" for i in range(1, Constants.players_per_group)]
    )

    @staticmethod
    def vars_for_template(player: Player):
        statement = player.participant.vars.get("statement", "")
        others_rows = []
        for i, other in enumerate(player.get_others_in_group(), start=1):
            others_rows.append({
                "idx": i,
                "who": f"Group member {i}",
                "opinion": other.participant.vars.get("opinion", ""),
                "motivation": other.participant.vars.get("motivation", ""),
            })

        return dict(
            others_rows=others_rows,
            min_rating=-10,
            max_rating=10,
            statement = statement
        )

class UpdateOpinion(Page):
    form_model = "player"
    form_fields = ["updated_opinion"]

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            statement=player.participant.vars.get("statement", ""),
            initial_opinion=player.participant.vars.get("opinion", ""),
        )

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        player.participant.vars["updated_opinion"] = player.updated_opinion

class NominatePartner(Page):
    form_model = "player"
    form_fields = ["nominated_discussion_partner"]

    @staticmethod
    def vars_for_template(player: Player):
        others = list(player.get_others_in_group())
        options = [
            dict(
                value=p.id_in_group,
                label=f"Group member {p.id_in_group}",
                opinion=p.participant.vars.get("opinion", ""),
                motivation=p.participant.vars.get("motivation", ""),
            )
            for p in others
        ]
        return dict(
            statement=player.participant.vars.get("statement", ""),
            options=options,
        )

    @staticmethod
    def error_message(player: Player, values):
        val = values.get("nominated_discussion_partner")
        if val is None:
            return "Please select a group member."

        allowed = {p.id_in_group for p in player.get_others_in_group()}
        if val not in allowed:
            return "Invalid selection."

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        player.participant.vars["nominated_discussion_partner"] = player.nominated_discussion_partner

#page_sequence = [GroupFormationPage, GroupOverview]
page_sequence = [GroupFormationPage, GroupOverview, EvaluateGroup, UpdateOpinion, NominatePartner]