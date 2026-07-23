import random
import string

from otree.api import Bot, Submission

from . import *


N_MOTIVATION_TOKENS = 5

class PlayerBot(Bot):

    def play_round(self):

        yield Submission(
            Demographics,
            dict(
                gender=random.choices(
                    ["Man", "Woman"],
                    weights=[0.6, 0.40],
                    k=1,
                )[0]
            ),
            check_html=False,
        )


        yield Submission(
            Vignette,
            dict(
                vignette_problematic=random.choice([
                    *range(-10, -2),
                    *range(3, 11),
                ]),
                vignette_discriminatory=random.choice([
                    *range(-10, -2),
                    *range(3, 11),
                ]),
                vignette_imagine=random.choice([
                    *range(-10, -2),
                    *range(3, 11),
                ]),
            ),
            check_html=False,
        )

        motivation = " ".join(
            random.choice(string.ascii_lowercase)
            for _ in range(N_MOTIVATION_TOKENS)
        )

        yield Submission(
            Motivation,
            dict(motivation=motivation),
            check_html=False,
        )

