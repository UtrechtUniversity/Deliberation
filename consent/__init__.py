import datetime, random
from otree.api import *

doc = """
Participants arrive at a consent form.
"""

class Constants(BaseConstants):
    name_in_url = 'consent'
    players_per_group = None
    num_rounds = 1


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    consent = models.BooleanField(
        label="",
        choices=[[True, 'I consent']],
        blank=True
    )
    consent_timestamp = models.StringField(blank=True)

class ConsentPage(Page):
    form_model = 'player'
    form_fields = ['consent']


    def error_message(player, values):
        if not values.get('consent'):
            return "You must check the box to give your consent in order to participate in this study."

    def before_next_page(player: Player, timeout_happened):
        if not player.consent:
            player.participant.vars['consent'] = False
            return

        # timestamp
        player.consent_timestamp = datetime.datetime.now().isoformat()

        # store for downstream apps
        player.participant.vars['consent'] = True


page_sequence = [ConsentPage]
