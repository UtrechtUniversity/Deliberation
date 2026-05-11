from otree.api import *

doc = """
Collect participant demographics
"""

class Constants(BaseConstants):
    name_in_url = 'demographics'
    players_per_group = None
    num_rounds = 1


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):

    gender = models.StringField(
        choices=[
            "Woman",
            "Man",
            "X / other"
        ],
        widget=widgets.RadioSelect,
        label="What is your gender?"
    )

class Demographics(Page):
    form_model = 'player'
    form_fields = ['gender' ]

    @staticmethod
    def before_next_page(player, timeout_happened):
        player.participant.vars['gender'] = player.gender


page_sequence = [Demographics]