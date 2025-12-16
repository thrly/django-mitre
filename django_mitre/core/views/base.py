"""
Base views for mitre content

"""

import json
from collections.abc import Generator
from urllib.parse import urlencode

from django import forms
from django.conf import settings
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.decorators import classonlymethod
from django.views.generic import DetailView, FormView, ListView
from django.views.generic.edit import FormMixin
from django_filtering.form import flat_filtering_form_factory

from ..forms import FilterForm
from ..utils import model_fields, model_url_name


class UseMitreCoreTemplatesMixin:
    template_filename = None

    def get_template_names(self):
        model_app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        return [
            f"{model_app_label}/{model_name}/{self.template_filename}",
            f"{model_app_label}/{self.template_filename}",
            # default to the mitrecore template
            f"mitrecore/{self.template_filename}",
        ]


class FlatFilteringFormViewMixin(FormMixin):
    filterset_class = None
    flat_filtering_form_hidden_fields = ["collection*"]

    def get_form_class(self):
        return flat_filtering_form_factory(
            self.filterset_class,
            hidden_fields=self.flat_filtering_form_hidden_fields,
        )

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["filterset"] = self.get_filterset()
        return kwargs

    def form_valid(self, form):
        # Assign the form for access within `get_success_url`.
        self.form = form
        return super().form_valid(form)

    def get_success_url(self):
        url = reverse(model_url_name(self.model, "index"))
        qs = urlencode(
            {
                "q": json.dumps(self.form.filterset.query_data),
            }
        )
        return f"{url}?{qs}"


class BaseIndexView(UseMitreCoreTemplatesMixin, FlatFilteringFormViewMixin, ListView):
    fields = ["mitre_id", "name", "short_description", "collection"]
    fields_to_form_field = {
        "mitre_id": "mitre_id__icontains",
        "name": "name__icontains",
        "short_description": "description__icontains",
        "collection": None,
    }
    template_filename = "index.html"
    paginate_by = 20
    filterset_class = None

    @classonlymethod
    def as_view(cls, **initkwargs):
        if cls.model is None and "model" not in initkwargs:
            raise TypeError(f"{cls.__name__} requires the `model` be defined.")
        if cls.filterset_class is None and "filterset_class" not in initkwargs:
            raise TypeError(f"{cls.__name__} requires the `filterset_class` be defined.")
        return super().as_view(**initkwargs)

    def get_model_fields(self):
        return model_fields(self.model, self.fields)

    def get_filter_form_fields(self) -> Generator[forms.Field | None, None, None]:
        form = self.get_form()

        for field in self.fields:
            form_field_name = self.fields_to_form_field[field]
            if not form_field_name:
                yield None
            else:
                yield form[form_field_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["listing_url"] = reverse(model_url_name(self.model, "index"))
        context["filtering_url"] = reverse(model_url_name(self.model, "filter"))

        context["filter_url_name"] = model_url_name(self.model, "filter")
        context["is_filtered"] = bool(self.get_filters())
        filterset = self.get_filterset()
        context["filtering_options_schema"] = str(filterset.filtering_options_schema)
        context["filtering_json_schema"] = str(filterset.json_schema)
        context["DEBUG"] = "true" if settings.DEBUG else "false"  # js true/false value
        return context

    def get_filters(self):
        form = FilterForm(self.request.GET)
        if not form.is_valid():
            raise Exception(f"Ran into form validation error? {form.errors}")
        q = form.cleaned_data["q"]
        return q if q else []

    def get_filterset_class(self):
        return self.filterset_class

    def get_filterset(self):
        filterset_class = self.get_filterset_class()
        return filterset_class(self.get_filters()) if filterset_class else None

    def filter_queryset(self, queryset):
        filterset_cls = self.get_filterset_class()
        if filterset_cls is None:
            return queryset

        filter_data = self.get_filters()
        if not filter_data:
            return queryset

        filterset = filterset_cls(filter_data)
        return filterset.filter_queryset(queryset)

    def get_ordering(self):
        # Only allow to order by one field at a time.
        field_name = self.request.GET.get("order")
        if field_name and field_name.strip("-") not in self.fields:
            return None
        return field_name

    def get_queryset(self):
        queryset = super().get_queryset()
        # Filter out all deprecated and revoked content
        queryset = queryset.filter(deprecated=False, revoked=False)
        # Filter using user supplied criteria
        queryset = self.filter_queryset(queryset)
        return queryset

    def get_title(self):
        return self.model._meta.verbose_name_plural.title()


class BaseDetailView(UseMitreCoreTemplatesMixin, DetailView):
    template_filename = "detail.html"

    def get_object(self, queryset=None):
        # Try getting the object without specific filtering
        # We do want to be able to display revoked and deprecated records.
        try:
            obj = super().get_object(queryset=queryset)
        except self.model.MultipleObjectsReturned:
            if queryset is None:
                queryset = self.model.objects.all()
            # Multiple objects were found, a rare case.
            # Likely culprit is a record with the mitre identifier
            # that is in either a deprecated or revoked state.
            queryset = queryset.filter(deprecated=False, revoked=False)
            obj = super().get_object(queryset=queryset)
        return obj

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data()
        context_data["title"] = self.get_title()
        context_data["title_suffix"] = self.get_title_suffix()
        context_data["mitre_id"] = self.object.mitre_id
        return context_data

    def get_title(self):
        return self.object.name

    def get_title_suffix(self):
        return "[revoked]" if self.object.revoked else ""


class FilterView(UseMitreCoreTemplatesMixin, FormView):
    model = None
    form_class = None
    filterset_class = None
    template_filename = "filters.html"

    def get_form_class(self):
        """
        Overridden to provide a default when no ``form_class`` is set.
        """
        if self.form_class is None:
            return FilterForm
        return self.form_class

    def form_valid(self, form):
        querystring = urlencode({"q": json.dumps(form.cleaned_data["q"])})
        url = reverse(model_url_name(self.model, "index"))
        if querystring:
            url = f"{url}?{querystring}"
        return HttpResponseRedirect(url)

    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        kwargs = {
            "initial": self.get_initial(),
            "prefix": self.get_prefix(),
        }
        if self.request.method in ("POST", "PUT"):
            kwargs.update(
                {
                    "data": self.request.POST,
                    "files": self.request.FILES,
                }
            )
        elif self.request.method == "GET":
            kwargs.update(
                {
                    "data": self.request.GET,
                }
            )
        return kwargs

    def get_filterset_class(self):
        return self.filterset_class

    def get_filterset(self, form):
        filterset = self.get_filterset_class()(form.cleaned_data["q"])
        return filterset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["listing_url"] = reverse(model_url_name(self.model, "index"))
        context["filtering_url"] = reverse(model_url_name(self.model, "filter"))

        form = context["form"]
        form.is_valid()
        filterset = self.get_filterset(form)
        context["filtering_options_schema"] = str(filterset.filtering_options_schema)
        context["filtering_json_schema"] = str(filterset.json_schema)
        context["DEBUG"] = "true" if settings.DEBUG else "false"  # js true/false value
        return context

    def get_title(self):
        return f"Filter {self.model._meta.verbose_name_plural.title()}"
