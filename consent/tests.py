from otree.api import Bot
from . import *

class PlayerBot(Bot):
    def play_round(self):
        # give consent
        yield ConsentPage, {'consent': True}
