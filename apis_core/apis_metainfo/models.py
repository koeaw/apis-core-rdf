import re
from difflib import SequenceMatcher
from math import inf
import copy
import importlib

import requests

# from reversion import revisions as reversion
import reversion
from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.fields.reverse_related import ManyToOneRel
from django.db.models.fields.related import OneToOneField, ForeignKey, ManyToManyField
from django.forms import model_to_dict
from django.urls import reverse
from django.utils.functional import cached_property
from model_utils.managers import InheritanceManager
from apis_core.utils.normalize import clean_uri
from django.core.exceptions import ValidationError, ImproperlyConfigured

# from django.contrib.contenttypes.fields import GenericRelation
# from utils.highlighter import highlight_text
from apis_core.utils import caching, rdf

from apis_core.apis_metainfo import signals

# from apis_core.apis_entities.serializers_generic import EntitySerializer
# from apis_core.apis_labels.models import Label
# from apis_core.apis_vocabularies.models import CollectionType, LabelType, TextType

path_ac_settings = getattr(settings, "APIS_AUTOCOMPLETE_SETTINGS", False)
if path_ac_settings:
    ac_settings = importlib.import_module(path_ac_settings)
    autocomp_settings = getattr(ac_settings, "autocomp_settings")
else:
    from apis_core.default_settings.NER_settings import autocomp_settings
# from apis_core.utils import DateParser

NEXT_PREV = getattr(settings, "APIS_NEXT_PREV", True)

if "apis_highlighter" in settings.INSTALLED_APPS:
    from apis_highlighter.models import Annotation


class RootObject(models.Model):
    """
    The very root thing that can exist in a given ontology. Several classes inherit from it.
    By having one overarching super class we gain the advantage of unique identifiers.
    """

    name = models.CharField(max_length=255, verbose_name="Name")
    # self_contenttype: a foreign key to the respective contenttype comes in handy when querying for
    # triples where the subject's or object's contenttype must be respected (e.g. get all triples
    # where the subject is a Person)
    self_contenttype = models.ForeignKey(
        ContentType, on_delete=models.deletion.CASCADE, null=True, blank=True
    )
    objects = models.Manager()
    objects_inheritance = InheritanceManager()

    def save(self, *args, **kwargs):
        if self.self_contenttype is None:
            self.self_contenttype = caching.get_contenttype_of_class(self.__class__)
        super().save(*args, **kwargs)

    def __str__(self):
        if self.name != "":
            return self.name
        else:
            return "no name provided"

    def duplicate(self):
        origin = self.__class__
        signals.pre_duplicate.send(sender=origin, instance=self)
        # usually, copying instances would work like
        # https://docs.djangoproject.com/en/4.2/topics/db/queries/#copying-model-instances
        # but we are working with abstract classes,
        # so we have to do it by hand  using model_to_dict:(
        objdict = model_to_dict(self)
        objdict.pop("id")

        # remove related fields from dict representation
        related_fields = [
            field for field in self._meta.get_fields() if field.is_relation
        ]
        for field in related_fields:
            objdict.pop(field.name, None)

        entity_model = caching.get_entity_class_of_name(self._meta.model_name)
        newobj = entity_model.objects.create(**objdict)

        for field in related_fields:
            # we are not using `isinstance` because we want to
            # differentiate between different levels of inheritance
            if type(field) is ForeignKey:
                setattr(newobj, field.name, getattr(self, field.name))
            if type(field) is ManyToManyField:
                objfield = getattr(newobj, field.name)
                values = getattr(self, field.name).all()
                objfield.set(values)

        duplicate = newobj.save()
        signals.post_duplicate.send(sender=origin, instance=self, duplicate=duplicate)
        return duplicate


@reversion.register()
class Source(models.Model):
    """Holds information about entities and their relations"""

    orig_filename = models.CharField(max_length=255, blank=True)
    indexed = models.BooleanField(default=False)
    pubinfo = models.CharField(max_length=400, blank=True)
    author = models.CharField(max_length=255, blank=True)
    orig_id = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        if self.author != "" and self.orig_filename != "":
            return "{}, stored by {}".format(self.orig_filename, self.author)
        elif self.orig_filename != "":
            return "{}".format(self.orig_filename)
        else:
            return "(ID: {})".format(self.id)


@reversion.register()
class Collection(models.Model):
    """Allows to group entities and relation."""

    from apis_core.apis_vocabularies.models import CollectionType

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    collection_type = models.ForeignKey(
        CollectionType, blank=True, null=True, on_delete=models.SET_NULL
    )
    groups_allowed = models.ManyToManyField(Group)
    parent_class = models.ForeignKey(
        "self", blank=True, null=True, on_delete=models.CASCADE
    )
    published = models.BooleanField(default=False)

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._loaded_values = dict(zip(field_names, values))
        return instance

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if hasattr(self, "_loaded_values"):
            if self.published != self._loaded_values["published"]:
                for ent in self.tempentityclass_set.all():
                    ent.published = self.published
                    ent.save()
        super().save(*args, **kwargs)


