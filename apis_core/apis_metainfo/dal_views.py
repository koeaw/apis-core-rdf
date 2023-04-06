from dal import autocomplete

from apis_core.apis_entities.models import TempEntityClass


class TempEntityClassAC(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = TempEntityClass.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs
