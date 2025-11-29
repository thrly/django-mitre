from django.apps import apps
from django.urls import include

from ..core.utils import path, produce_paths_for_model, re_path
from ..core.views import AppIndexView
from . import models, patterns, views


app_name = "mitrembc"

urlpatterns = [
    path(
        "",
        AppIndexView.as_view(title="Mitre MBC", app_name=app_name),
        name="index",
    ),
    # Matrix
    path(
        "matrix/",
        views.MatrixIndexView.as_view(),
        name="index",
        model=models.Matrix,
    ),
]

VIEWABLE_MODELS_AND_PK_PATTERNS = (
    # [<model>, <pattern>],
    # patterns.MATRIX_ID_PATTERN,  # Matrix is special
    patterns.SOFTWARE_ID_PATTERN,
    patterns.TACTIC_ID_PATTERN,
    patterns.TECHNIQUE_ID_PATTERN,
)

for model_name, regex_pk_pattern in VIEWABLE_MODELS_AND_PK_PATTERNS:
    model = apps.get_model(model_name)
    urlpatterns += [
        path(
            f"{model._meta.model_name}/",
            #: regex_pk_pattern is an re.compile object; pull out the pattern
            include(produce_paths_for_model(model, regex_pk_pattern.pattern)),
        ),
    ]


# Redirect to the correct model view based on the mitre id
urlpatterns.append(
    re_path(
        r"^redirect-id/(?P<mitre_id>[\w.]+)/",
        views.redirect_by_id,
        name="redirect_by_mitre_id",
    )
)
