from os import environ

SESSION_CONFIGS = [
    dict(
        name='test',
        display_name='test',
        app_sequence=['consent',
             'experiment'],
        num_demo_participants=16, # the number of participants that can enter the experiment
    ),
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
