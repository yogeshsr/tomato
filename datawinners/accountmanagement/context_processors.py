from django.conf import settings
from django.utils import translation
from django.utils.translation import get_language


def add_feature_flags(context):
    flags_dict = {'TRIAL_REGISTRATION_ENABLED': settings.TRIAL_REGISTRATION_ENABLED,
            'GOOGLE_MAPS_ENABLED': settings.GOOGLE_MAPS_ENABLED,
            'GOOGLE_ANALYTICS_ENABLED': settings.GOOGLE_ANALYTICS_ENABLED,
            'DEBUG': settings.DEBUG,
            'EDIT_SUBJECT_ENABLED': settings.EDIT_SUBJECT_ENABLED,
            'EDIT_DATA_SENDERS_ENABLED': settings.EDIT_DATA_SENDERS_ENABLED,
            'refresh_rate': settings.REFRESH_RATE,

            'MULTI_LANGUAGE': True,
            'IDENTIFICATION_NUMBERS_ENABLED': True,
            'CUSTOMIZE_MESSAGE_ENABLED': True,
            'SIMPLE_SURVEY_ENABLED': True,
            'SMS_STATISTICS_ENABLED': True
    }

    if hasattr(settings, "BRAND_FEATURES") and len(settings.BRAND_FEATURES):
        flags_dict.update(settings.BRAND_FEATURES)

    return flags_dict

def add_help_link(context):
    return {'support_help_link': context.build_absolute_uri('/%s/support' % get_language())}

def current_active_language(context):
    return {'active_language': translation.get_language()}
