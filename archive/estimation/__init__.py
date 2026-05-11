from otree.api import *

doc = """
Ungrouped players proceed to a different app.
Here, they are tasked to estimate the scores of other players based on their argumentation (and demographics).
"""

class Constants(BaseConstants):
    name_in_url = 'estimate'
    players_per_group = None
    num_rounds = 1

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    pass


"""
here i need a function that get fired upon arrival;
players are presented with an argument (+ demographics) of an 'author'
these can be selected from the pool of all submitted argumentation.
based on some criteria (e.g., category + score)
repeatedly (e.g., multiple types, in random order)

they are then asked to 'estimate' the score
here we should add monetary incentive.
e.g., right side = X cents; exactly right (or 1 off at max.) an additional Z cents.

"""

class Estimation(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.participant.vars.get("set_id") is None


page_sequence = [Estimation]
