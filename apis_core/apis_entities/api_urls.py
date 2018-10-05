from django.conf.urls import url
from django.conf import settings
from rest_framework.urlpatterns import format_suffix_patterns
from . import api_views
from .api_views import GetOrCreateEntity


app_name = 'apis_entities'

urlpatterns = [
    url(r'^savenetworkfiles/$', api_views.SaveNetworkFiles.as_view()),
    url(r'^getorcreateentity/$', GetOrCreateEntity.as_view(), name='GetOrCreateEntity')
]

if 'deep learning' in getattr(settings, "APIS_COMPONENTS", []) and 'apis_highlighter' in settings.INSTALLED_APPS:
    from apis_highlighter.api_views import TestDLModel
    urlpatterns.append(url(r'^nlp_model/$', TestDLModel.as_view(), name='TestDLModel'),)

if 'apis_highlighter' in settings.INSTALLED_APPS:
    from apis_highlighter.api_views import AnnotatorAgreementView, ShowOverlappingHighlights
    urlpatterns.extend([url(r'^annotatoragreement/$',
                            AnnotatorAgreementView.as_view(),
                            name='AnnotatorAgreementView'),
                       url(r'^overlappinghighlights/$',
                           ShowOverlappingHighlights.as_view(),
                           name='ShowOverlappingHighlights')])