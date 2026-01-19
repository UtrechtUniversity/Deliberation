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


class Message(ExtraModel):
    group = models.Link(Group)
    sender = models.Link(Player)
    text = models.StringField()


def to_dict(msg: Message):
    return dict(sender=msg.sender.id_in_group, text=msg.text)

def group_by_arrival_time_method(subsession: Subsession, waiting_players):
    groups = {}
    for p in waiting_players:
        group_id = p.participant.past_group_id
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

page_sequence = [GroupFormationWaitPage, ChatPage]
