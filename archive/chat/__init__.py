from otree.api import *

from settings import (
    GROUP_SIZE as group_size,)


doc = """
Custom chat app that preserves groups from a previous app.
adjusted from https://github.com/oTree-org/otree-snippets/tree/master 
"""

class Constants(BaseConstants):
    name_in_url = 'chat'
    players_per_group = None
    num_rounds = 1


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    pass

"""hier dan een extraModel 'authors' 

hmm.. weet niet of dit voor cross-app gebruik werkt...
aangezien huidige grouping page niet op basis van arrival time is,
hoeft 'ie niet als eerste pagina. dus alles kan geintegreerd
1. reading task (give score [-10; 10])
2. writing task (brief argumentation)
   hier moet dan opgeslagen naar ExtraModel gebeuren
3. grouping page
    2 routes:
        - groeperen in sets --> deliberation task (chatroom)
        - niet-gegroepeerd --> estimation task [(]selectie uit ExtraModel; bv., selecteer text zonder numbers (want geen score-reveal)]
            hoe vertalen we argumenten naar score, en hoe hangt dit af van demographic similarity en opinion distance

"""
class Author(ExtraModel):
    sender = models.Link(Player)
    text = models.StringField()



def to_dict(msg: Author):
    return dict(sender=msg.sender.id_in_group, text=msg.text)


class Message(ExtraModel):
    group = models.Link(Group)
    sender = models.Link(Player)
    text = models.StringField()


def to_dict(msg: Message):
    return dict(sender=msg.sender.id_in_group, text=msg.text)

def group_by_arrival_time_method(subsession: Subsession, waiting_players):
    groups = {}
    for p in waiting_players:
        group_id = p.participant.group_id
        if group_id not in groups:
            groups[group_id] = []
        groups[group_id].append(p)
        if len(groups[group_id]) == group_size:
            return groups[group_id]

class GroupFormationWaitPage(WaitPage):
    group_by_arrival_time = True
    body_text = "Waiting for your group members ..."



# PAGES
class ChatPage(Page):
    #only show to people assigned to a set of groups
    @staticmethod
    def is_displayed(player: Player):
        return player.participant.vars.get("set_id") is not None

    @staticmethod
    def js_vars(player: Player):
        return dict(my_id=player.id_in_group)

    @staticmethod
    def live_method(player: Player, data):
        my_id = player.id_in_group
        group = player.group

        if 'text' in data:
            text = data['text']
            msg = Message.create(group=group, sender=player, text=text)
            return {0: [to_dict(msg)]}
        return {my_id: [to_dict(msg) for msg in Message.filter(group=group)]}

def custom_export(players):
    yield [
        'session_code',
        'participant_code',
        'group_id',
        'sender_id_in_group',
        'message_text',
    ]

    # avoid exporting the same message multiple times
    seen_groups = set()

    for player in players:
        group = player.group
        if group.id in seen_groups:
            continue
        seen_groups.add(group.id)

        messages = Message.filter(group=group)
        for msg in messages:
            yield [
                player.session.code,
                msg.sender.participant.code,
                msg.group.id,
                msg.sender.id_in_group,
                msg.text,
            ]

""""
in de groepsformatie functie, moet dan voor alle spelers een entry zijn met gender, score, en argumentatie.
dan subsets maken per category (M+, M-, W+, W-)
dan per category random sample van X.
"""


def group_by_arrival_time_method(subsession: Subsession, waiting_players):
    groups = {}
    for p in waiting_players:
        group_id = p.participant.group_id
        if group_id not in groups:
            groups[group_id] = []
        groups[group_id].append(p)
        if len(groups[group_id]) == group_size:
            return groups[group_id]


"""
Here, I need to define a function that:
- selects a player from the session, from a specific category/bin (e.g., M+)
- returns the text argument, demographic trait, and score

Players are shown X 'authors' (along with their argumentation).
And they need to estimate their score.
This choice is incentivized: when they estimate the right side, they earn X cents;
when their estimation and the author's self-reported


here i need a function that get fired upon arrival;
players are presented with an argument (+ demographics) of an 'author'
these can be selected from the pool of all submitted argumentation.
based on some criteria (e.g., category + score)
repeatedly (e.g., multiple types, in random order)

they are then asked to 'estimate' the score
here we should add monetary incentive.
e.g., right side = X cents; exactly right (or 1 off at max.) an additional Z cents.
"""

class EstimationTask(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.participant.vars.get("set_id") is None


page_sequence = [ GroupFormationWaitPage, ChatPage, EstimationTask]
