import frappe

def get_pagination_params(default_page_size=15):
    """
    Extracts 'page' and 'limit' from the request and calculates
    limit_start and limit_page_length for database queries.
    """
    page_number = frappe.form_dict.get("page", 1)
    limit = frappe.form_dict.get("limit", default_page_size)

    try:
        page_number = int(page_number)
        if page_number < 1:
            page_number = 1
    except (ValueError, TypeError):
        page_number = 1

    try:
        limit = int(limit)
        if limit < 1:
            limit = default_page_size
    except (ValueError, TypeError):
        limit = default_page_size

    limit_start = (page_number - 1) * limit
    return limit_start, limit

def apply_pagination(kwargs, default_page_size=15):
    """
    Applies pagination parameters to a dictionary of kwargs.
    Useful for frappe.get_all or frappe.get_list.
    """
    limit_start, limit_page_length = get_pagination_params(default_page_size)
    
    # If explicitly passed in kwargs, respect that
    if "limit_start" not in kwargs:
        kwargs["limit_start"] = limit_start
    if "limit_page_length" not in kwargs:
        kwargs["limit_page_length"] = limit_page_length
        
    # Remove large limit_page_length overrides if they exist and aren't explicitly requested
    if kwargs.get("limit_page_length") in [500, 999999] and "limit" not in frappe.form_dict:
         kwargs["limit_page_length"] = limit_page_length
         
    return kwargs
