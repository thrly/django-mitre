from collections.abc import Callable
from functools import partial
from importlib import import_module

from django.conf import settings
from django.db.models import Model
from django.urls import path as django_urls_path
from django.urls import re_path as django_urls_re_path
from django.utils.module_loading import import_string
from django_filtering import filterset_factory

from ..filters import MitreFilterSet
from ..views.base import BaseIndexView, FilterView
from .model import model_url_name


__all__ = [
    "get_view_class_name",
    "path",
    "produce_paths_for_model",
    "re_path",
]


def default_view_wrapper(
    #: view without wrapping (e.g. `View.as_view()`)
    view: Callable,
    #: Name of the to be registered url
    url_name: str | None = None,
    model: Model | None = None,
    #: General short name of the view (e.g. list, detail, filter)
    name: str | None = None
) -> Callable:
    """
    The default view wrapper returns the view without modification.
    """
    return view


def get_view_wrapper() -> Callable:
    """
    Returns a callable wrapper function that enables the developer extending this package
    to apply custom logic to the view.
    For exmaple, the developer can use this wrapper to apply permissions checks.

    The view wrapper, registered with the ``DJANGO_MITRE_VIEW_WRAPPER`` setting
    takes a ``view`` argument and ``model``, ``name``, and ``url_name`` keyword arguments.

    """
    wrapper = getattr(settings, 'DJANGO_MITRE_VIEW_WRAPPER', default_view_wrapper)
    if isinstance(wrapper, str):
        wrapper = import_string(wrapper)
    return wrapper


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
        re_path("^$", index_view, "index", model=model),
        re_path(f"^detail/{pk_pattern}/$", detail_view, "detail", model=model),
        path("filter/", filter_view, "filter", model=model),
    ]
    return paths


def _path(
    route: str,
    view: Callable | list | tuple,
    name: str | None = None,
    model: Model | None = None,
    is_regex: bool = False,
):
    if isinstance(view, list | tuple):
        return django_urls_path(route, view)
    url_name = model_url_name(model, name, namespaced=False) if model else name
    view = get_view_wrapper()(view, model=model, name=name, url_name=url_name)
    if is_regex:
        return django_urls_re_path(route, view, name=url_name)
    else:
        return django_urls_path(route, view, name=url_name)

path = partial(_path, is_regex=False)
re_path = partial(_path, is_regex=True)
