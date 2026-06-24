from os import environ

SESSION_CONFIGS = [
    dict(
        name='deliberation14',
        display_name='4 Player Deliberation Rooms (Pilot)',
        vignette='vignette1',
        app_sequence=['experiment', 'survey', 'reward'],
        #app_sequence=['consent','experiment','reward', 'survey'],
        num_demo_participants=14, # the number of participants that can enter the experiment
        completionlink_pseudo = 'https://app.prolific.com/submissions/complete?cc=PSEUDO',
        completionlink_deliberation = 'https://app.prolific.com/submissions/complete?cc=DELIBERATION',
        completionlink_nocategory = 'https://app.prolific.com/submissions/complete?cc=NO_CATEGORY'),


]

ROOMS = [
    dict(
        name='test',
        display_name='Deliberation Room',
        # participant_label_file='_rooms/fashion_dilemma.txt',
        # use_secure_urls=True,
    ),
]

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00, participation_fee=0.00, doc=""
)

# set some central parameters to be used across apps:
GROUP_SIZE = 4 # the number of people per discussion group

PARTICIPANT_FIELDS = ["group_id"]
LANGUAGE_CODE = 'en'
REAL_WORLD_CURRENCY_CODE = 'EUR'
USE_POINTS = True

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

DEMO_PAGE_INTRO_HTML = """ """

SECRET_KEY = 'secret'
