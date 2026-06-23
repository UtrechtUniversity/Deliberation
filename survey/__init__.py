from otree.api import *


doc = """
Ethical response survey (pilot)
"""


class C(BaseConstants):
    NAME_IN_URL = 'survey'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    ethical_inclusion = models.IntegerField(
        choices=[
            [1, "Yes"],
            [2, "I have no preferences"],
            [3, "No"],
        ],
        widget=widgets.RadioSelect
    )

    ethical_approval = models.IntegerField(
        choices=[
            [1, "Yes"],
            [2, "Yes, but with caution"],
            [3, "I’m not sure"],
            [4, "No"],
        ],
        widget=widgets.RadioSelect
    )

    # open-ended explanations
    ethical_inclusion_expl = models.LongStringField(blank=True)
    ethical_approval_expl = models.LongStringField(blank=True)

    comments = models.LongStringField(blank=True)

# PAGES
class Survey(Page):
    form_model = 'player'
    form_fields = [
        'ethical_inclusion',
        'ethical_inclusion_expl',
        'ethical_approval',
        'ethical_approval_expl',
        'comments'
    ]

    @staticmethod
    def is_displayed(player):
        return player.participant.vars.get("category") is not None


page_sequence = [Survey]

