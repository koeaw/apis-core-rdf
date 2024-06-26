from apis_core.generic.filtersets import GenericFilterSet, GenericFilterSetForm
from django_filters import CharFilter, ModelMultipleChoiceFilter
from django.contrib.contenttypes.models import ContentType
from apis_core.apis_relations.models import Property
from django.db.models import Q

PROPERTY_EXCLUDES = [
    "self_contenttype",
    "deprecated_name",
    "property_class_uri",
    "rootobject_ptr",
]


class PropertyFilterSetForm(GenericFilterSetForm):
    columns_exclude = PROPERTY_EXCLUDES


class PropertyFilterSet(GenericFilterSet):
    name_forward = CharFilter(lookup_expr="icontains")
    name_reverse = CharFilter(lookup_expr="icontains")

    class Meta:
        form = PropertyFilterSetForm
        exclude = PROPERTY_EXCLUDES


class TripleFilterSet(GenericFilterSet):
    subj = CharFilter(method="subj_icontains")
    obj = CharFilter(method="obj_icontains")
    subj_class = ModelMultipleChoiceFilter(
        label="Subj class",
        queryset=ContentType.objects.filter(
            pk__in=Property.objects.all().values("subj_class")
        ),
        method="class_in",
    )
    obj_class = ModelMultipleChoiceFilter(
        label="Obj class",
        queryset=ContentType.objects.filter(
            pk__in=Property.objects.all().values("obj_class")
        ),
        method="class_in",
    )

    def subj_icontains(self, queryset, name, value):
        return queryset.filter(subj__name__icontains=value)

    def obj_icontains(self, queryset, name, value):
        return queryset.filter(obj__name__icontains=value)

    def class_in(self, queryset, name, value):
        # value is the list of contenttypes
        if value and name:
            name, _ = name.split("_")
            return queryset.filter(Q(**{f"{name}__self_contenttype__in": value}))
        return queryset
