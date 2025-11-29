from django.apps import apps
from django.urls import include

from ..core.utils import path, produce_paths_for_model, re_path
from ..core.views import AppIndexView
from . import models, patterns, views
from .filters import MitreAttackFilterSet


app_name = "mitreattack"

urlpatterns = [
    path(
        "",
        AppIndexView.as_view(title="Mitre Att&ck", app_name=app_name),
        name="index",
    ),
]

VIEWABLE_MODELS_AND_PK_PATTERNS = (
    # [<model>, <pattern>],
    patterns.CAMPAIGN_ID_PATTERN,
    patterns.DATASOURCE_ID_PATTERN,
    patterns.GROUP_ID_PATTERN,
    patterns.MATRIX_ID_PATTERN,
    patterns.MITIGATION_ID_PATTERN,
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
            include(
                produce_paths_for_model(
                    model, regex_pk_pattern.pattern, default_filterset_class=MitreAttackFilterSet
                )
            ),
        ),
    ]


# URLs for prefiltered records by Collection shortname
urlpatterns.extend(
    [
        re_path(
            r"^matrix/(?P<slug>[-a-z/]+)/$",
            views.MatrixDetailView.as_view(),
            name="detail_by_collection",
            model=models.Matrix,
        ),
    ]
)


# Redirect to the correct model view based on the mitre id
urlpatterns.append(
    re_path(
        r"^redirect-id/(?P<mitre_id>[\w.]+)/",
        views.redirect_by_id,
        name="redirect_by_mitre_id",
    )
)
