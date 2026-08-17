from . import *


class PlayerBot(Bot):
    def play_round(self):
        yield Survey, {
            'ethical_inclusion': 1,
            'ethical_inclusion_expl': 'Participants should be included.',
            'ethical_approval': 2,
            'ethical_approval_expl': 'The study is acceptable with caution.',
            'comments': 'No additional comments.',
        }