from importlib import import_module

from django.db.models import Model
from django.urls import path, re_path
from django_filtering import filterset_factory

from ..filters import MitreFilterSet
from ..views.base import BaseIndexView, FilterView
from .model import model_url_name


__all__ = [
    "get_view_class_name",
    "produce_paths_for_model",
]


def get_view_class_name(m: Model, v: str):
    """Produce the view name from the model and view indicator"""
    return f"{m.__name__}{v.title()}View"


def gracefully_import_module(name, package=None, default=None):
    """
    Gracefully use the default when ``ModuleNotFoundError`` is raised.
    """
    try:
        return import_module(name, package)
    except ModuleNotFoundError:
        return default


def produce_paths_for_model(
    model,
    pk_pattern,
    IndexView=BaseIndexView,
    FilterView=FilterView,
    default_filterset_class=MitreFilterSet,
):
    # Find supporting modules
    #: Don't assume the app has a `filters` module.
    app_config = model._meta.app_config
    app_filters = gracefully_import_module(".filters", app_config.module.__package__, default={})
    views = getattr(app_config.module, "views", None)
    assert views, f"Missing `views` module for {app_config.name}"

    # Get or create the index view class.
    index_view_class = getattr(views, get_view_class_name(model, "index"), None)
    if index_view_class is None:
        index_view_class = IndexView

    # Get or create the filterset class.
    filterset_class = getattr(app_filters, f"{model.__name__}FilterSet", None)
    if filterset_class is None:
        filterset_class = filterset_factory(
            model=model,
            base_cls=default_filterset_class,
        )

    # Create views
    filter_view = FilterView.as_view(model=model, filterset_class=filterset_class)
    index_view = index_view_class.as_view(model=model, filterset_class=filterset_class)
    detail_view = getattr(views, get_view_class_name(model, "detail")).as_view()

    paths = [
        re_path(
            "^$",
            index_view,
            name=model_url_name(model, "index", namespaced=False),
        ),
        re_path(
            f"^detail/{pk_pattern}/$",
            detail_view,
            name=model_url_name(model, "detail", namespaced=False),
        ),
        path(
            "filter/",
            filter_view,
            name=model_url_name(model, "filter", namespaced=False),
        ),
    ]
    return paths
