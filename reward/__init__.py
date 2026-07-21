from otree.api import *


doc = """
Participants are redirected to Prolific with a completion code.
We have separate codes for those assigned a deliberation/pseudo group.
-hose who are not eligible (due to non-binary gender or neutral response to discrimination attribution item) skip the
group formation phase; they are requested to return the study via Prolific. They will receive fair compensation for the 
reading/writing task.
"""


class Constants(BaseConstants):
    name_in_url = 'reward'
    players_per_group = None
    num_rounds = 1

    base_pay = "5.00"
    bonus_pay = "4.00"
    ineligible_pay = "1.50"

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    pass

# PAGES

class NotEligible(Page):

    @staticmethod
    def is_displayed(player):
        return (
            player.participant.vars.get("set_id") is None
            and player.participant.vars.get("category") is None
        )

    @staticmethod
    def vars_for_template(player):
        return dict(
            timeout_seconds=45,
            pay=Constants.ineligible_pay,
        )

class PaymentInfo(Page):
    form_model = 'player'

    @staticmethod
    def js_vars(player):
        if player.participant.vars.get("set_id") is not None:
            completionlink = player.subsession.session.config[
                'completionlink_deliberation'
            ]
        elif player.participant.vars.get("category") is not None:
            completionlink = player.subsession.session.config[
                'completionlink_pseudo'
            ]
        else:
            completionlink = player.subsession.session.config[
                'completionlink_nocategory'
            ]

        return dict(completionlink=completionlink)

page_sequence = [NotEligible, PaymentInfo]