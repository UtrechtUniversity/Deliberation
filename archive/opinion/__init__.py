from otree.api import *

doc = """
Present the reading task and ask players to what extent they would attribute the situation to discrimination.
"""

class Constants(BaseConstants):
    name_in_url = 'opinion'
    players_per_group = None
    num_rounds = 1
    max_chars = 500 # maximum number of characters for motivation

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass

# vignette text
vignette_text = \
    "The company where you work is hiring a new department manager. "\
    "Two internal candidates apply: Mary and Paul. You know these candidates well. "\
    "Both have worked at the company for several years and have similar qualifications and performance evaluations. "\
    "In the end, Paul is selected for the position instead of Mary."

# scale from -10 (no discrimination) to 10 (discrimination)
scale_choices = [(i, str(i)) for i in range(-10, 11)]

class Player(BasePlayer):

    vignette_problematic = models.IntegerField(
        choices=scale_choices,
        widget=widgets.RadioSelect,
        label="To what extent do you think this situation is problematic?"
    )

    vignette_discriminatory = models.IntegerField(
        choices=scale_choices,
        widget=widgets.RadioSelect,
        label="To what extent do you think this situation is discriminatory?"
    )

    vignette_imagine = models.IntegerField(
        choices=scale_choices,
        widget=widgets.RadioSelect,
        label="To what extent can you imagine others would perceive this situation as discriminatory?"
    )

    motivation = models.LongStringField(
        label=f"Please explain why you chose your answers (max {Constants.max_chars} characters)."
    )

class Vignette(Page):
    form_model = "player"
    form_fields = ["vignette_problematic", "vignette_discriminatory", "vignette_imagine" ]

    @staticmethod
    def vars_for_template(player: Player):
        return dict(vignette=vignette_text)

    def before_next_page(player: Player, timeout_happened):
        score = player.vignette_discriminatory
        gender = player.participant.vars.get("gender")

        category = None  # default = NA

        if gender == "Man":
            if score < -2:
                category = "M+"
            elif score > 2:
                category = "M-"

        elif gender == "Woman":
            if score < -2:
                category = "W+"
            elif score > 2:
                category = "W-"

        player.participant.vars["category"] = category
        player.participant.vars["vignette_discriminatory"] = score
        print(f"Participant {player.participant.id_in_session} category: {category}")

class Motivation(Page):
    form_model = "player"
    form_fields = ["motivation"]

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            max_chars=Constants.max_chars,
            vignette = vignette_text,
            values = {
                "problematic": player.vignette_problematic,
                "discriminatory": player.vignette_discriminatory,
            }
        )

    @staticmethod
    def error_message(player: Player, values):
        text = (values.get("motivation") or "").strip()

        if not text:
            return "Please provide an explanation."

        if len(text) > Constants.max_chars:
            return (
                f"Please keep your explanation to {Constants.max_chars} characters or fewer."
            )

page_sequence = [Vignette, #Motivation
 ]

