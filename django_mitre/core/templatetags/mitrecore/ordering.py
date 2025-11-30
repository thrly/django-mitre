from django.template import Library


register = Library()


@register.inclusion_tag("mitrecore/ordering/ordered_table_header.html", takes_context=True)
def ordered_table_header(context, title, field_name):
    """
    Provides a simple way to sort the table data by clicking the header title.
    """
    query_params = context.request.GET
    current_value = query_params.get("order")

    if current_value == field_name:
        sort_order = "asc"
        next_sort_order_value = f"-{field_name}"
    elif current_value == f"-{field_name}":
        sort_order = "desc"
        next_sort_order_value = ""  # nullified
    else:
        sort_order = ""
        next_sort_order_value = field_name  # asc

    context.update(
        {
            "title": title,
            "field_name": field_name,
            "sort_order": sort_order,  # either asc or desc
            "next_sort_order_value": next_sort_order_value,
        }
    )
    return context
