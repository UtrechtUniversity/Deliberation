from os import environ

SESSION_CONFIGS = [
    dict(
        name='test',
        display_name='test',
        app_sequence=['opinion', 'discussion', 'chat'],
        num_demo_participants=30,
    ),
]

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00, participation_fee=0.00, doc=""
)

# set some central parameters to be used across apps:
GROUP_SIZE = 2

PARTICIPANT_FIELDS = ["past_group_id"]
LANGUAGE_CODE = 'en'
REAL_WORLD_CURRENCY_CODE = 'EUR'
USE_POINTS = True

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')

DEMO_PAGE_INTRO_HTML = """ """

SECRET_KEY = 'secret'
