import frappe

def get_pagination_params(default_page_size=8, page=None, limit=None):
    """
    Extracts 'page' and 'limit' from the request and calculates
    limit_start and limit_page_length for database queries.
    """
    if page is None:
        page = frappe.form_dict.get("page", 1)
    if limit is None:
        limit = frappe.form_dict.get("limit", default_page_size)

    try:
        page_number = int(page)
        if page_number < 1:
            page_number = 1
    except (ValueError, TypeError):
        page_number = 1

    limit_val = limit
    if str(limit_val).lower() == "all" or limit_val == 0:
        limit = None
    else:
        try:
            limit = int(limit_val)
            if limit < 0:
                limit = default_page_size
        except (ValueError, TypeError):
            limit = default_page_size

    limit_start = (page_number - 1) * limit if limit else 0
    return limit_start, limit, page_number

def apply_pagination(kwargs, default_page_size=15, page=None, limit=None):
    """
    Applies pagination parameters to a dictionary of kwargs.
    Useful for frappe.get_all or frappe.get_list.
    """
    limit_start, limit_page_length, page_number = get_pagination_params(default_page_size, page=page, limit=limit)
    
    # If explicitly passed in kwargs, respect that
    if "limit_start" not in kwargs:
        kwargs["limit_start"] = limit_start
    if "limit_page_length" not in kwargs:
        kwargs["limit_page_length"] = limit_page_length
        
    # Remove large limit_page_length overrides if they exist and aren't explicitly requested
    if kwargs.get("limit_page_length") in [500, 999999] and "limit" not in frappe.form_dict and limit is None:
         kwargs["limit_page_length"] = limit_page_length
         
    return kwargs

def get_paginated_data(doctype, **kwargs):
    """
    Executes a database query with pagination and returns the results
    along with pagination metadata (total_pages, total_count, etc.).
    """
    default_page_size = kwargs.pop("default_page_size", 8)
    
    explicit_page = kwargs.pop("page", None)
    if explicit_page is None:
        doctype_key = doctype.replace(" ", "_")
        last_word = doctype.split()[-1]
        explicit_page = (
            frappe.form_dict.get(f"{doctype_key}_page")
            or frappe.form_dict.get(f"{last_word}_page")
            or frappe.form_dict.get("page", 1)
        )
        
    explicit_limit = kwargs.pop("limit", None)
    limit_start, limit_page_length, page_number = get_pagination_params(
        default_page_size, page=explicit_page, limit=explicit_limit
    )
    
    paginated_kwargs = kwargs.copy()
    if "limit_start" not in paginated_kwargs:
        paginated_kwargs["limit_start"] = limit_start
    if "limit_page_length" not in paginated_kwargs:
        paginated_kwargs["limit_page_length"] = limit_page_length
        
    if paginated_kwargs.get("limit_page_length") in [500, 999999] and "limit" not in frappe.form_dict and explicit_limit is None:
        paginated_kwargs["limit_page_length"] = limit_page_length

    data = frappe.get_all(doctype, **paginated_kwargs)
    
    filters = kwargs.get("filters", {})
    or_filters = kwargs.get("or_filters", None)
    try:
        if or_filters:
            total_count = len(frappe.get_all(doctype, filters=filters, or_filters=or_filters, fields=["name"]))
        else:
            total_count = frappe.db.count(doctype, filters=filters)
    except Exception:
        total_count = len(data)
    
    limit = paginated_kwargs.get("limit_page_length")
    total_pages = (total_count + limit - 1) // limit if limit and limit > 0 else 1
    
    if getattr(frappe.local, "response", None) is not None:
        if "pagination" not in frappe.local.response:
            frappe.local.response["pagination"] = {}
        frappe.local.response["pagination"][doctype] = {
            "total_count": total_count,
            "total_pages": total_pages,
            "page": page_number,
            "limit": limit
        }
        # For simple endpoints, set them globally on the response too
        frappe.local.response["total_count"] = total_count
        frappe.local.response["total_pages"] = total_pages
        frappe.local.response["page"] = page_number
        frappe.local.response["limit"] = limit
    
    return data
