import re

from django.http import HttpResponseBadRequest
from django.shortcuts import redirect
from django.urls import reverse

from ..core.utils.model import model_url_name
from ..core.utils.prefetch import prefetch_nested_techniques
from ..core.views.base import BaseDetailView, BaseIndexView
from . import models
from .utils import get_model_by_id


def redirect_by_id(request, mitre_id):
    model = get_model_by_id(mitre_id)
    if model is None:
        return HttpResponseBadRequest("No model found for this id scheme")
    else:
        #: Adjust the identifier to its canonical form.
        mitre_id = re.sub("^([a-z]{1,2})", lambda m: m.group(0).upper(), mitre_id)
        return redirect(reverse(model_url_name(model, "detail"), args=[mitre_id]))


class TechniqueIndexView(BaseIndexView):
    model = models.Technique
    flat_filtering_form_hidden_fields = ["collection*", "tactic*"]


class TechniqueDetailView(BaseDetailView):
    model = models.Technique
    fields = ["mitre_id", "name", "short_description"]
    slug_field = "mitre_id"


class SoftwareDetailView(BaseDetailView):
    model = models.Software
    fields = ["mitre_id", "name", "short_description"]
    slug_field = "mitre_id"


class GroupDetailView(BaseDetailView):
    model = models.Group
    fields = ["mitre_id", "name", "short_description", "aliases"]
    slug_field = "mitre_id"


class DataSourceDetailView(BaseDetailView):
    model = models.DataSource
    fields = ["mitre_id", "name", "short_description"]
    slug_field = "mitre_id"

    def get_title(self):
        suffix = ""
        if self.object.revoked:
            suffix = " (revoked)"
        return f"{self.object.name}{suffix}"


class TacticDetailView(BaseDetailView):
    model = models.Tactic
    fields = ["mitre_id", "name", "short_description"]
    slug_field = "mitre_id"


class MatrixDetailView(BaseDetailView):
    model = models.Matrix
    fields = ["mitre_id", "name", "short_description"]

    def get_ordered_tactics(self):
        if not hasattr(self, "_ordered_tactics"):
            self._ordered_tactics = self.object.tactic_set.order_by(
                "order_weight"
            ).prefetch_related(prefetch_nested_techniques(models.Technique))
        return self._ordered_tactics

    def get_title(self):
        return self.object.name


class MitigationDetailView(BaseDetailView):
    model = models.Mitigation
    fields = ["mitre_id", "name", "short_description"]
    slug_field = "mitre_id"


class CampaignDetailView(BaseDetailView):
    model = models.Campaign
    slug_field = "mitre_id"