# TODO RDF: Remove text entirely
@reversion.register()
class Text(models.Model):
    """Holds unstructured text associeted with
    one ore many entities/relations."""

    from apis_core.apis_vocabularies.models import TextType

    kind = models.ForeignKey(TextType, blank=True, null=True, on_delete=models.SET_NULL)
    text = models.TextField(blank=True)
    source = models.ForeignKey(Source, blank=True, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        if self.text != "":
            return "ID: {} - {}".format(self.id, self.text[:25])
        else:
            return "ID: {}".format(self.id)

    def check_for_deleted_annotations(self):

        from apis_highlighter.models import Annotation

        if self.pk is not None:
            deleted = []
            orig = Text.objects.get(pk=self.pk)
            if orig.text != self.text and "apis_highlighter" in settings.INSTALLED_APPS:
                ann = Annotation.objects.filter(text_id=self.pk).order_by("start")
                min_ann_len = min([x.end - x.start for x in ann])
                seq = SequenceMatcher(
                    lambda x: len(x) > min_ann_len, orig.text, self.text
                )
                for a in ann:
                    changed = False
                    count = 0
                    for s in seq.get_matching_blocks():
                        count += 1
                        if s.a <= a.start and (s.a + s.size) >= a.end:
                            old_start = copy.deepcopy(a.start)
                            old_end = copy.deepcopy(a.end)
                            new_start = a.start + (s.b - s.a)
                            new_end = a.end + (s.b - s.a)
                            if (
                                orig.text[old_start:old_end]
                                == self.text[new_start:new_end]
                            ):
                                changed = True
                                break
                    if not changed:
                        deleted.append(a.id)
        else:
            deleted = None
        return deleted

    def save(self, *args, **kwargs):

        if self.pk is not None:
            orig = Text.objects.get(pk=self.pk)
            if orig.text != self.text and "apis_highlighter" in settings.INSTALLED_APPS:
                from apis_highlighter.models import Annotation

                def correlate_annotations(text_old, text_new, annotations_old):
                    """
                    This function computes the positions for pre-existing annotations when a text is
                    changed. Since we only received the old and the new text we don't have any
                    information on the individual steps of changes happened to the text. And
                    since we don't have that information we can not know for sure where a
                    pre-existing annotation has moved to given its relative position in a text (
                    because the annotated sub-text alone is not enough to give this information
                    because there can exist multiple of the same sub-text).

                    So we use a heuristic here where for each annotation embedded in an old text
                    we compute its textual neighbourhood and give each word a weight where the
                    weight depends on proximity to the annotation. For example the word to the
                    left of an annotation and the word to the right of an annotation both have a
                    high score while the outermost ones at the beginning and the end of the text
                    have the lowest score. Now when we receive a new text we do the same
                    computation again and then correspond the annotations with each other that
                    have the closes score (i.e. the most similar textual context).

                    :param text_old: the old text coming from the db
                    :param text_new: the new text coming from the user
                    :param annotations_old: the list of pre-existing annotations in the old text
                    :return: None - the computed changes are persisted in the annotations
                    """

                    def calculate_context_weights(text, i_start, i_end):
                        def calculate_word_dict(text, direction):
                            word_list = re.split(" |\\n", text)
                            word_list = [w for w in word_list if w != ""]
                            word_dict = {}
                            if word_list != []:
                                value_step = 1 / len(word_list)
                                value_current = 1
                                for word in word_list[::direction]:
                                    word_value = word_dict.get(word, 0)
                                    word_dict[word] = word_value + value_current
                                    value_current -= value_step

                            return word_dict

                        text_left = text[:i_start]
                        text_right = text[i_end:]
                        word_dict_left = calculate_word_dict(
                            text=text_left, direction=-1
                        )
                        word_dict_right = calculate_word_dict(
                            text=text_right, direction=1
                        )

                        return {
                            "word_dict_left": word_dict_left,
                            "word_dict_right": word_dict_right,
                        }

                    def make_diff(word_dict_a, word_dict_b):
                        words_all = set(word_dict_a.keys()).union(
                            set(word_dict_b.keys())
                        )
                        diff_all = 0
                        for word in words_all:
                            word_value_a = word_dict_a.get(word, 0)
                            word_value_b = word_dict_b.get(word, 0)
                            diff_all += abs(word_value_a - word_value_b)

                        return diff_all

                    for ann in annotations_old:
                        i_old_start = ann.start
                        i_old_end = ann.end
                        context_weights_dict_old = calculate_context_weights(
                            text=text_old, i_start=i_old_start, i_end=i_old_end
                        )
                        ann_text = text_old[ann.start : ann.end]
                        diff_min = inf
                        i_new_start = None
                        i_new_end = None
                        for i in re.finditer(f"(?={re.escape(ann_text)})", text_new):
                            i_candidate_start = i.start()
                            i_candidate_end = i_candidate_start + len(ann_text)
                            context_weights_dict_new = calculate_context_weights(
                                text=text_new,
                                i_start=i_candidate_start,
                                i_end=i_candidate_end,
                            )
                            diff_left = make_diff(
                                context_weights_dict_new["word_dict_left"],
                                context_weights_dict_old["word_dict_left"],
                            )
                            diff_right = make_diff(
                                context_weights_dict_new["word_dict_right"],
                                context_weights_dict_old["word_dict_right"],
                            )
                            diff_current = diff_left + diff_right
                            if diff_current < diff_min:
                                diff_min = diff_current
                                i_new_start = i_candidate_start
                                i_new_end = i_candidate_end

                        if diff_min != inf:
                            ann.start = i_new_start
                            ann.end = i_new_end
                            ann.save()
                        else:
                            ann.delete()  # TODO: we might want to delete relations as well.

                correlate_annotations(
                    text_old=orig.text,
                    text_new=self.text,
                    annotations_old=Annotation.objects.filter(text_id=self.pk).order_by(
                        "start"
                    ),
                )

        super().save(*args, **kwargs)


# TODO: Move this somewhere else so that it can be imported at several places (right now it's redundant with copies)
from django.db.models.fields.related_descriptors import ForwardManyToOneDescriptor


class InheritanceForwardManyToOneDescriptor(ForwardManyToOneDescriptor):
    def get_queryset(self, **hints):
        return self.field.remote_field.model.objects_inheritance.db_manager(
            hints=hints
        ).select_subclasses()


class InheritanceForeignKey(models.ForeignKey):
    forward_related_accessor_class = InheritanceForwardManyToOneDescriptor


# Uri model
# We use a custom UriManager, so we can override the queryset `get_or_create`
# method. This is useful because we normalize the uri field before saving.


class UriQuerySet(models.query.QuerySet):
    def get_or_create(self, defaults=None, **kwargs):
        if "uri" in kwargs:
            kwargs["uri"] = clean_uri(kwargs["uri"])
        return super().get_or_create(defaults, **kwargs)


class UriManager(models.Manager):
    def get_queryset(self):
        return UriQuerySet(self.model)


@reversion.register()
class Uri(models.Model):
    uri = models.URLField(blank=True, null=True, unique=True, max_length=255)
    domain = models.CharField(max_length=255, blank=True)
    rdf_link = models.URLField(blank=True)
    root_object = InheritanceForeignKey(
        RootObject, blank=True, null=True, on_delete=models.CASCADE
    )
    # loaded set to True when RDF was loaded and parsed into the data model
    loaded = models.BooleanField(default=False)
    # Timestamp when file was loaded and parsed
    loaded_time = models.DateTimeField(blank=True, null=True)

    objects = UriManager()

    def __str__(self):
        return str(self.uri)

    def get_web_object(self):
        result = {
            "relation_pk": self.pk,
            "relation_type": "uri",
            "related_root_object": self.root_object.name,
            "related_root_object_url": self.root_object.get_absolute_url(),
            "related_root_object_class_name": self.root_object.__class__.__name__.lower(),
            "uri": self.uri,
        }
        return result

    @classmethod
    def get_listview_url(self):
        return reverse("apis_core:apis_metainfo:uri_browse")

    @classmethod
    def get_createview_url(self):
        return reverse("apis_core:apis_metainfo:uri_create")

    def get_absolute_url(self):
        return reverse("apis_core:apis_metainfo:uri_detail", kwargs={"pk": self.id})

    def get_delete_url(self):
        return reverse("apis_core:apis_metainfo:uri_delete", kwargs={"pk": self.id})

    def get_edit_url(self):
        return reverse("apis_core:apis_metainfo:uri_edit", kwargs={"pk": self.id})

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def clean(self):
        self.uri = clean_uri(self.uri)
        if self.uri and not hasattr(self, "root_object"):
            try:
                model, attributes = rdf.get_modelname_and_dict_from_uri(self.uri)
                if model and attributes:
                    app_label, model = model.split(".", 1)
                    ct = ContentType.objects.get_by_natural_key(app_label, model)
                    obj = ct.model_class()(**attributes)
                    obj.save()
                    self.root_object = obj
                else:
                    raise ImproperlyConfigured(
                        f"{uri}: found model <{model}> and attributes <{attributes}>"
                    )
            except Exception as e:
                raise ValidationError(f"{e}: {self.uri}")


# @receiver(post_save, sender=Uri, dispatch_uid="remove_default_uri")
# def remove_default_uri(sender, instance, **kwargs):
#    if Uri.objects.filter(root_object=instance.entity).count() > 1:
#        Uri.objects.filter(root_object=instance.entity, domain="apis default").delete()
