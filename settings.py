from os import environ

SESSION_CONFIGS = [
    dict(
        name='deliberation',
        display_name='4 Player Deliberation Rooms (Pilot)',
        vignette='vignette1',
        app_sequence=['experiment','survey', 'reward',],
        num_demo_participants=12, # the number of participants that can enter the experiment (adjust this based on the number of registered participants)
        completionlink_pseudo = 'https://app.prolific.com/submissions/complete?cc=CR3HKI41',
        completionlink_deliberation = 'https://app.prolific.com/submissions/complete?cc=C18K70L7',
        completionlink_nocategory = 'https://app.prolific.com/submissions/complete?cc=C14567G7',
        use_browser_bots=False
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
