from django.conf.urls import url
from django.conf import settings
from rest_framework.urlpatterns import format_suffix_patterns
from entities import api_views
from entities.api_views import GetOrCreateEntity
from highlighter.api_views import AnnotatorAgreementView, ShowOverlappingHighlights

app_name = 'entities'

urlpatterns = [
    url(r'^savenetworkfiles/$', api_views.SaveNetworkFiles.as_view()),
    url(r'^annotatoragreement/$', AnnotatorAgreementView.as_view(), name='AnnotatorAgreementView'),
    url(r'^overlappinghighlights/$', ShowOverlappingHighlights.as_view(), name='ShowOverlappingHighlights'),
    url(r'^getorcreateentity/$', GetOrCreateEntity.as_view(), name='GetOrCreateEntity')
]

if 'deep learning' in getattr(settings, "APIS_COMPONENTS", []):
    from highlighter.api_views import TestDLModel
    urlpatterns.append(url(r'^nlp_model/$', TestDLModel.as_view(), name='TestDLModel'),)
