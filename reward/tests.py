from . import *

class PlayerBot(Bot):
    def play_round(self):
        if self.player.participant.consent:
            yield Submission(PaymentInfo, {}, check_html=False)
