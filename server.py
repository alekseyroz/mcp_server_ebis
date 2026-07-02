"""MCP Server for eBis Cloud REST API."""

from base64 import b64encode
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from src.config import BASE_URL, PASSWORD, USERNAME

mcp = FastMCP("eBis Cloud")


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _auth_headers() -> dict[str, str]:
    token = b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def _get(endpoint: str, params: dict | None = None) -> Any:
    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{BASE_URL}/{endpoint}",
            headers=_auth_headers(),
            params=params,
        )
        resp.raise_for_status()
        return resp.json()


def _post(endpoint: str, body: dict) -> Any:
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{BASE_URL}/{endpoint}",
            headers={**_auth_headers(), "Content-Type": "application/json"},
            json=body,
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Work Order tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_workorder_lists(list_name: str | None = None) -> dict:
    """
    Retrieve the supporting reference lists used when filtering work order exports.

    Args:
        list_name: Optional. Name of a specific list to return (e.g. 'CityID').
                   If omitted, all available lists are returned.

    Returns:
        Dict containing reference lists such as CityID with their IDs and Names.
    """
    params = {}
    if list_name:
        params["name"] = list_name
    return _get("workorder/lists", params=params)


@mcp.tool()
def export_workorders(
    city_ids: list[int | str] | None = None,
    completed_dates: list[str] | None = None,
    created_dates: list[str] | None = None,
    include_billing_option: bool = False,
    include_invoice_media: bool = False,
    include_invoice_totals: bool = False,
    include_meter_reading: bool = False,
    include_outside_repair: bool = False,
    include_parts: bool = False,
    include_service: bool = False,
    include_service_logs: bool = False,
    include_signoffs: bool = False,
    include_wo_item_media: bool = False,
    include_wo_media: bool = False,
    hierarchy: str = "flat",
    id_accessible: bool = False,
) -> dict:
    """
    Export detailed work order information from eBis Cloud.

    Includes optional sections: Outside Repair, Signoffs, Service, Media, Parts, Invoices.

    Args:
        city_ids: Filter by city IDs or names, e.g. [1013, 1014, "Denver"].
                  Use get_workorder_lists(list_name='CityID') to find valid values.
        completed_dates: Filter by completion date(s), e.g. ["2024-01-25", "2024-01-26"].
        created_dates: Filter by creation date(s), e.g. ["2024-01-25", "2024-01-26"].
        include_billing_option: Include billing option data.
        include_invoice_media: Include invoice media attachments.
        include_invoice_totals: Include invoice totals.
        include_meter_reading: Include meter reading data.
        include_outside_repair: Include outside repair records.
        include_parts: Include parts records.
        include_service: Include service records.
        include_service_logs: Include service log records (includes technician names).
        include_signoffs: Include PM, QC, SafetyCheck, and SB signoffs.
        include_wo_item_media: Include media attached to individual work order items.
        include_wo_media: Include media attached to the work order.
        hierarchy: Response structure — "flat" (default) or "nested".
                   "flat" flattens all parent/child fields into one row.
                   "nested" preserves the hierarchical structure.
        id_accessible: If True, child lists are returned as object trees keyed
                       by ID rather than as arrays.

    Returns:
        Work order export data matching the requested filters and include options.
    """
    body: dict[str, Any] = {}

    if city_ids is not None:
        body["CityID"] = city_ids
    if completed_dates is not None:
        body["CompletedDate"] = completed_dates
    if created_dates is not None:
        body["CreatedDate"] = created_dates
    if include_billing_option:
        body["IncludeBillingOption"] = True
    if include_invoice_media:
        body["IncludeInvoiceMedia"] = True
    if include_invoice_totals:
        body["IncludeInvoiceTotals"] = True
    if include_meter_reading:
        body["IncludeMeterReading"] = True
    if include_outside_repair:
        body["IncludeOutsideRepair"] = True
    if include_parts:
        body["IncludeParts"] = True
    if include_service:
        body["IncludeService"] = True
    if include_service_logs:
        body["IncludeServiceLogs"] = True
    if include_signoffs:
        body["IncludeSignoffs"] = True
    if include_wo_item_media:
        body["IncludeWoItemMedia"] = True
    if include_wo_media:
        body["IncludeWoMedia"] = True
    if hierarchy != "flat":
        body["Hierarchy"] = hierarchy
    if id_accessible:
        body["IDAccessible"] = True

    return _post("workorder", body)


@mcp.tool()
def get_workorder_addupdate_lists(list_names: list[str] | None = None) -> dict:
    """
    Retrieve the supporting reference lists used when creating or updating a work order.

    Available list names: CityID, CustomerID, AircraftID, BillingProfileID, MeterProfileID.

    Args:
        list_names: Optional list of specific list names to return,
                    e.g. ["CityID", "BillingProfileID"]. If omitted, all lists are returned.

    Returns:
        Dict of requested reference lists, each containing {ID, Name} entries.
    """
    params = {}
    if list_names:
        params["name"] = ",".join(list_names)
    return _get("workorder/addupdate/lists", params=params)


@mcp.tool()
def create_update_workorder(
    # City resolution
    city_id: int | None = None,
    city_abbr: str | None = None,
    create_city_if_not_exists: bool = False,
    default_to_aircraft_city: bool = True,
    # Customer resolution
    customer_id: int | None = None,
    customer_name: str | None = None,
    create_customer_if_not_exists: bool = False,
    default_to_aircraft_primary_customer: bool = True,
    # Aircraft resolution
    aircraft_id: int | None = None,
    reg_num: str | None = None,
    create_aircraft_if_not_exists: bool = False,
    add_customer_to_aircraft_if_not_attached: bool = False,
    # Billing profile resolution
    billing_profile_id: int | None = None,
    billing_profile_name: str | None = None,
    use_any_billing_profile: bool = True,
    # Meter profile (new aircraft only)
    meter_profile_id: int | None = None,
    meter_profile_name: str | None = None,
    use_any_meter_profile: bool = True,
    # Work order content
    items: list[dict] | None = None,
    priority_id: int | None = None,
) -> dict:
    """
    Create or update a work order in eBis Cloud.

    eBis resolves city, customer, billing profile, and aircraft in order before
    creating the work order. Use get_workorder_addupdate_lists() to find valid IDs.

    City resolution (in priority order):
        city_id > city_abbr > default_to_aircraft_city

    Customer resolution (in priority order):
        customer_id > customer_name > default_to_aircraft_primary_customer

    Aircraft resolution (in priority order):
        aircraft_id > reg_num

    Billing profile resolution (in priority order):
        billing_profile_id > billing_profile_name > use_any_billing_profile

    Args:
        city_id: eBis ID for the intended city. Takes priority over city_abbr.
        city_abbr: Identify the city by name/abbreviation. Ignored if city_id is set.
        create_city_if_not_exists: If True and city is not found, create it and continue.
        default_to_aircraft_city: If no city provided, use the aircraft's associated city.
        customer_id: eBis ID for the intended customer. Takes priority over customer_name.
        customer_name: Identify the customer by name. Ignored if customer_id is set.
        create_customer_if_not_exists: If True and customer is not found, create it and continue.
        default_to_aircraft_primary_customer: If no customer provided, use the aircraft's primary customer.
        aircraft_id: eBis ID for the intended aircraft. Takes priority over reg_num.
        reg_num: Identify the aircraft by registration/tail number. Ignored if aircraft_id is set.
        create_aircraft_if_not_exists: If True and aircraft is not found, create it and continue.
        add_customer_to_aircraft_if_not_attached: If True and the customer is not linked to
            the aircraft, associate them and continue. New customers are linked automatically.
        billing_profile_id: eBis ID for the intended billing profile. Takes priority over billing_profile_name.
        billing_profile_name: Identify the billing profile by name. Ignored if billing_profile_id is set.
        use_any_billing_profile: If no billing profile provided, find and attach any available one.
        meter_profile_id: eBis ID for the meter profile — only used when creating a new aircraft.
            Ignored for existing aircraft. Takes priority over meter_profile_name.
        meter_profile_name: Identify the meter profile by name. Ignored if meter_profile_id is set.
            Only applies to new aircraft creation.
        use_any_meter_profile: If no meter profile provided for a new aircraft, find and attach any.
        items: List of work order line items to add. Each item is a dict with:
               - LineNumber (int, optional): Line number.
               - Discrepancy (str): Description of the discrepancy.
               - Notes (str, optional): Additional notes.
        priority_id: eBis ID for the work order priority.

    Returns:
        Dict with Data containing:
        - MessageID / MessageText: "OK" on success, error details otherwise.
        - ID: Created work order ID.
        - EBisWoLink: Direct URL to the work order in eBis.
        - CityID, CityAbbr, CustomerID, CustomerName, AircraftID, RegNum.
        - BillingProfileID, BillingProfileName, MeterProfileID, MeterProfileName.
        - ItemResult: List of created line items with their IDs and discrepancies.
    """
    payload: dict[str, Any] = {}

    if city_id is not None:
        payload["CityID"] = city_id
    if city_abbr is not None:
        payload["CityAbbr"] = city_abbr
    if create_city_if_not_exists:
        payload["CreateCityIfNotExists"] = True
    if not default_to_aircraft_city:
        payload["DefaultToAircraftCity"] = False

    if customer_id is not None:
        payload["CustomerID"] = customer_id
    if customer_name is not None:
        payload["CustomerName"] = customer_name
    if create_customer_if_not_exists:
        payload["CreateCustomerIfNotExists"] = True
    if not default_to_aircraft_primary_customer:
        payload["DefaultToAircraftPrimaryCustomer"] = False

    if aircraft_id is not None:
        payload["AircraftID"] = aircraft_id
    if reg_num is not None:
        payload["RegNum"] = reg_num
    if create_aircraft_if_not_exists:
        payload["CreateAircraftIfNotExists"] = True
    if add_customer_to_aircraft_if_not_attached:
        payload["AddCustomerToAircraftIfNotAttached"] = True

    if billing_profile_id is not None:
        payload["BillingProfileID"] = billing_profile_id
    if billing_profile_name is not None:
        payload["BillingProfileName"] = billing_profile_name
    if not use_any_billing_profile:
        payload["UseAnyBillingProfile"] = False

    if meter_profile_id is not None:
        payload["MeterProfileID"] = meter_profile_id
    if meter_profile_name is not None:
        payload["MeterProfileName"] = meter_profile_name
    if not use_any_meter_profile:
        payload["UseAnyMeterProfile"] = False

    if items:
        payload["Items"] = items
    if priority_id is not None:
        payload["PriorityID"] = priority_id

    return _post("workorder/addupdate", payload)


# ---------------------------------------------------------------------------
# Work Order Totals tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_workorder_totals_lists(list_names: list[str] | None = None) -> dict:
    """
    Retrieve the supporting reference lists used when filtering work order totals.

    Available list names: CityID, CurrencyID, CustomerID, DepartmentID, FleetObjectID,
    MaintainedByID, MakeID, ModelID, RegionID, VehicleTypeID, WoCat1ID, WoCat2ID,
    WoCat3ID, WoDepartmentID, WorkCenterID, WoStatusID, WoTypeID.

    Args:
        list_names: Optional list of specific list names to return,
                    e.g. ["CityID", "CurrencyID"]. If omitted, all lists are returned.

    Returns:
        Dict of requested reference lists, each containing {ID, Name} entries.
    """
    params = {}
    if list_names:
        params["name"] = ",".join(list_names)
    return _get("workorder/totals/lists", params=params)


@mcp.tool()
def get_workorder_totals(
    completed_dates: list[str] | None = None,
    created_dates: list[str] | None = None,
    ac_reg_num: str | None = None,
    ac_serial_no: str | None = None,
    city_ids: list[int | str] | None = None,
    city_nos: list[str] | None = None,
    created_by_username_like: str | None = None,
    currency_ids: list[int | str] | None = None,
    customer_ids: list[int | str] | None = None,
    department_ids: list[int | str] | None = None,
    ebis_ids: list[int] | None = None,
    every_item: bool = False,
    fleet_object_ids: list[int | str] | None = None,
    group_by_invoice: bool = False,
    include_open_wos: bool = False,
    maintained_by_ids: list[int | str] | None = None,
    make_ids: list[int | str] | None = None,
    model_ids: list[int | str] | None = None,
    region_ids: list[int | str] | None = None,
    vehicle_type_ids: list[int | str] | None = None,
    void_work_orders: bool = False,
    wo_cat1_ids: list[int | str] | None = None,
    wo_cat2_ids: list[int | str] | None = None,
    wo_cat3_ids: list[int | str] | None = None,
    wo_corr_action: str | None = None,
    wo_department_ids: list[int | str] | None = None,
    wo_discrep: str | None = None,
    work_center_ids: list[int | str] | None = None,
    work_orders: list[str] | None = None,
    wo_status_ids: list[int | str] | None = None,
    wo_type_ids: list[int | str] | None = None,
    hierarchy: str = "flat",
    id_accessible: bool = False,
    full_debug: bool = False,
    unit_test: bool = False,
) -> dict:
    """
    Retrieve work order totals based on custom criteria.

    Use get_workorder_totals_lists() to discover valid ID/name values for
    any of the ID filter parameters.

    Args:
        completed_dates: Limit to work orders completed within these dates, e.g. ["2024-01-25"].
        created_dates: Limit to work orders created on these dates, e.g. ["2024-01-25"].
        ac_reg_num: Filter by aircraft registration/tail number (exact match).
        ac_serial_no: Filter by aircraft serial number (exact match).
        city_ids: Filter by city IDs or names, e.g. [1013, "Denver"].
        city_nos: Filter by city number strings, e.g. ["C01", "C02"].
        created_by_username_like: Fragment search on the username that created the WO.
        currency_ids: Filter by currency IDs or names.
        customer_ids: Filter by customer IDs or names.
        department_ids: Filter by department IDs or names.
        ebis_ids: Filter by specific eBis internal work order IDs.
        every_item: If True, return a row per line item rather than per work order.
        fleet_object_ids: Filter by fleet object IDs or names.
        group_by_invoice: If True, group totals by invoice.
        include_open_wos: If True, include open (non-completed) work orders.
        maintained_by_ids: Filter by maintained-by organisation IDs or names.
        make_ids: Filter by aircraft make IDs or names.
        model_ids: Filter by aircraft model IDs or names.
        region_ids: Filter by region IDs or names.
        vehicle_type_ids: Filter by vehicle type IDs or names.
        void_work_orders: If True, include voided work orders.
        wo_cat1_ids: Filter by WO Category 1 IDs or names.
        wo_cat2_ids: Filter by WO Category 2 IDs or names.
        wo_cat3_ids: Filter by WO Category 3 IDs or names.
        wo_corr_action: Fragment search on corrective action text.
        wo_department_ids: Filter by WO department IDs or names.
        wo_discrep: Fragment search on discrepancy text.
        work_center_ids: Filter by work center IDs or names.
        work_orders: Filter by work order number strings, e.g. ["WO-1001", "WO-1002"].
        wo_status_ids: Filter by work order status IDs or names.
        wo_type_ids: Filter by work order type IDs or names.
        hierarchy: Response structure — "flat" (default) or "nested".
                   Nested hierarchy: City > Equipment > WorkOrders > Customer/InvoiceTotals/Items.
        id_accessible: If True, child lists are keyed by ID rather than returned as arrays.
        full_debug: Enable full debug output (dev/testing use).
        unit_test: Enable unit test mode (dev/testing use).

    Returns:
        Work order totals matching the requested filters.
    """
    body: dict[str, Any] = {}

    if completed_dates is not None:
        body["CompletedDate"] = completed_dates
    if created_dates is not None:
        body["CreatedDate"] = created_dates
    if ac_reg_num is not None:
        body["AcRegNum"] = ac_reg_num
    if ac_serial_no is not None:
        body["AcSerialNo"] = ac_serial_no
    if city_ids is not None:
        body["CityID"] = city_ids
    if city_nos is not None:
        body["CityNo"] = city_nos
    if created_by_username_like is not None:
        body["CreatedByUsernameLike"] = created_by_username_like
    if currency_ids is not None:
        body["CurrencyID"] = currency_ids
    if customer_ids is not None:
        body["CustomerID"] = customer_ids
    if department_ids is not None:
        body["DepartmentID"] = department_ids
    if ebis_ids is not None:
        body["EBisID"] = ebis_ids
    if every_item:
        body["EveryItem"] = True
    if fleet_object_ids is not None:
        body["FleetObjectID"] = fleet_object_ids
    if group_by_invoice:
        body["GroupByInvoice"] = True
    if include_open_wos:
        body["IncludeOpenWos"] = True
    if maintained_by_ids is not None:
        body["MaintainedByID"] = maintained_by_ids
    if make_ids is not None:
        body["MakeID"] = make_ids
    if model_ids is not None:
        body["ModelID"] = model_ids
    if region_ids is not None:
        body["RegionID"] = region_ids
    if vehicle_type_ids is not None:
        body["VehicleTypeID"] = vehicle_type_ids
    if void_work_orders:
        body["VoidWorkOrders"] = True
    if wo_cat1_ids is not None:
        body["WoCat1ID"] = wo_cat1_ids
    if wo_cat2_ids is not None:
        body["WoCat2ID"] = wo_cat2_ids
    if wo_cat3_ids is not None:
        body["WoCat3ID"] = wo_cat3_ids
    if wo_corr_action is not None:
        body["WoCorrAction"] = wo_corr_action
    if wo_department_ids is not None:
        body["WoDepartmentID"] = wo_department_ids
    if wo_discrep is not None:
        body["WoDiscrep"] = wo_discrep
    if work_center_ids is not None:
        body["WorkCenterID"] = work_center_ids
    if work_orders is not None:
        body["WorkOrder"] = work_orders
    if wo_status_ids is not None:
        body["WoStatusID"] = wo_status_ids
    if wo_type_ids is not None:
        body["WoTypeID"] = wo_type_ids
    if hierarchy != "flat":
        body["Hierarchy"] = hierarchy
    if id_accessible:
        body["IDAccessible"] = True
    if full_debug:
        body["FullDebug"] = True
    if unit_test:
        body["UnitTest"] = True

    return _post("workorder/totals", body)


# ---------------------------------------------------------------------------
# Outside Repair tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_outside_repair_lists(list_names: list[str] | None = None) -> dict:
    """
    Retrieve the supporting reference lists used when filtering outside repair searches.

    Available list names: CityID, CostCenterID, CustomerID, DepartmentID, EngineID,
    IbsID, MakeID, ModelID, RegionID, StatusTypeID, UserStatusID, VehicleTypeID,
    WoActionCategoryID, WoCategoryID, WorkCenterID, WoStatusID, WoSubCategoryID, WoTypeID.

    Args:
        list_names: Optional list of specific list names to return,
                    e.g. ["CityID", "CostCenterID"]. If omitted, all lists are returned.

    Returns:
        Dict of requested reference lists, each containing {ID, Name} entries.
    """
    params = {}
    if list_names:
        params["name"] = ",".join(list_names)
    return _get("workorder/outsiderepair/lists", params=params)


@mcp.tool()
def search_outside_repair(
    completed_dates: list[str] | None = None,
    date_added: list[str] | None = None,
    added_by_user_like: str | None = None,
    all_accessible_cities: bool = False,
    city_ids: list[int | str] | None = None,
    city_no_like: str | None = None,
    cost_center_ids: list[int | str] | None = None,
    customer_ids: list[int | str] | None = None,
    department_ids: list[int | str] | None = None,
    engine1_serial: str | None = None,
    engine_ids: list[int | str] | None = None,
    ibs_ids: list[int | str] | None = None,
    make_ids: list[int | str] | None = None,
    model_ids: list[int | str] | None = None,
    output_only_detail: bool = False,
    part_description: str | None = None,
    part_number: str | None = None,
    region_ids: list[int | str] | None = None,
    reg_nums: list[str] | None = None,
    serial_no: str | None = None,
    show_deleted_only: bool = False,
    status_type_id: int | str | None = None,
    user_status_ids: list[int | str] | None = None,
    vehicle_type_abbrs: list[str] | None = None,
    vehicle_type_ids: list[int | str] | None = None,
    vendor_name: str | None = None,
    vin: str | None = None,
    wo_action_category_ids: list[int | str] | None = None,
    wo_category_ids: list[int | str] | None = None,
    work_center_ids: list[int | str] | None = None,
    work_order_like: str | None = None,
    wo_status_ids: list[int | str] | None = None,
    wo_sub_category_ids: list[int | str] | None = None,
    wo_type_ids: list[int | str] | None = None,
    year_built: list[int] | None = None,
    hierarchy: str = "flat",
    id_accessible: bool = False,
    language: str | None = None,
) -> dict:
    """
    Search outside repair items based on custom criteria.

    Use get_outside_repair_lists() to discover valid ID/name values for
    any of the ID filter parameters.

    Args:
        completed_dates: Limit to work orders completed within these dates, e.g. ["2024-01-25"].
        date_added: Filter by the date the outside repair was added, e.g. ["2024-01-25"].
        added_by_user_like: Fragment search on the username that added the outside repair.
        all_accessible_cities: If True, include all cities accessible to the user.
        city_ids: Filter by city IDs or names.
        city_no_like: Fragment search on city number.
        cost_center_ids: Filter by cost center IDs or names.
        customer_ids: Filter by customer IDs or names.
        department_ids: Filter by department IDs or names.
        engine1_serial: Fragment search on engine 1 serial number.
        engine_ids: Filter by engine IDs or names.
        ibs_ids: Filter by IBS IDs or names.
        make_ids: Filter by aircraft make IDs or names.
        model_ids: Filter by aircraft model IDs or names.
        output_only_detail: If True, output only detail-level records.
        part_description: Fragment search on part description.
        part_number: Fragment search on part number.
        region_ids: Filter by region IDs or names.
        reg_nums: Filter by aircraft registration/tail numbers, e.g. ["N12345", "N67890"].
        serial_no: Fragment search on aircraft serial number.
        show_deleted_only: If True, return only deleted outside repair records.
        status_type_id: Filter by a single status type ID or name.
        user_status_ids: Filter by user status IDs or names.
        vehicle_type_abbrs: Filter by vehicle type abbreviations, e.g. ["HEL", "FW"].
        vehicle_type_ids: Filter by vehicle type IDs or names.
        vendor_name: Fragment search on vendor name.
        vin: Fragment search on VIN.
        wo_action_category_ids: Filter by WO action category IDs or names.
        wo_category_ids: Filter by WO category IDs or names.
        work_center_ids: Filter by work center IDs or names.
        work_order_like: Fragment search on work order number.
        wo_status_ids: Filter by work order status IDs or names.
        wo_sub_category_ids: Filter by WO sub-category IDs or names.
        wo_type_ids: Filter by work order type IDs or names.
        year_built: Filter by aircraft year(s) built, e.g. [2001, 2002].
        hierarchy: Response structure — "flat" (default) or "nested".
                   Nested hierarchy: WorkOrders > Items > OutsideRepair.
        id_accessible: If True, child lists are keyed by ID rather than returned as arrays.
        language: Language for generic list parameter lookups (default: "English").

    Returns:
        Outside repair records matching the requested filters.
    """
    body: dict[str, Any] = {}

    if completed_dates is not None:
        body["CompletedDate"] = completed_dates
    if date_added is not None:
        body["DateAdded"] = date_added
    if added_by_user_like is not None:
        body["AddedByUserLike"] = added_by_user_like
    if all_accessible_cities:
        body["AllAccessibleCities"] = True
    if city_ids is not None:
        body["CityID"] = city_ids
    if city_no_like is not None:
        body["CityNoLike"] = city_no_like
    if cost_center_ids is not None:
        body["CostCenterID"] = cost_center_ids
    if customer_ids is not None:
        body["CustomerID"] = customer_ids
    if department_ids is not None:
        body["DepartmentID"] = department_ids
    if engine1_serial is not None:
        body["Engine1Serial"] = engine1_serial
    if engine_ids is not None:
        body["EngineID"] = engine_ids
    if ibs_ids is not None:
        body["IbsID"] = ibs_ids
    if make_ids is not None:
        body["MakeID"] = make_ids
    if model_ids is not None:
        body["ModelID"] = model_ids
    if output_only_detail:
        body["OutputOnlyDetail"] = True
    if part_description is not None:
        body["PartDescription"] = part_description
    if part_number is not None:
        body["PartNumber"] = part_number
    if region_ids is not None:
        body["RegionID"] = region_ids
    if reg_nums is not None:
        body["RegNum"] = reg_nums
    if serial_no is not None:
        body["SerialNo"] = serial_no
    if show_deleted_only:
        body["ShowDeletedOnly"] = True
    if status_type_id is not None:
        body["StatusTypeID"] = status_type_id
    if user_status_ids is not None:
        body["UserStatusID"] = user_status_ids
    if vehicle_type_abbrs is not None:
        body["VehicleTypeAbbr"] = vehicle_type_abbrs
    if vehicle_type_ids is not None:
        body["VehicleTypeID"] = vehicle_type_ids
    if vendor_name is not None:
        body["VendorName"] = vendor_name
    if vin is not None:
        body["Vin"] = vin
    if wo_action_category_ids is not None:
        body["WoActionCategoryID"] = wo_action_category_ids
    if wo_category_ids is not None:
        body["WoCategoryID"] = wo_category_ids
    if work_center_ids is not None:
        body["WorkCenterID"] = work_center_ids
    if work_order_like is not None:
        body["WorkOrderLike"] = work_order_like
    if wo_status_ids is not None:
        body["WoStatusID"] = wo_status_ids
    if wo_sub_category_ids is not None:
        body["WoSubCategoryID"] = wo_sub_category_ids
    if wo_type_ids is not None:
        body["WoTypeID"] = wo_type_ids
    if year_built is not None:
        body["YearBuilt"] = year_built
    if hierarchy != "flat":
        body["Hierarchy"] = hierarchy
    if id_accessible:
        body["IDAccessible"] = True
    if language is not None:
        body["Language"] = language

    return _post("workorder/outsiderepair", body)


# ---------------------------------------------------------------------------
# Work Order Listing tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_workorder_listing_lists(list_names: list[str] | None = None) -> dict:
    """
    Retrieve the supporting reference lists used when querying work order listings.

    Available list names: CityGroupID, CityID, CustomerID, EngineID, MaintainedByID,
    MakeID, ModelID, PmDocID, RegionID, SortByID, VehicleTypeID, WoActionCategoryID,
    WoCategoryID, WorkCenterID, WoStatusID, WoSubCategoryID, WoTypeID, ZoneID.

    Args:
        list_names: Optional list of specific list names to return,
                    e.g. ["CityGroupID", "WoStatusID"]. If omitted, all lists are returned.

    Returns:
        Dict of requested reference lists, each containing {ID, Name} entries.
    """
    params = {}
    if list_names:
        params["name"] = ",".join(list_names)
    return _get("workorder/listing/lists", params=params)


@mcp.tool()
def get_workorder_listing(
    wo_status_id: int | str,
    wo_type_id: int | str,
    city_group_ids: list[int | str] | None = None,
    city_ids: list[int | str] | None = None,
    city_no: str | None = None,
    completed_dates: list[str] | None = None,
    created_dates: list[str] | None = None,
    customer_ids: list[int | str] | None = None,
    detailed_export: bool = False,
    due_dates: list[str] | None = None,
    engine_ids: list[int | str] | None = None,
    export_all_items: bool = False,
    export_invoice_totals: bool = False,
    has_customer_po: str | None = None,
    maintained_by_ids: list[int | str] | None = None,
    make_ids: list[int | str] | None = None,
    model_ids: list[int | str] | None = None,
    pm_doc_ids: list[int | str] | None = None,
    region_ids: list[int | str] | None = None,
    sort_by_id: int | str | None = None,
    vehicle_type_ids: list[int | str] | None = None,
    wo_action_category_ids: list[int | str] | None = None,
    wo_category_ids: list[int | str] | None = None,
    work_center_ids: list[int | str] | None = None,
    wo_sub_category_ids: list[int | str] | None = None,
    zone_ids: list[int | str] | None = None,
    hierarchy: str = "flat",
    id_accessible: bool = False,
    language: str | None = None,
) -> dict:
    """
    Retrieve work order listing information based on custom criteria.

    Use get_workorder_listing_lists() to discover valid ID/name values for
    any of the ID filter parameters.

    Args:
        wo_status_id: (Required) Work order status ID or name, e.g. 101 or "Open".
        wo_type_id: (Required) Work order type ID or name, e.g. 101 or "Scheduled".
        city_group_ids: Filter by city group IDs or names.
        city_ids: Filter by city IDs or names.
        city_no: Fragment search on city number.
        completed_dates: Filter by completion date(s), e.g. ["2024-01-25"].
        created_dates: Filter by creation date(s), e.g. ["2024-01-25"].
        customer_ids: Filter by customer IDs or names.
        detailed_export: If True, include detailed line-item data in the export.
        due_dates: Filter by due date(s), e.g. ["2024-01-25"].
        engine_ids: Filter by engine IDs or names.
        export_all_items: If True, export all work order items regardless of status.
        export_invoice_totals: If True, include invoice totals in the export.
        has_customer_po: Filter by customer PO presence — "yes", "no", or "all".
        maintained_by_ids: Filter by maintained-by organisation IDs or names.
        make_ids: Filter by aircraft make IDs or names.
        model_ids: Filter by aircraft model IDs or names.
        pm_doc_ids: Filter by PM document IDs or names.
        region_ids: Filter by region IDs or names.
        sort_by_id: Sort results by this field ID or name.
        vehicle_type_ids: Filter by vehicle type IDs or names.
        wo_action_category_ids: Filter by WO action category IDs or names.
        wo_category_ids: Filter by WO category IDs or names.
        work_center_ids: Filter by work center IDs or names.
        wo_sub_category_ids: Filter by WO sub-category IDs or names.
        zone_ids: Filter by zone IDs or names.
        hierarchy: Response structure — only "flat" is supported for this endpoint.
        id_accessible: If True, child lists are keyed by ID rather than returned as arrays.
        language: Language for generic list parameter lookups (default: "English").

    Returns:
        Work order listing records matching the requested filters.
    """
    body: dict[str, Any] = {
        "WoStatusID": wo_status_id,
        "WoTypeID": wo_type_id,
    }

    if city_group_ids is not None:
        body["CityGroupID"] = city_group_ids
    if city_ids is not None:
        body["CityID"] = city_ids
    if city_no is not None:
        body["CityNo"] = city_no
    if completed_dates is not None:
        body["CompletedDate"] = completed_dates
    if created_dates is not None:
        body["CreatedDate"] = created_dates
    if customer_ids is not None:
        body["CustomerID"] = customer_ids
    if detailed_export:
        body["DetailedExport"] = True
    if due_dates is not None:
        body["DueDate"] = due_dates
    if engine_ids is not None:
        body["EngineID"] = engine_ids
    if export_all_items:
        body["ExportAllItems"] = True
    if export_invoice_totals:
        body["ExportInvoiceTotals"] = True
    if has_customer_po is not None:
        body["HasCustomerPo"] = has_customer_po
    if maintained_by_ids is not None:
        body["MaintainedByID"] = maintained_by_ids
    if make_ids is not None:
        body["MakeID"] = make_ids
    if model_ids is not None:
        body["ModelID"] = model_ids
    if pm_doc_ids is not None:
        body["PmDocID"] = pm_doc_ids
    if region_ids is not None:
        body["RegionID"] = region_ids
    if sort_by_id is not None:
        body["SortByID"] = sort_by_id
    if vehicle_type_ids is not None:
        body["VehicleTypeID"] = vehicle_type_ids
    if wo_action_category_ids is not None:
        body["WoActionCategoryID"] = wo_action_category_ids
    if wo_category_ids is not None:
        body["WoCategoryID"] = wo_category_ids
    if work_center_ids is not None:
        body["WorkCenterID"] = work_center_ids
    if wo_sub_category_ids is not None:
        body["WoSubCategoryID"] = wo_sub_category_ids
    if zone_ids is not None:
        body["ZoneID"] = zone_ids
    if hierarchy != "flat":
        body["Hierarchy"] = hierarchy
    if id_accessible:
        body["IDAccessible"] = True
    if language is not None:
        body["Language"] = language

    return _post("workorder/listing", body)


# ---------------------------------------------------------------------------
# Work Order Compliance tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_workorder_compliance_lists(list_names: list[str] | None = None) -> dict:
    """
    Retrieve the supporting reference lists used when querying work order compliance.

    Available list names: CityID, CustomerID, MaintainedByID, RegionID,
    SummaryGroupByID, WorkCenterID, ZoneID.

    Args:
        list_names: Optional list of specific list names to return,
                    e.g. ["CityID", "SummaryGroupByID"]. If omitted, all lists are returned.

    Returns:
        Dict of requested reference lists, each containing {ID, Name} entries.
    """
    params = {}
    if list_names:
        params["name"] = ",".join(list_names)
    return _get("workorder/compliance/lists", params=params)


@mcp.tool()
def get_workorder_compliance(
    summary_group_by_id: int | str,
    city_ids: list[int | str] | None = None,
    completed_dates: list[str] | None = None,
    customer_ids: list[int | str] | None = None,
    due_dates: list[str] | None = None,
    maintained_by_ids: list[int | str] | None = None,
    region_ids: list[int | str] | None = None,
    show_unassigned_workcenter: bool = False,
    work_center_ids: list[int | str] | None = None,
    zone_ids: list[int | str] | None = None,
    id_accessible: bool = False,
    language: str | None = None,
) -> dict:
    """
    Retrieve compliance information about whether work orders are created on time.

    Use get_workorder_compliance_lists() to discover valid ID/name values for
    any of the ID filter parameters.

    Args:
        summary_group_by_id: (Required) Field to group the compliance summary by,
                             e.g. 101 or "WorkCenter". Use get_workorder_compliance_lists()
                             with list_names=["SummaryGroupByID"] to see options.
        city_ids: Filter by city IDs or names.
        completed_dates: Filter by work order completion date(s), e.g. ["2024-01-25"].
        customer_ids: Filter by customer IDs or names.
        due_dates: Filter by work order due date(s), e.g. ["2024-01-25"].
        maintained_by_ids: Filter by maintained-by organisation IDs or names.
        region_ids: Filter by region IDs or names.
        show_unassigned_workcenter: If True, include work orders with no assigned work center.
        work_center_ids: Filter by work center IDs or names.
        zone_ids: Filter by zone IDs or names.
        id_accessible: If True, child lists are keyed by ID rather than returned as arrays.
        language: Language for generic list parameter lookups (default: "English").

    Returns:
        Compliance records indicating whether work orders were created on time,
        grouped by the specified summary field.
    """
    body: dict[str, Any] = {
        "SummaryGroupByID": summary_group_by_id,
    }

    if city_ids is not None:
        body["CityID"] = city_ids
    if completed_dates is not None:
        body["CompletedDate"] = completed_dates
    if customer_ids is not None:
        body["CustomerID"] = customer_ids
    if due_dates is not None:
        body["DueDate"] = due_dates
    if maintained_by_ids is not None:
        body["MaintainedByID"] = maintained_by_ids
    if region_ids is not None:
        body["RegionID"] = region_ids
    if show_unassigned_workcenter:
        body["ShowUnassignedWorkcenter"] = True
    if work_center_ids is not None:
        body["WorkCenterID"] = work_center_ids
    if zone_ids is not None:
        body["ZoneID"] = zone_ids
    if id_accessible:
        body["IDAccessible"] = True
    if language is not None:
        body["Language"] = language

    return _post("workorder/compliance", body)


# ---------------------------------------------------------------------------
# Work Order Part History tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_part_history_lists(list_names: list[str] | None = None) -> dict:
    """
    Retrieve the supporting reference lists used when querying work order part history.

    Available list names: CityID, CostCenterID, CustomerID, DepartmentID, Engine1ID,
    IbsID, Make1ID, Model1ID, PartComponentID, PartTypeID, RegionID, StatusTypeID,
    UserStatusID, VehicleTypeID, WoActionCategoryID, WoCategoryID, WoEbisMainTypeID,
    WorkCenterID, WoStatusID, WoSubCategoryID, WoTypeID.

    Args:
        list_names: Optional list of specific list names to return,
                    e.g. ["CityID", "PartTypeID"]. If omitted, all lists are returned.

    Returns:
        Dict of requested reference lists, each containing {ID, Name} entries.
    """
    params = {}
    if list_names:
        params["name"] = ",".join(list_names)
    return _get("workorder/parthistory/lists", params=params)


@mcp.tool()
def get_part_history(
    added_by_user_like: str | None = None,
    all_accessible_cities: bool = False,
    city_ids: list[int | str] | None = None,
    city_no_like: str | None = None,
    completed_dates: list[str] | None = None,
    cost_center_ids: list[int | str] | None = None,
    customer_ids: list[int | str] | None = None,
    date_added: list[str] | None = None,
    date_used: list[str] | None = None,
    department_ids: list[int | str] | None = None,
    engine1_ids: list[int | str] | None = None,
    engine1_serial: str | None = None,
    ibs_ids: list[int | str] | None = None,
    line_code: str | None = None,
    make1_ids: list[int | str] | None = None,
    model1_ids: list[int | str] | None = None,
    part_component_ids: list[int | str] | None = None,
    part_description: str | None = None,
    part_number: str | None = None,
    parts_not_in_master_parts: bool = False,
    parts_with_serial_numbers: bool = False,
    part_type_ids: list[int | str] | None = None,
    region_ids: list[int | str] | None = None,
    reg_nums: list[str] | None = None,
    serial_no: str | None = None,
    show_deleted_only: bool = False,
    status_type_id: int | str | None = None,
    user_status_ids: list[int | str] | None = None,
    vehicle_type_abbrs: list[str] | None = None,
    vehicle_type_ids: list[int | str] | None = None,
    vin: str | None = None,
    wo_action_category_ids: list[int | str] | None = None,
    wo_category_ids: list[int | str] | None = None,
    wo_date_created: list[str] | None = None,
    wo_ebis_main_type_ids: list[int | str] | None = None,
    work_center_ids: list[int | str] | None = None,
    work_order_like: str | None = None,
    wo_status_ids: list[int | str] | None = None,
    wo_sub_category_ids: list[int | str] | None = None,
    wo_type_ids: list[int | str] | None = None,
    year_built: list[int] | None = None,
    id_accessible: bool = False,
    language: str | None = None,
) -> dict:
    """
    Retrieve work order part usage history based on custom criteria.

    Use get_part_history_lists() to discover valid ID/name values for
    any of the ID filter parameters.

    Args:
        added_by_user_like: Fragment search on the username that added the part record.
        all_accessible_cities: If True, include all cities accessible to the user.
        city_ids: Filter by city IDs or names.
        city_no_like: Fragment search on city number.
        completed_dates: Filter by work order completion date(s), e.g. ["2024-01-25"].
        cost_center_ids: Filter by cost center IDs or names.
        customer_ids: Filter by customer IDs or names.
        date_added: Filter by the date the part was added, e.g. ["2024-01-25"].
        date_used: Filter by the date the part was used, e.g. ["2024-01-25"].
        department_ids: Filter by department IDs or names.
        engine1_ids: Filter by primary engine IDs or names.
        engine1_serial: Fragment search on primary engine serial number.
        ibs_ids: Filter by IBS IDs or names.
        line_code: Fragment search on part line code.
        make1_ids: Filter by aircraft make IDs or names.
        model1_ids: Filter by aircraft model IDs or names.
        part_component_ids: Filter by part component IDs or names.
        part_description: Fragment search on part description.
        part_number: Fragment search on part number.
        parts_not_in_master_parts: If True, return only parts not found in master parts list.
        parts_with_serial_numbers: If True, return only parts that have serial numbers.
        part_type_ids: Filter by part type IDs or names.
        region_ids: Filter by region IDs or names.
        reg_nums: Filter by aircraft registration/tail numbers, e.g. ["N12345"].
        serial_no: Fragment search on aircraft serial number.
        show_deleted_only: If True, return only deleted part history records.
        status_type_id: Filter by a single status type ID or name.
        user_status_ids: Filter by user status IDs or names.
        vehicle_type_abbrs: Filter by vehicle type abbreviations, e.g. ["HEL", "FW"].
        vehicle_type_ids: Filter by vehicle type IDs or names.
        vin: Fragment search on VIN.
        wo_action_category_ids: Filter by WO action category IDs or names.
        wo_category_ids: Filter by WO category IDs or names.
        wo_date_created: Filter by work order creation date(s), e.g. ["2024-01-25"].
        wo_ebis_main_type_ids: Filter by eBis main type IDs or names.
        work_center_ids: Filter by work center IDs or names.
        work_order_like: Fragment search on work order number.
        wo_status_ids: Filter by work order status IDs or names.
        wo_sub_category_ids: Filter by WO sub-category IDs or names.
        wo_type_ids: Filter by work order type IDs or names.
        year_built: Filter by aircraft year(s) built, e.g. [2001, 2002].
        id_accessible: If True, child lists are keyed by ID rather than returned as arrays.
        language: Language for generic list parameter lookups (default: "English").

    Returns:
        Part history records matching the requested filters.
    """
    body: dict[str, Any] = {}

    if added_by_user_like is not None:
        body["AddedByUserLike"] = added_by_user_like
    if all_accessible_cities:
        body["AllAccessibleCities"] = True
    if city_ids is not None:
        body["CityID"] = city_ids
    if city_no_like is not None:
        body["CityNoLike"] = city_no_like
    if completed_dates is not None:
        body["CompletedDate"] = completed_dates
    if cost_center_ids is not None:
        body["CostCenterID"] = cost_center_ids
    if customer_ids is not None:
        body["CustomerID"] = customer_ids
    if date_added is not None:
        body["DateAdded"] = date_added
    if date_used is not None:
        body["DateUsed"] = date_used
    if department_ids is not None:
        body["DepartmentID"] = department_ids
    if engine1_ids is not None:
        body["Engine1ID"] = engine1_ids
    if engine1_serial is not None:
        body["Engine1Serial"] = engine1_serial
    if ibs_ids is not None:
        body["IbsID"] = ibs_ids
    if line_code is not None:
        body["LineCode"] = line_code
    if make1_ids is not None:
        body["Make1ID"] = make1_ids
    if model1_ids is not None:
        body["Model1ID"] = model1_ids
    if part_component_ids is not None:
        body["PartComponentID"] = part_component_ids
    if part_description is not None:
        body["PartDescription"] = part_description
    if part_number is not None:
        body["PartNumber"] = part_number
    if parts_not_in_master_parts:
        body["PartsNotInMasterParts"] = True
    if parts_with_serial_numbers:
        body["PartsWithSerialNumbers"] = True
    if part_type_ids is not None:
        body["PartTypeID"] = part_type_ids
    if region_ids is not None:
        body["RegionID"] = region_ids
    if reg_nums is not None:
        body["RegNum"] = reg_nums
    if serial_no is not None:
        body["SerialNo"] = serial_no
    if show_deleted_only:
        body["ShowDeletedOnly"] = True
    if status_type_id is not None:
        body["StatusTypeID"] = status_type_id
    if user_status_ids is not None:
        body["UserStatusID"] = user_status_ids
    if vehicle_type_abbrs is not None:
        body["VehicleTypeAbbr"] = vehicle_type_abbrs
    if vehicle_type_ids is not None:
        body["VehicleTypeID"] = vehicle_type_ids
    if vin is not None:
        body["Vin"] = vin
    if wo_action_category_ids is not None:
        body["WoActionCategoryID"] = wo_action_category_ids
    if wo_category_ids is not None:
        body["WoCategoryID"] = wo_category_ids
    if wo_date_created is not None:
        body["WoDateCreated"] = wo_date_created
    if wo_ebis_main_type_ids is not None:
        body["WoEbisMainTypeID"] = wo_ebis_main_type_ids
    if work_center_ids is not None:
        body["WorkCenterID"] = work_center_ids
    if work_order_like is not None:
        body["WorkOrderLike"] = work_order_like
    if wo_status_ids is not None:
        body["WoStatusID"] = wo_status_ids
    if wo_sub_category_ids is not None:
        body["WoSubCategoryID"] = wo_sub_category_ids
    if wo_type_ids is not None:
        body["WoTypeID"] = wo_type_ids
    if year_built is not None:
        body["YearBuilt"] = year_built
    if id_accessible:
        body["IDAccessible"] = True
    if language is not None:
        body["Language"] = language

    return _post("workorder/parthistory", body)


# ---------------------------------------------------------------------------
# Work Order Tech Activity tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_tech_activity_lists(list_names: list[str] | None = None) -> dict:
    """
    Retrieve the supporting reference lists used when querying technician activity.

    Available list names: TechGroupID.

    Args:
        list_names: Optional list of specific list names to return,
                    e.g. ["TechGroupID"]. If omitted, all lists are returned.

    Returns:
        Dict of requested reference lists, each containing {ID, Name} entries.
    """
    params = {}
    if list_names:
        params["name"] = ",".join(list_names)
    return _get("workorder/techactivity/lists", params=params)


@mcp.tool()
def get_tech_activity(
    dates: list[str],
    city_ids: list[int | str] | None = None,
    tech_group_ids: list[int | str] | None = None,
    technician_ids: list[int | str] | None = None,
    id_accessible: bool = False,
    full_debug: bool = False,
) -> dict:
    """
    Retrieve detailed logs of technician activity on work orders.

    Use get_tech_activity_lists() to discover valid TechGroupID values.

    Args:
        dates: (Required) One or more dates to query activity for, e.g. ["2024-01-25", "2024-01-26"].
        city_ids: Filter by city IDs or names. Submit [-1] to include all accessible cities.
        tech_group_ids: Filter by technician group IDs or names.
        technician_ids: Filter by individual technician IDs or names.
        id_accessible: If True, child lists are keyed by ID rather than returned as arrays.
        full_debug: Enable full debug output (dev/testing use).

    Returns:
        Technician activity log records for the requested dates and filters.
    """
    body: dict[str, Any] = {
        "Date": dates,
    }

    if city_ids is not None:
        body["CityID"] = city_ids
    if tech_group_ids is not None:
        body["TechGroupID"] = tech_group_ids
    if technician_ids is not None:
        body["TechnicianID"] = technician_ids
    if id_accessible:
        body["IDAccessible"] = True
    if full_debug:
        body["FullDebug"] = True

    return _post("workorder/techactivity", body)


# ---------------------------------------------------------------------------
# Resync Billing And Tax tool
# ---------------------------------------------------------------------------

@mcp.tool()
def resync_billing_and_tax(
    wo_id_list: list[int],
    full_debug: bool = False,
) -> dict:
    """
    Resynchronize billing, tax, and invoice information for one or more work orders.

    Args:
        wo_id_list: (Required) List of work order IDs to resync, e.g. [111, 234, 399].
        full_debug: Enable full debug output (dev/testing use).

    Returns:
        Result of the billing/tax resync operation for the specified work orders.
    """
    body: dict[str, Any] = {
        "WoIDList": wo_id_list,
    }

    if full_debug:
        body["FullDebug"] = True

    return _post("workorder/billingresync", body)


# ---------------------------------------------------------------------------
# Over The Counter (OTC) tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_otc_listing_lists(list_names: list[str] | None = None) -> dict:
    """
    Retrieve the supporting reference lists used when querying OTC listings.

    Available list names: EBisMainTypeID, CityID, StatusID, CustomerID, TypeID, DepartmentID.

    Args:
        list_names: Optional list of specific list names to return,
                    e.g. ["EBisMainTypeID", "CityID"]. If omitted, all lists are returned.

    Returns:
        Dict of requested reference lists, each containing {ID, Name} entries.
        EBisMainTypeID values: 1=Quote, 2=Invoice, 3=CoreInvoice.
    """
    params = {}
    if list_names:
        params["name"] = ",".join(list_names)
    return _get("otc/listing/lists", params=params)


@mcp.tool()
def get_otc_listing(
    ebis_main_type_ids: list[int | str] | None = None,
    back_order_is: str | None = None,
    return_is: str | None = None,
    original_quote_number: str | None = None,
    reminder_due_next_days: int | None = None,
    filter_text: str | None = None,
    include_parts: bool = False,
    include_misc_charges: bool = False,
    otc_id: int | None = None,
    city_ids: list[int | str] | None = None,
    status_ids: list[int | str] | None = None,
    customer_ids: list[int | str] | None = None,
    type_ids: list[int | str] | None = None,
    department_ids: list[int | str] | None = None,
    show_mine_only: bool = False,
    accounting_invoice_num: str | None = None,
    buyer_contact: str | None = None,
    buyer_purchase_order: str | None = None,
    created_dates: list[str] | None = None,
    display_dates: list[str] | None = None,
    est_ship_dates: list[str] | None = None,
    has_media: str | None = None,
    has_misc_charges: str | None = None,
    misc_charge: str | None = None,
    notes: str | None = None,
    part_description: str | None = None,
    part_number: str | None = None,
    part_serial_no: str | None = None,
    payment_due_dates: list[str] | None = None,
    processed_dates: list[str] | None = None,
    shipped_dates: list[str] | None = None,
    tracking_number: str | None = None,
    rpt_sort: str | None = None,
    hierarchy: str = "nested",
    id_accessible: bool = False,
    language: str | None = None,
    debug_sql: bool = False,
) -> dict:
    """
    Retrieve items and totals for over-the-counter (OTC) transactions.

    OTC records include Quotes, Invoices, and Core Invoices.
    Use get_otc_listing_lists() to discover valid ID/name values for ID filter parameters.

    Args:
        ebis_main_type_ids: Filter by transaction type IDs or names.
                            1=Quote, 2=Invoice, 3=CoreInvoice.
        back_order_is: Filter by back order status — "yes", "no", or "all".
        return_is: Filter by return status — "yes", "no", or "all".
        original_quote_number: Fragment search — find an invoice by its originating quote number.
        reminder_due_next_days: Return records with a reminder date within the next N days.
        filter_text: General text filter applied across the listing.
        include_parts: If True, include parts line items in the response.
        include_misc_charges: If True, include miscellaneous charges in the response.
        otc_id: Return a single OTC record by its eBis ID.
        city_ids: Filter by city IDs or names.
        status_ids: Filter by OTC status IDs or names.
        customer_ids: Filter by customer IDs or names.
        type_ids: Filter by OTC type IDs or names.
        department_ids: Filter by department IDs or names.
        show_mine_only: If True, return only records created by the authenticated user.
        accounting_invoice_num: Fragment search on accounting invoice number.
        buyer_contact: Fragment search on buyer contact name.
        buyer_purchase_order: Fragment search on buyer purchase order number.
        created_dates: Filter by creation date(s), e.g. ["2024-01-25"].
        display_dates: Filter by display date(s), e.g. ["2024-01-25"].
        est_ship_dates: Filter by estimated ship date(s), e.g. ["2024-01-25"].
        has_media: Filter by media presence — "yes", "no", or "all".
        has_misc_charges: Filter by misc charge presence — "yes", "no", or "all".
        misc_charge: Fragment search on miscellaneous charge description.
        notes: Fragment search on notes text.
        part_description: Fragment search on part description.
        part_number: Fragment search on part number.
        part_serial_no: Fragment search on part serial number.
        payment_due_dates: Filter by payment due date(s), e.g. ["2024-01-25"].
        processed_dates: Filter by processed date(s), e.g. ["2024-01-25"].
        shipped_dates: Filter by shipped date(s), e.g. ["2024-01-25"].
        tracking_number: Fragment search on shipping tracking number.
        rpt_sort: Sort order for the report output.
        hierarchy: Response structure — "nested" (default) or "flat".
                   Nested hierarchy: Otc > Parts, MiscCharges.
        id_accessible: If True, child lists are keyed by ID rather than returned as arrays.
        language: Language for generic list parameter lookups (default: "English").
        debug_sql: Enable SQL debug output (dev/testing use).

    Returns:
        OTC listing records matching the requested filters, optionally including
        parts and miscellaneous charges.
    """
    body: dict[str, Any] = {}

    if ebis_main_type_ids is not None:
        body["EBisMainTypeID"] = ebis_main_type_ids
    if back_order_is is not None:
        body["BackOrderIs"] = back_order_is
    if return_is is not None:
        body["ReturnIs"] = return_is
    if original_quote_number is not None:
        body["OriginalQuoteNumber"] = original_quote_number
    if reminder_due_next_days is not None:
        body["ReminderDueNextDays"] = reminder_due_next_days
    if filter_text is not None:
        body["FilterText"] = filter_text
    if include_parts:
        body["IncludeParts"] = True
    if include_misc_charges:
        body["IncludeMiscCharges"] = True
    if otc_id is not None:
        body["OtcID"] = otc_id
    if city_ids is not None:
        body["CityID"] = city_ids
    if status_ids is not None:
        body["StatusID"] = status_ids
    if customer_ids is not None:
        body["CustomerID"] = customer_ids
    if type_ids is not None:
        body["TypeID"] = type_ids
    if department_ids is not None:
        body["DepartmentID"] = department_ids
    if show_mine_only:
        body["ShowMineOnly"] = True
    if accounting_invoice_num is not None:
        body["AccountingInvoiceNum"] = accounting_invoice_num
    if buyer_contact is not None:
        body["BuyerContact"] = buyer_contact
    if buyer_purchase_order is not None:
        body["BuyerPurchaseOrder"] = buyer_purchase_order
    if created_dates is not None:
        body["CreatedDate"] = created_dates
    if display_dates is not None:
        body["DisplayDate"] = display_dates
    if est_ship_dates is not None:
        body["EstShipDate"] = est_ship_dates
    if has_media is not None:
        body["HasMedia"] = has_media
    if has_misc_charges is not None:
        body["HasMiscCharges"] = has_misc_charges
    if misc_charge is not None:
        body["MiscCharge"] = misc_charge
    if notes is not None:
        body["Notes"] = notes
    if part_description is not None:
        body["PartDescription"] = part_description
    if part_number is not None:
        body["PartNumber"] = part_number
    if part_serial_no is not None:
        body["PartSerialNo"] = part_serial_no
    if payment_due_dates is not None:
        body["PaymentDueDate"] = payment_due_dates
    if processed_dates is not None:
        body["ProcessedDate"] = processed_dates
    if shipped_dates is not None:
        body["ShippedDate"] = shipped_dates
    if tracking_number is not None:
        body["TrackingNumber"] = tracking_number
    if rpt_sort is not None:
        body["RptSort"] = rpt_sort
    if hierarchy != "nested":
        body["Hierarchy"] = hierarchy
    if id_accessible:
        body["IDAccessible"] = True
    if language is not None:
        body["Language"] = language
    if debug_sql:
        body["DebugSql"] = True

    return _post("otc/listing", body)


# ---------------------------------------------------------------------------
# Equipment Listing tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_equipment_listing_lists(list_names: list[str] | None = None) -> dict:
    """
    Retrieve the supporting reference lists used when querying equipment listings.

    Available list names: CityID, ControllerID, CostCenterID, CustomerID, DepartmentID,
    Engine1ID, FleetConfigID, Make1ID, MeterProfileID, Model1ID, MotorID, PartsCatalogID,
    PmDocID, Power1ID, RegionID, TelemetryIntegID, UserStatusID, VehicleTypeID,
    WorkCenterID, ZoneID.

    Args:
        list_names: Optional list of specific list names to return,
                    e.g. ["CityID", "VehicleTypeID"]. If omitted, all lists are returned.

    Returns:
        Dict of requested reference lists, each containing {ID, Name} entries.
    """
    params = {}
    if list_names:
        params["name"] = ",".join(list_names)
    return _get("equipment/listing/lists", params=params)


@mcp.tool()
def get_equipment_listing(
    after_paint_date: list[str] | None = None,
    any_license_due_next_days: int | None = None,
    asset_no: str | None = None,
    asset_no_multiple: list[str] | None = None,
    banner_status: str | None = None,
    battery_mgmt_id: str | None = None,
    city_ids: list[int | str] | None = None,
    city_no_like: str | None = None,
    city_no_multiple: list[str] | None = None,
    contractor: str | None = None,
    controller_ids: list[int | str] | None = None,
    cost_center_ids: list[int | str] | None = None,
    customer_ids: list[int | str] | None = None,
    department_ids: list[int | str] | None = None,
    ebis_ids: list[int] | None = None,
    engine1_ids: list[int | str] | None = None,
    engine1_serial: str | None = None,
    engine1_spec_no: str | None = None,
    fleet_config_ids: list[int | str] | None = None,
    front_axel_serial: str | None = None,
    has_date_based_schedule: bool = False,
    has_license_no: str | None = None,
    has_linked_parts_list_override: str | None = None,
    has_meter_based_schedule: bool = False,
    has_pm_part_kit: str | None = None,
    has_pm_part_kit_override: str | None = None,
    has_pm_schedules: str | None = None,
    has_seatbelt: str | None = None,
    inactive_include: bool = False,
    last_pm_over_days_ago: int | None = None,
    lease_expires_next_days: int | None = None,
    license_no: str | None = None,
    make1_ids: list[int | str] | None = None,
    meter_profile_ids: list[int | str] | None = None,
    model1_ids: list[int | str] | None = None,
    motor_ids: list[int | str] | None = None,
    only_inactive: bool = False,
    only_with_telemetry: bool = False,
    only_with_valid_warranty: bool = False,
    parts_catalog_ids: list[int | str] | None = None,
    pm_doc_ids: list[int | str] | None = None,
    power1_ids: list[int | str] | None = None,
    rear_axel_serial: str | None = None,
    reflectivity: str | None = None,
    region_ids: list[int | str] | None = None,
    rental_expires_next_days: int | None = None,
    serial_no: str | None = None,
    show_license_no: bool = False,
    stationary_loc_multiple: list[str] | None = None,
    surplus: str | None = None,
    telemetry_integ_ids: list[int | str] | None = None,
    telemetry_key: str | None = None,
    transmission_serial: str | None = None,
    user_status_ids: list[int | str] | None = None,
    vehicle_type_ids: list[int | str] | None = None,
    vin: str | None = None,
    warranty_expires_in_days: int | None = None,
    work_center_ids: list[int | str] | None = None,
    year_built: list[int] | None = None,
    zone_ids: list[int | str] | None = None,
    id_accessible: bool = False,
    language: str | None = None,
) -> dict:
    """
    Retrieve a general equipment listing based on custom criteria.

    Use get_equipment_listing_lists() to discover valid ID/name values for
    any of the ID filter parameters.

    Args:
        after_paint_date: Filter equipment painted after these dates, e.g. ["2024-01-25"].
        any_license_due_next_days: Return equipment with any license due within N days.
        asset_no: Fragment search on asset number.
        asset_no_multiple: Filter by multiple exact asset numbers, e.g. ["A001", "A002"].
        banner_status: Fragment search on banner status.
        battery_mgmt_id: Fragment search on battery management ID.
        city_ids: Filter by city IDs or names.
        city_no_like: Fragment search on city number.
        city_no_multiple: Filter by multiple exact city numbers, e.g. ["C01", "C02"].
        contractor: Filter by contractor status — "yes", "no", or "all".
        controller_ids: Filter by controller IDs or names.
        cost_center_ids: Filter by cost center IDs or names.
        customer_ids: Filter by customer IDs or names.
        department_ids: Filter by department IDs or names.
        ebis_ids: Filter by specific eBis equipment IDs.
        engine1_ids: Filter by primary engine IDs or names.
        engine1_serial: Fragment search on primary engine serial number.
        engine1_spec_no: Fragment search on primary engine spec number.
        fleet_config_ids: Filter by fleet configuration IDs or names.
        front_axel_serial: Fragment search on front axle serial number.
        has_date_based_schedule: If True, return only equipment with a date-based PM schedule.
        has_license_no: Filter by license number presence — "yes", "no", or "all".
        has_linked_parts_list_override: Filter by linked parts list override — "yes", "no", or "all".
        has_meter_based_schedule: If True, return only equipment with a meter-based PM schedule.
        has_pm_part_kit: Filter by PM part kit presence — "yes", "no", or "all".
        has_pm_part_kit_override: Filter by PM part kit override — "yes", "no", or "all".
        has_pm_schedules: Filter by PM schedule presence — "yes", "no", or "all".
        has_seatbelt: Filter by seatbelt presence — "yes", "no", or "all".
        inactive_include: If True, include inactive equipment in the results.
        last_pm_over_days_ago: Return equipment whose last PM was more than N days ago.
        lease_expires_next_days: Return equipment whose lease expires within N days.
        license_no: Fragment search on license number.
        make1_ids: Filter by primary make IDs or names.
        meter_profile_ids: Filter by meter profile IDs or names.
        model1_ids: Filter by primary model IDs or names.
        motor_ids: Filter by motor IDs or names.
        only_inactive: If True, return only inactive equipment.
        only_with_telemetry: If True, return only equipment that has telemetry.
        only_with_valid_warranty: If True, return only equipment with a valid warranty.
        parts_catalog_ids: Filter by parts catalog IDs or names.
        pm_doc_ids: Filter by PM document IDs or names.
        power1_ids: Filter by primary power source IDs or names.
        rear_axel_serial: Fragment search on rear axle serial number.
        reflectivity: Filter by reflectivity status — "yes", "no", or "all".
        region_ids: Filter by region IDs or names.
        rental_expires_next_days: Return equipment whose rental expires within N days.
        serial_no: Fragment search on equipment serial number.
        show_license_no: If True, include license number fields in the response.
        stationary_loc_multiple: Filter by multiple stationary location values.
        surplus: Filter by surplus status — "yes", "no", or "all".
        telemetry_integ_ids: Filter by telemetry integration IDs or names.
        telemetry_key: Fragment search on telemetry key.
        transmission_serial: Fragment search on transmission serial number.
        user_status_ids: Filter by user status IDs or names.
        vehicle_type_ids: Filter by vehicle type IDs or names.
        vin: Fragment search on VIN.
        warranty_expires_in_days: Return equipment whose warranty expires within N days.
        work_center_ids: Filter by work center IDs or names.
        year_built: Filter by year(s) built, e.g. [2001, 2002].
        zone_ids: Filter by zone IDs or names.
        id_accessible: If True, child lists are keyed by ID rather than returned as arrays.
        language: Language for generic list parameter lookups (default: "English").

    Returns:
        Equipment listing records matching the requested filters.
    """
    body: dict[str, Any] = {}

    if after_paint_date is not None:
        body["AfterPaintDate"] = after_paint_date
    if any_license_due_next_days is not None:
        body["AnyLicenseDueNextDays"] = any_license_due_next_days
    if asset_no is not None:
        body["AssetNo"] = asset_no
    if asset_no_multiple is not None:
        body["AssetNoMultiple"] = asset_no_multiple
    if banner_status is not None:
        body["BannerStatus"] = banner_status
    if battery_mgmt_id is not None:
        body["BatteryMgmtID"] = battery_mgmt_id
    if city_ids is not None:
        body["CityID"] = city_ids
    if city_no_like is not None:
        body["CityNoLike"] = city_no_like
    if city_no_multiple is not None:
        body["CityNoMultiple"] = city_no_multiple
    if contractor is not None:
        body["Contractor"] = contractor
    if controller_ids is not None:
        body["ControllerID"] = controller_ids
    if cost_center_ids is not None:
        body["CostCenterID"] = cost_center_ids
    if customer_ids is not None:
        body["CustomerID"] = customer_ids
    if department_ids is not None:
        body["DepartmentID"] = department_ids
    if ebis_ids is not None:
        body["EBisID"] = ebis_ids
    if engine1_ids is not None:
        body["Engine1ID"] = engine1_ids
    if engine1_serial is not None:
        body["Engine1Serial"] = engine1_serial
    if engine1_spec_no is not None:
        body["Engine1SpecNo"] = engine1_spec_no
    if fleet_config_ids is not None:
        body["FleetConfigID"] = fleet_config_ids
    if front_axel_serial is not None:
        body["FrontAxelSerial"] = front_axel_serial
    if has_date_based_schedule:
        body["HasDateBasedSchedule"] = True
    if has_license_no is not None:
        body["HasLicenseNo"] = has_license_no
    if has_linked_parts_list_override is not None:
        body["HasLinkedPartsListOverride"] = has_linked_parts_list_override
    if has_meter_based_schedule:
        body["HasMeterBasedSchedule"] = True
    if has_pm_part_kit is not None:
        body["HasPmPartKit"] = has_pm_part_kit
    if has_pm_part_kit_override is not None:
        body["HasPmPartKitOverride"] = has_pm_part_kit_override
    if has_pm_schedules is not None:
        body["HasPmSchedules"] = has_pm_schedules
    if has_seatbelt is not None:
        body["HasSeatbelt"] = has_seatbelt
    if inactive_include:
        body["InactiveInclude"] = True
    if last_pm_over_days_ago is not None:
        body["LastPmOverDaysAgo"] = last_pm_over_days_ago
    if lease_expires_next_days is not None:
        body["LeaseExpiresNextDays"] = lease_expires_next_days
    if license_no is not None:
        body["LicenseNo"] = license_no
    if make1_ids is not None:
        body["Make1ID"] = make1_ids
    if meter_profile_ids is not None:
        body["MeterProfileID"] = meter_profile_ids
    if model1_ids is not None:
        body["Model1ID"] = model1_ids
    if motor_ids is not None:
        body["MotorID"] = motor_ids
    if only_inactive:
        body["OnlyInactive"] = True
    if only_with_telemetry:
        body["OnlyWithTelemetry"] = True
    if only_with_valid_warranty:
        body["OnlyWithValidWarranty"] = True
    if parts_catalog_ids is not None:
        body["PartsCatalogID"] = parts_catalog_ids
    if pm_doc_ids is not None:
        body["PmDocID"] = pm_doc_ids
    if power1_ids is not None:
        body["Power1ID"] = power1_ids
    if rear_axel_serial is not None:
        body["RearAxelSerial"] = rear_axel_serial
    if reflectivity is not None:
        body["Reflectivity"] = reflectivity
    if region_ids is not None:
        body["RegionID"] = region_ids
    if rental_expires_next_days is not None:
        body["RentalExpiresNextDays"] = rental_expires_next_days
    if serial_no is not None:
        body["SerialNo"] = serial_no
    if show_license_no:
        body["ShowLicenseNo"] = True
    if stationary_loc_multiple is not None:
        body["StationaryLocMultiple"] = stationary_loc_multiple
    if surplus is not None:
        body["Surplus"] = surplus
    if telemetry_integ_ids is not None:
        body["TelemetryIntegID"] = telemetry_integ_ids
    if telemetry_key is not None:
        body["TelemetryKey"] = telemetry_key
    if transmission_serial is not None:
        body["TransmissionSerial"] = transmission_serial
    if user_status_ids is not None:
        body["UserStatusID"] = user_status_ids
    if vehicle_type_ids is not None:
        body["VehicleTypeID"] = vehicle_type_ids
    if vin is not None:
        body["Vin"] = vin
    if warranty_expires_in_days is not None:
        body["WarrantyExpiresInDays"] = warranty_expires_in_days
    if work_center_ids is not None:
        body["WorkCenterID"] = work_center_ids
    if year_built is not None:
        body["YearBuilt"] = year_built
    if zone_ids is not None:
        body["ZoneID"] = zone_ids
    if id_accessible:
        body["IDAccessible"] = True
    if language is not None:
        body["Language"] = language

    return _post("equipment/listing", body)


# ---------------------------------------------------------------------------
# Out Of Service Detail tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_out_of_service_lists(list_names: list[str] | None = None) -> dict:
    """
    Retrieve the supporting reference lists used when querying out-of-service detail.

    Available list names: CityID, CustomerID, DepartmentGroupID, DepartmentID,
    MaintainedByID, MakeID, ModelID, PowerID, RegionID, VehicleTypeID, WorkCenterID.

    Args:
        list_names: Optional list of specific list names to return,
                    e.g. ["CityID", "VehicleTypeID"]. If omitted, all lists are returned.

    Returns:
        Dict of requested reference lists, each containing {ID, Name} entries.
    """
    params = {}
    if list_names:
        params["name"] = ",".join(list_names)
    return _get("equipment/outofservice/detail/lists", params=params)


@mcp.tool()
def get_out_of_service_detail(
    city_ids: list[int | str] | None = None,
    customer_ids: list[int | str] | None = None,
    department_group_ids: list[int | str] | None = None,
    department_ids: list[int | str] | None = None,
    maintained_by_ids: list[int | str] | None = None,
    make_ids: list[int | str] | None = None,
    model_ids: list[int | str] | None = None,
    power_ids: list[int | str] | None = None,
    region_ids: list[int | str] | None = None,
    show_detail: bool = False,
    vehicle_type_ids: list[int | str] | None = None,
    work_center_ids: list[int | str] | None = None,
    id_accessible: bool = False,
) -> dict:
    """
    Retrieve a detailed list of equipment currently out of service.

    Use get_out_of_service_lists() to discover valid ID/name values for
    any of the ID filter parameters.

    Args:
        city_ids: Filter by city IDs or names.
        customer_ids: Filter by customer IDs or names.
        department_group_ids: Filter by department group IDs or names.
        department_ids: Filter by department IDs or names.
        maintained_by_ids: Filter by maintained-by organisation IDs or names.
        make_ids: Filter by equipment make IDs or names.
        model_ids: Filter by equipment model IDs or names.
        power_ids: Filter by power source IDs or names.
        region_ids: Filter by region IDs or names.
        show_detail: If True, include additional detail fields in the response.
        vehicle_type_ids: Filter by vehicle type IDs or names.
        work_center_ids: Filter by work center IDs or names.
        id_accessible: If True, child lists are keyed by ID rather than returned as arrays.

    Returns:
        Out-of-service equipment records matching the requested filters.
    """
    body: dict[str, Any] = {}

    if city_ids is not None:
        body["CityID"] = city_ids
    if customer_ids is not None:
        body["CustomerID"] = customer_ids
    if department_group_ids is not None:
        body["DepartmentGroupID"] = department_group_ids
    if department_ids is not None:
        body["DepartmentID"] = department_ids
    if maintained_by_ids is not None:
        body["MaintainedByID"] = maintained_by_ids
    if make_ids is not None:
        body["MakeID"] = make_ids
    if model_ids is not None:
        body["ModelID"] = model_ids
    if power_ids is not None:
        body["PowerID"] = power_ids
    if region_ids is not None:
        body["RegionID"] = region_ids
    if show_detail:
        body["ShowDetail"] = True
    if vehicle_type_ids is not None:
        body["VehicleTypeID"] = vehicle_type_ids
    if work_center_ids is not None:
        body["WorkCenterID"] = work_center_ids
    if id_accessible:
        body["IDAccessible"] = True

    return _post("equipment/outofservice/detail", body)


# ---------------------------------------------------------------------------
# Out Of Service Summary tool
# ---------------------------------------------------------------------------

@mcp.tool()
def get_out_of_service_summary(id_accessible: bool = False) -> dict:
    """
    Retrieve live and snapshot out-of-service summary information for equipment.

    This endpoint has no filter parameters — it returns the full summary for all
    equipment accessible to the authenticated user.

    Args:
        id_accessible: If True, child lists are keyed by ID rather than returned as arrays.

    Returns:
        Out-of-service summary records including live and snapshot OOS data.
    """
    body: dict[str, Any] = {}

    if id_accessible:
        body["IDAccessible"] = True

    return _post("equipment/outofservice/summary", body)


# ---------------------------------------------------------------------------
# Equipment Transfer tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_equipment_transfer_lists(list_names: list[str] | None = None) -> dict:
    """
    Retrieve the supporting reference lists used when querying equipment transfers.

    Available list names: CityID.

    Args:
        list_names: Optional list of specific list names to return,
                    e.g. ["CityID"]. If omitted, all lists are returned.

    Returns:
        Dict of requested reference lists, each containing {ID, Name} entries.
    """
    params = {}
    if list_names:
        params["name"] = ",".join(list_names)
    return _get("equipment/transfer/lists", params=params)


@mcp.tool()
def get_equipment_transfers(
    transfer_dates: list[str],
    city_ids: list[int | str] | None = None,
    id_accessible: bool = False,
) -> dict:
    """
    Retrieve the history of equipment transferred between cities.

    Args:
        transfer_dates: (Required) One or more dates to query transfers for,
                        e.g. ["2024-01-25", "2024-01-26"].
        city_ids: Filter by city IDs or names. Use get_equipment_transfer_lists()
                  to find valid values.
        id_accessible: If True, child lists are keyed by ID rather than returned as arrays.

    Returns:
        Equipment transfer history records for the requested dates and filters.
    """
    body: dict[str, Any] = {
        "TransferDate": transfer_dates,
    }

    if city_ids is not None:
        body["CityID"] = city_ids
    if id_accessible:
        body["IDAccessible"] = True

    return _post("equipment/transfer", body)


# ---------------------------------------------------------------------------
# Equipment Batch Add/Update tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_equipment_addupdate_lists(list_names: list[str] | None = None) -> dict:
    """
    Retrieve the supporting reference lists used when adding or updating equipment.

    Available list names: EquipTypeID, CityID, MeterProfileID, CustomerID, VehicleTypeID,
    ControllerID, MotorID, TelemetryIntegID, UserStatusID, DepartmentID, WorkCenterID,
    CostCenterID, BillingProfileID, ColorID, CurrencyID, ToolCertID, FleetConfigID,
    PartsCatalogID, PmPartKitID, PartListPartKitID, CategoryProfileID, EpaTypeID,
    LocationID, MaintainedByID, AerialMake1ID, AerialModel1ID, AtRiskID, AbeIndicatorID,
    FleetObjectID, LeassorID, PmiTypeID, StepConfigID, SystemStatusID, WorkClassID,
    PoiTypeID, EngineID, MakeID, ModelID, PowerID, TransmissionID, VendorID.

    Args:
        list_names: Optional list of specific list names to return,
                    e.g. ["EquipTypeID", "CityID"]. If omitted, all lists are returned.

    Returns:
        Dict of requested reference lists, each containing {ID, Name} entries.
    """
    params = {}
    if list_names:
        params["name"] = ",".join(list_names)
    return _get("equipment/addupdate/lists", params=params)


@mcp.tool()
def add_update_equipment(
    # Batch mode — mutually exclusive with single-record fields
    equipment_batch: list[dict] | None = None,
    # Single-record mode
    mode: str | None = None,
    # Record identity / lookup
    id: int | None = None,
    ebis_id: int | None = None,
    asset_id_lookup: int | None = None,
    city_abbr_lookup: str | None = None,
    # Core fields (required for Insert)
    city_id: int | None = None,
    city_no: str | None = None,
    equip_type_id: int | None = None,
    meter_profile_id: int | None = None,
    vehicle_type_id: int | None = None,
    # General fields
    customer_id: int | None = None,
    customer2_id: int | None = None,
    make1_id: int | None = None,
    model1_id: int | None = None,
    year_built: int | None = None,
    power1_id: int | None = None,
    engine1_id: int | None = None,
    engine1_serial: str | None = None,
    engine1_spec_no: str | None = None,
    transmission1_id: int | None = None,
    controller_id: int | None = None,
    motor_id: int | None = None,
    serial_no: str | None = None,
    vin: str | None = None,
    asset_no: str | None = None,
    stationary_loc: str | None = None,
    telemetry_integ_id: int | None = None,
    telemetry_vendor_asset_no: str | None = None,
    user_status_id: int | None = None,
    department_id: int | None = None,
    work_center_id: int | None = None,
    cost_center_id: int | None = None,
    billing_profile_id: int | None = None,
    tax_profile_id: int | None = None,
    color_id: int | None = None,
    color_other: str | None = None,
    license_no: str | None = None,
    cost: float | None = None,
    currency_id: int | None = None,
    in_service_date: str | None = None,
    in_service_refurb_date: str | None = None,
    warranty_expires: str | None = None,
    warranty_expires2: str | None = None,
    warranty_notes: str | None = None,
    surplus: bool | None = None,
    cab: bool | None = None,
    is_test: bool | None = None,
    has_seatbelt: bool | None = None,
    reflectivity: bool | None = None,
    ext_warranty: bool | None = None,
    purch_used: bool | None = None,
    disable_pm_wo_create: bool | None = None,
    notes: str | None = None,
    banner_status: str | None = None,
    # Secondary make/model/engine
    make2_id: int | None = None,
    model2_id: int | None = None,
    power2_id: int | None = None,
    engine2_id: int | None = None,
    engine2_serial: str | None = None,
    engine_spec_no2: str | None = None,
    serial_no2: str | None = None,
    # Engine detail
    engine1_hp: int | None = None,
    engine1_capacity: float | None = None,
    engine1_num_cyl: int | None = None,
    engine1_model_year: int | None = None,
    engine1_model_type: str | None = None,
    engine1_family_code: str | None = None,
    engine1_rpm: str | None = None,
    epa_type_id: int | None = None,
    epa_license_no: str | None = None,
    # Calibration / tool cert
    tool_cert_id: int | None = None,
    calib_date: str | None = None,
    due_date: str | None = None,
    label_date: str | None = None,
    calib_schedule: str | None = None,
    # Profile / catalog links
    fleet_config_id: int | None = None,
    parts_catalog_id: int | None = None,
    pm_part_kit_id: int | None = None,
    part_list_part_kit_id: int | None = None,
    category_profile_id: int | None = None,
    pm_parts_kit_disable: bool | None = None,
    # Location / org
    location_id: int | None = None,
    maintained_by_id: int | None = None,
    po_dest_stock_room_id: int | None = None,
    # Vendor
    vendor1_id: int | None = None,
    vendor1_contact: str | None = None,
    vendor2_id: int | None = None,
    vendor2_contact: str | None = None,
    # Dates / financial
    acquisition_date: str | None = None,
    delivery_date: str | None = None,
    replacement_date: str | None = None,
    lease_cost: float | None = None,
    lease_expires: str | None = None,
    retire_date: str | None = None,
    after_paint_date: str | None = None,
    inspection_date: str | None = None,
    rental_start_date: str | None = None,
    rental_expire_date: str | None = None,
    appraisal_value: float | None = None,
    book_value: float | None = None,
    disposal_value: float | None = None,
    sold_fee: float | None = None,
    sold_to: str | None = None,
    # License expiries
    airport_license: str | None = None,
    airport_lic_expire: str | None = None,
    city_lic_expire: str | None = None,
    state_lic_expire: str | None = None,
    county_lic_expire: str | None = None,
    country_lic_expire: str | None = None,
    # Physical / misc
    fuel_capacity: float | None = None,
    obj_length: float | None = None,
    obj_width: float | None = None,
    obj_height: float | None = None,
    obj_gross_weight: float | None = None,
    obj_empty_weight: float | None = None,
    obj_total_weight: float | None = None,
    freon_amount: str | None = None,
    freon_type: str | None = None,
    size_dimension: str | None = None,
    sort_field: str | None = None,
    env_no: str | None = None,
    shea_no: str | None = None,
    usage_indictator: int | None = None,
    gse_eq_count: int | None = None,
    construct_month: int | None = None,
    prior_asset_no: str | None = None,
    prior_owner: str | None = None,
    asset_mgm_no: str | None = None,
    chassis_no: str | None = None,
    eq_part_category: str | None = None,
    plant_section: str | None = None,
    county_reg: str | None = None,
    state_reg: str | None = None,
    country_reg: str | None = None,
    country_manuf: str | None = None,
    planner_group: str | None = None,
    planning_plant: str | None = None,
    identification: str | None = None,
    # Aerial / specialty
    aerial_make1_id: int | None = None,
    aerial_model1_id: int | None = None,
    aerial_serial: str | None = None,
    aerial_year_built: int | None = None,
    product_filter_type_id: int | None = None,
    at_risk_id: int | None = None,
    abe_indicator_id: int | None = None,
    fleet_object_id: int | None = None,
    leassor_id: int | None = None,
    pmi_type_id: int | None = None,
    step_config_id: int | None = None,
    system_status_id: int | None = None,
    work_class_id: int | None = None,
    poi_type_id: int | None = None,
    # Drivetrain serials
    transmission_serial: str | None = None,
    front_axel_serial: str | None = None,
    rear_axel_serial: str | None = None,
    front_torque: str | None = None,
    rear_torque: str | None = None,
    # City No insert helpers
    city_no_insert_type_id: int | None = None,
    city_no_insert_prefix: str | None = None,
    # Conveyor / specialty fields
    belt_type: str | None = None,
    belt_width_between: float | None = None,
    belt_length: str | None = None,
    drive_belt_no: str | None = None,
    clutch_brake_no: str | None = None,
    controller_type: str | None = None,
    bed_length: str | None = None,
    incline_angle: str | None = None,
    degree_of_turn: int | None = None,
    inside_radius: int | None = None,
    mfr_motor_framecode: str | None = None,
    mfr_no: str | None = None,
    master_control_no: str | None = None,
    motor_hp: float | None = None,
    oem: str | None = None,
    reducer_no: str | None = None,
    is_scale: bool | None = None,
    scale_capacity: float | None = None,
    scale_length: float | None = None,
    scale_revenue: float | None = None,
    scale_width: float | None = None,
    scale_height: float | None = None,
    motor_no: str | None = None,
    motor_mfr: str | None = None,
    reducer_mfr: str | None = None,
    reducer_ratio: str | None = None,
    workstation1: str | None = None,
    workstation2: str | None = None,
    # Mode=ChangeCityNo
    change_to_city_no: str | None = None,
    # Mode=ChangeEquipType
    change_to_equip_type_id: int | None = None,
    # Mode=Transfer
    transfer_to_city_id: int | None = None,
    transfer_to_work_center_id: int | None = None,
    transfer_to_cost_center_id: int | None = None,
    transfer_date: str | None = None,
    transfer_notes: str | None = None,
    transfer_inactivate: bool | None = None,
    transfer_activate: bool | None = None,
    transfer_move_open_wos: bool | None = None,
    transfer_void_open_wos: bool | None = None,
    # Mode=PowerChange
    power_change_to_power_id: int | None = None,
    power_change_to_engine_id: int | None = None,
    power_change_to_transmission_id: int | None = None,
    power_change_notes: str | None = None,
    power_change_engine1_serial: str | None = None,
    power_change_engine1_spec_no: str | None = None,
    power_change_engine1_family_code: str | None = None,
    power_change_engine1_rpm: str | None = None,
    power_change_engine1_hp: float | None = None,
    power_change_engine1_capacity: float | None = None,
    power_change_engine1_num_cyl: int | None = None,
    power_change_engine1_model_year: int | None = None,
    # Generic name-based lookups
    engine_id: int | str | None = None,
    make_id: int | str | None = None,
    model_id: int | str | None = None,
    power_id: int | str | None = None,
    telemetry_profile_id: int | str | None = None,
    transmission_id: int | str | None = None,
    vendor_id: int | str | None = None,
    user_validate_temp_token: str | None = None,
) -> dict:
    """
    Add or update one or more pieces of equipment in eBis Cloud.

    Supports two calling modes:
    - **Batch mode**: Pass a list of equipment dicts via `equipment_batch`. Each dict
      should contain a `Mode` and whichever fields apply to that record. A `LineNumber`
      in each dict is returned in the response to correlate results.
    - **Single-record mode**: Pass `mode` and individual field parameters directly.

    Equipment is matched (for Update/Activate/etc.) on any of: ID, EBisID,
    AssetIDLookup, CityAbbrLookup, or CityNo.

    Mode values and their requirements:
    - **Insert**: CityNo, CityID, VehicleTypeID, MeterProfileID, EquipTypeID required.
      Use city_no_insert_type_id / city_no_insert_prefix to auto-generate CityNo.
    - **Update**: Any general fields included will be updated.
    - **Activate**: Reactivates the equipment record.
    - **Inactivate**: Inactivates the equipment record.
    - **PowerChange**: Apply fields beginning with `power_change_*`.
    - **ChangeEquipType**: Requires `change_to_equip_type_id`.
    - **ChangeCityNo**: Requires `change_to_city_no`.
    - **Transfer**: Requires `transfer_to_city_id` and `transfer_date`.

    Use get_equipment_addupdate_lists() to find valid IDs for any ID parameter.

    Returns:
        List of per-equipment results, each with EBisID, LineNumber, MessageID,
        MessageText, and an Actions list detailing what was done and whether it succeeded.
    """
    # Batch mode takes priority
    if equipment_batch is not None:
        return _post("equipment/addupdate", {"EquipmentBatch": equipment_batch})

    body: dict[str, Any] = {}

    if mode is not None:
        body["Mode"] = mode
    if id is not None:
        body["ID"] = id
    if ebis_id is not None:
        body["EBisID"] = ebis_id
    if asset_id_lookup is not None:
        body["AssetIDLookup"] = asset_id_lookup
    if city_abbr_lookup is not None:
        body["CityAbbrLookup"] = city_abbr_lookup
    if city_id is not None:
        body["CityID"] = city_id
    if city_no is not None:
        body["CityNo"] = city_no
    if equip_type_id is not None:
        body["EquipTypeID"] = equip_type_id
    if meter_profile_id is not None:
        body["MeterProfileID"] = meter_profile_id
    if vehicle_type_id is not None:
        body["VehicleTypeID"] = vehicle_type_id
    if customer_id is not None:
        body["CustomerID"] = customer_id
    if customer2_id is not None:
        body["Customer2ID"] = customer2_id
    if make1_id is not None:
        body["Make1ID"] = make1_id
    if model1_id is not None:
        body["Model1ID"] = model1_id
    if year_built is not None:
        body["YearBuilt"] = year_built
    if power1_id is not None:
        body["Power1ID"] = power1_id
    if engine1_id is not None:
        body["Engine1ID"] = engine1_id
    if engine1_serial is not None:
        body["Engine1Serial"] = engine1_serial
    if engine1_spec_no is not None:
        body["Engine1SpecNo"] = engine1_spec_no
    if transmission1_id is not None:
        body["Transmission1ID"] = transmission1_id
    if controller_id is not None:
        body["ControllerID"] = controller_id
    if motor_id is not None:
        body["MotorID"] = motor_id
    if serial_no is not None:
        body["SerialNo"] = serial_no
    if vin is not None:
        body["Vin"] = vin
    if asset_no is not None:
        body["AssetNo"] = asset_no
    if stationary_loc is not None:
        body["StationaryLoc"] = stationary_loc
    if telemetry_integ_id is not None:
        body["TelemetryIntegID"] = telemetry_integ_id
    if telemetry_vendor_asset_no is not None:
        body["TelemetryVendorAssetNo"] = telemetry_vendor_asset_no
    if user_status_id is not None:
        body["UserStatusID"] = user_status_id
    if department_id is not None:
        body["DepartmentID"] = department_id
    if work_center_id is not None:
        body["WorkCenterID"] = work_center_id
    if cost_center_id is not None:
        body["CostCenterID"] = cost_center_id
    if billing_profile_id is not None:
        body["BillingProfileID"] = billing_profile_id
    if tax_profile_id is not None:
        body["TaxProfileID"] = tax_profile_id
    if color_id is not None:
        body["ColorID"] = color_id
    if color_other is not None:
        body["ColorOther"] = color_other
    if license_no is not None:
        body["LicenseNo"] = license_no
    if cost is not None:
        body["Cost"] = cost
    if currency_id is not None:
        body["CurrencyID"] = currency_id
    if in_service_date is not None:
        body["InServiceDate"] = in_service_date
    if in_service_refurb_date is not None:
        body["InServiceRefurbDate"] = in_service_refurb_date
    if warranty_expires is not None:
        body["WarrantyExpires"] = warranty_expires
    if warranty_expires2 is not None:
        body["WarrantyExpires2"] = warranty_expires2
    if warranty_notes is not None:
        body["WarrantyNotes"] = warranty_notes
    if surplus is not None:
        body["Surplus"] = surplus
    if cab is not None:
        body["Cab"] = cab
    if is_test is not None:
        body["IsTest"] = is_test
    if has_seatbelt is not None:
        body["HasSeatbelt"] = has_seatbelt
    if reflectivity is not None:
        body["Reflectivity"] = reflectivity
    if ext_warranty is not None:
        body["ExtWarranty"] = ext_warranty
    if purch_used is not None:
        body["PurchUsed"] = purch_used
    if disable_pm_wo_create is not None:
        body["DisablePmWoCreate"] = disable_pm_wo_create
    if notes is not None:
        body["Notes"] = notes
    if banner_status is not None:
        body["BannerStatus"] = banner_status
    if make2_id is not None:
        body["Make2ID"] = make2_id
    if model2_id is not None:
        body["Model2ID"] = model2_id
    if power2_id is not None:
        body["Power2ID"] = power2_id
    if engine2_id is not None:
        body["Engine2ID"] = engine2_id
    if engine2_serial is not None:
        body["Engine2Serial"] = engine2_serial
    if engine_spec_no2 is not None:
        body["EngineSpecNo2"] = engine_spec_no2
    if serial_no2 is not None:
        body["SerialNo2"] = serial_no2
    if engine1_hp is not None:
        body["Engine1HP"] = engine1_hp
    if engine1_capacity is not None:
        body["Engine1Capacity"] = engine1_capacity
    if engine1_num_cyl is not None:
        body["Engine1NumCyl"] = engine1_num_cyl
    if engine1_model_year is not None:
        body["Engine1ModelYear"] = engine1_model_year
    if engine1_model_type is not None:
        body["Engine1ModelType"] = engine1_model_type
    if engine1_family_code is not None:
        body["Engine1FamilyCode"] = engine1_family_code
    if engine1_rpm is not None:
        body["Engine1Rpm"] = engine1_rpm
    if epa_type_id is not None:
        body["EpaTypeID"] = epa_type_id
    if epa_license_no is not None:
        body["EpaLicenseNo"] = epa_license_no
    if tool_cert_id is not None:
        body["ToolCertID"] = tool_cert_id
    if calib_date is not None:
        body["CalibDate"] = calib_date
    if due_date is not None:
        body["DueDate"] = due_date
    if label_date is not None:
        body["LabelDate"] = label_date
    if calib_schedule is not None:
        body["CalibSchedule"] = calib_schedule
    if fleet_config_id is not None:
        body["FleetConfigID"] = fleet_config_id
    if parts_catalog_id is not None:
        body["PartsCatalogID"] = parts_catalog_id
    if pm_part_kit_id is not None:
        body["PmPartKitID"] = pm_part_kit_id
    if part_list_part_kit_id is not None:
        body["PartListPartKitID"] = part_list_part_kit_id
    if category_profile_id is not None:
        body["CategoryProfileID"] = category_profile_id
    if pm_parts_kit_disable is not None:
        body["PmPartsKitDisable"] = pm_parts_kit_disable
    if location_id is not None:
        body["LocationID"] = location_id
    if maintained_by_id is not None:
        body["MaintainedByID"] = maintained_by_id
    if po_dest_stock_room_id is not None:
        body["PoDestStockRoomID"] = po_dest_stock_room_id
    if vendor1_id is not None:
        body["Vendor1ID"] = vendor1_id
    if vendor1_contact is not None:
        body["Vendor1Contact"] = vendor1_contact
    if vendor2_id is not None:
        body["Vendor2ID"] = vendor2_id
    if vendor2_contact is not None:
        body["Vendor2Contact"] = vendor2_contact
    if acquisition_date is not None:
        body["AcquisitionDate"] = acquisition_date
    if delivery_date is not None:
        body["DeliveryDate"] = delivery_date
    if replacement_date is not None:
        body["ReplacementDate"] = replacement_date
    if lease_cost is not None:
        body["LeaseCost"] = lease_cost
    if lease_expires is not None:
        body["LeaseExpires"] = lease_expires
    if retire_date is not None:
        body["RetireDate"] = retire_date
    if after_paint_date is not None:
        body["AfterPaintDate"] = after_paint_date
    if inspection_date is not None:
        body["InspectionDate"] = inspection_date
    if rental_start_date is not None:
        body["RentalStartDate"] = rental_start_date
    if rental_expire_date is not None:
        body["RentalExpireDate"] = rental_expire_date
    if appraisal_value is not None:
        body["AppraisalValue"] = appraisal_value
    if book_value is not None:
        body["BookValue"] = book_value
    if disposal_value is not None:
        body["DisposalValue"] = disposal_value
    if sold_fee is not None:
        body["SoldFee"] = sold_fee
    if sold_to is not None:
        body["SoldTo"] = sold_to
    if airport_license is not None:
        body["AirportLicense"] = airport_license
    if airport_lic_expire is not None:
        body["AirportLicExpire"] = airport_lic_expire
    if city_lic_expire is not None:
        body["CityLicExpire"] = city_lic_expire
    if state_lic_expire is not None:
        body["StateLicExpire"] = state_lic_expire
    if county_lic_expire is not None:
        body["CountyLicExpire"] = county_lic_expire
    if country_lic_expire is not None:
        body["CountryLicExpire"] = country_lic_expire
    if fuel_capacity is not None:
        body["FuelCapacity"] = fuel_capacity
    if obj_length is not None:
        body["ObjLength"] = obj_length
    if obj_width is not None:
        body["ObjWidth"] = obj_width
    if obj_height is not None:
        body["ObjHeight"] = obj_height
    if obj_gross_weight is not None:
        body["ObjGrossWeight"] = obj_gross_weight
    if obj_empty_weight is not None:
        body["ObjEmptyWeight"] = obj_empty_weight
    if obj_total_weight is not None:
        body["ObjTotalWeight"] = obj_total_weight
    if freon_amount is not None:
        body["FreonAmount"] = freon_amount
    if freon_type is not None:
        body["FreonType"] = freon_type
    if size_dimension is not None:
        body["SizeDimension"] = size_dimension
    if sort_field is not None:
        body["SortField"] = sort_field
    if env_no is not None:
        body["EnvNo"] = env_no
    if shea_no is not None:
        body["SheaNo"] = shea_no
    if usage_indictator is not None:
        body["UsageIndictator"] = usage_indictator
    if gse_eq_count is not None:
        body["GseEqCount"] = gse_eq_count
    if construct_month is not None:
        body["ConstructMonth"] = construct_month
    if prior_asset_no is not None:
        body["PriorAssetNo"] = prior_asset_no
    if prior_owner is not None:
        body["PriorOwner"] = prior_owner
    if asset_mgm_no is not None:
        body["AssetMgmNo"] = asset_mgm_no
    if chassis_no is not None:
        body["ChassisNo"] = chassis_no
    if eq_part_category is not None:
        body["EqPartCategory"] = eq_part_category
    if plant_section is not None:
        body["PlantSection"] = plant_section
    if county_reg is not None:
        body["CountyReg"] = county_reg
    if state_reg is not None:
        body["StateReg"] = state_reg
    if country_reg is not None:
        body["CountryReg"] = country_reg
    if country_manuf is not None:
        body["CountryManuf"] = country_manuf
    if planner_group is not None:
        body["PlannerGroup"] = planner_group
    if planning_plant is not None:
        body["PlanningPlant"] = planning_plant
    if identification is not None:
        body["Identification"] = identification
    if aerial_make1_id is not None:
        body["AerialMake1ID"] = aerial_make1_id
    if aerial_model1_id is not None:
        body["AerialModel1ID"] = aerial_model1_id
    if aerial_serial is not None:
        body["AerialSerial"] = aerial_serial
    if aerial_year_built is not None:
        body["AerialYearBuilt"] = aerial_year_built
    if product_filter_type_id is not None:
        body["ProductFilterTypeID"] = product_filter_type_id
    if at_risk_id is not None:
        body["AtRiskID"] = at_risk_id
    if abe_indicator_id is not None:
        body["AbeIndicatorID"] = abe_indicator_id
    if fleet_object_id is not None:
        body["FleetObjectID"] = fleet_object_id
    if leassor_id is not None:
        body["LeassorID"] = leassor_id
    if pmi_type_id is not None:
        body["PmiTypeID"] = pmi_type_id
    if step_config_id is not None:
        body["StepConfigID"] = step_config_id
    if system_status_id is not None:
        body["SystemStatusID"] = system_status_id
    if work_class_id is not None:
        body["WorkClassID"] = work_class_id
    if poi_type_id is not None:
        body["PoiTypeID"] = poi_type_id
    if transmission_serial is not None:
        body["TransmissionSerial"] = transmission_serial
    if front_axel_serial is not None:
        body["FrontAxelSerial"] = front_axel_serial
    if rear_axel_serial is not None:
        body["RearAxelSerial"] = rear_axel_serial
    if front_torque is not None:
        body["FrontTorque"] = front_torque
    if rear_torque is not None:
        body["RearTorque"] = rear_torque
    if city_no_insert_type_id is not None:
        body["CityNoInsertTypeID"] = city_no_insert_type_id
    if city_no_insert_prefix is not None:
        body["CityNoInsertPrefix"] = city_no_insert_prefix
    if belt_type is not None:
        body["BeltType"] = belt_type
    if belt_width_between is not None:
        body["BeltWidthBetween"] = belt_width_between
    if belt_length is not None:
        body["BeltLength"] = belt_length
    if drive_belt_no is not None:
        body["DriveBeltNo"] = drive_belt_no
    if clutch_brake_no is not None:
        body["ClutchBrakeNo"] = clutch_brake_no
    if controller_type is not None:
        body["ControllerType"] = controller_type
    if bed_length is not None:
        body["BedLength"] = bed_length
    if incline_angle is not None:
        body["InclineAngle"] = incline_angle
    if degree_of_turn is not None:
        body["DegreeOfTurn"] = degree_of_turn
    if inside_radius is not None:
        body["InsideRadius"] = inside_radius
    if mfr_motor_framecode is not None:
        body["MfrMotorFramecode"] = mfr_motor_framecode
    if mfr_no is not None:
        body["MfrNo"] = mfr_no
    if master_control_no is not None:
        body["MasterControlNo"] = master_control_no
    if motor_hp is not None:
        body["MotorHp"] = motor_hp
    if oem is not None:
        body["Oem"] = oem
    if reducer_no is not None:
        body["ReducerNo"] = reducer_no
    if is_scale is not None:
        body["IsScale"] = is_scale
    if scale_capacity is not None:
        body["ScaleCapacity"] = scale_capacity
    if scale_length is not None:
        body["ScaleLength"] = scale_length
    if scale_revenue is not None:
        body["ScaleRevenue"] = scale_revenue
    if scale_width is not None:
        body["ScaleWidth"] = scale_width
    if scale_height is not None:
        body["ScaleHeight"] = scale_height
    if motor_no is not None:
        body["MotorNo"] = motor_no
    if motor_mfr is not None:
        body["MotorMfr"] = motor_mfr
    if reducer_mfr is not None:
        body["ReducerMfr"] = reducer_mfr
    if reducer_ratio is not None:
        body["ReducerRatio"] = reducer_ratio
    if workstation1 is not None:
        body["Workstation1"] = workstation1
    if workstation2 is not None:
        body["Workstation2"] = workstation2
    # Mode-specific fields
    if change_to_city_no is not None:
        body["ChangeToCityNo"] = change_to_city_no
    if change_to_equip_type_id is not None:
        body["ChangeToEquipTypeID"] = change_to_equip_type_id
    if transfer_to_city_id is not None:
        body["TransferToCityID"] = transfer_to_city_id
    if transfer_to_work_center_id is not None:
        body["TransferToWorkCenterID"] = transfer_to_work_center_id
    if transfer_to_cost_center_id is not None:
        body["TransferToCostCenterID"] = transfer_to_cost_center_id
    if transfer_date is not None:
        body["TransferDate"] = transfer_date
    if transfer_notes is not None:
        body["TransferNotes"] = transfer_notes
    if transfer_inactivate is not None:
        body["TransferInactivate"] = transfer_inactivate
    if transfer_activate is not None:
        body["TransferActivate"] = transfer_activate
    if transfer_move_open_wos is not None:
        body["TransferMoveOpenWos"] = transfer_move_open_wos
    if transfer_void_open_wos is not None:
        body["TransferVoidOpenWos"] = transfer_void_open_wos
    if power_change_to_power_id is not None:
        body["PowerChangeToPowerID"] = power_change_to_power_id
    if power_change_to_engine_id is not None:
        body["PowerChangeToEngineID"] = power_change_to_engine_id
    if power_change_to_transmission_id is not None:
        body["PowerChangeToTransmissionID"] = power_change_to_transmission_id
    if power_change_notes is not None:
        body["PowerChangeNotes"] = power_change_notes
    if power_change_engine1_serial is not None:
        body["PowerChangeEngine1Serial"] = power_change_engine1_serial
    if power_change_engine1_spec_no is not None:
        body["PowerChangeEngine1SpecNo"] = power_change_engine1_spec_no
    if power_change_engine1_family_code is not None:
        body["PowerChangeEngine1FamilyCode"] = power_change_engine1_family_code
    if power_change_engine1_rpm is not None:
        body["PowerChangeEngine1Rpm"] = power_change_engine1_rpm
    if power_change_engine1_hp is not None:
        body["PowerChangeEngine1HP"] = power_change_engine1_hp
    if power_change_engine1_capacity is not None:
        body["PowerChangeEngine1Capacity"] = power_change_engine1_capacity
    if power_change_engine1_num_cyl is not None:
        body["PowerChangeEngine1NumCyl"] = power_change_engine1_num_cyl
    if power_change_engine1_model_year is not None:
        body["PowerChangeEngine1ModelYear"] = power_change_engine1_model_year
    # Generic name-based lookups
    if engine_id is not None:
        body["EngineID"] = engine_id
    if make_id is not None:
        body["MakeID"] = make_id
    if model_id is not None:
        body["ModelID"] = model_id
    if power_id is not None:
        body["PowerID"] = power_id
    if telemetry_profile_id is not None:
        body["TelemetryProfileID"] = telemetry_profile_id
    if transmission_id is not None:
        body["TransmissionID"] = transmission_id
    if vendor_id is not None:
        body["VendorID"] = vendor_id
    if user_validate_temp_token is not None:
        body["UserValidateTempToken"] = user_validate_temp_token

    return _post("equipment/addupdate", body)


# ---------------------------------------------------------------------------
# Meter Readings tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_meter_reading_lists(list_names: list[str] | None = None) -> dict:
    """
    Retrieve the supporting reference lists used when querying meter readings.

    Available list names: CityID, ControllerID, CostCenterID, CustomerID, DepartmentID,
    Engine1ID, FleetConfigID, Make1ID, MeterProfileID, Model1ID, MotorID, PartsCatalogID,
    PmDocID, Power1ID, RegionID, TelemetryIntegID, UserStatusID, VehicleTypeID,
    WorkCenterID, ZoneID.

    Args:
        list_names: Optional list of specific list names to return,
                    e.g. ["CityID", "MeterProfileID"]. If omitted, all lists are returned.

    Returns:
        Dict of requested reference lists, each containing {ID, Name} entries.
    """
    params = {}
    if list_names:
        params["name"] = ",".join(list_names)
    return _get("equipment/meter/lists", params=params)


@mcp.tool()
def get_meter_readings(
    reading_dates: list[str],
    after_paint_date: list[str] | None = None,
    any_license_due_next_days: int | None = None,
    asset_no: str | None = None,
    asset_no_multiple: list[str] | None = None,
    banner_status: str | None = None,
    battery_mgmt_id: str | None = None,
    city_ids: list[int | str] | None = None,
    city_no_like: str | None = None,
    city_no_multiple: list[str] | None = None,
    contractor: str | None = None,
    controller_ids: list[int | str] | None = None,
    cost_center_ids: list[int | str] | None = None,
    customer_ids: list[int | str] | None = None,
    department_ids: list[int | str] | None = None,
    ebis_ids: list[int] | None = None,
    engine1_ids: list[int | str] | None = None,
    engine1_serial: str | None = None,
    engine1_spec_no: str | None = None,
    fleet_config_ids: list[int | str] | None = None,
    front_axel_serial: str | None = None,
    has_date_based_schedule: bool = False,
    has_license_no: str | None = None,
    has_linked_parts_list_override: str | None = None,
    has_meter_based_schedule: bool = False,
    has_pm_part_kit: str | None = None,
    has_pm_part_kit_override: str | None = None,
    has_pm_schedules: str | None = None,
    has_seatbelt: str | None = None,
    inactive_include: bool = False,
    last_pm_over_days_ago: int | None = None,
    lease_expires_next_days: int | None = None,
    license_no: str | None = None,
    make1_ids: list[int | str] | None = None,
    meter_profile_ids: list[int | str] | None = None,
    model1_ids: list[int | str] | None = None,
    motor_ids: list[int | str] | None = None,
    only_inactive: bool = False,
    only_with_telemetry: bool = False,
    only_with_valid_warranty: bool = False,
    parts_catalog_ids: list[int | str] | None = None,
    pm_doc_ids: list[int | str] | None = None,
    power1_ids: list[int | str] | None = None,
    rear_axel_serial: str | None = None,
    reflectivity: str | None = None,
    region_ids: list[int | str] | None = None,
    rental_expires_next_days: int | None = None,
    serial_no: str | None = None,
    show_license_no: bool = False,
    stationary_loc_multiple: list[str] | None = None,
    surplus: str | None = None,
    telemetry_integ_ids: list[int | str] | None = None,
    telemetry_key: str | None = None,
    transmission_serial: str | None = None,
    user_status_ids: list[int | str] | None = None,
    vehicle_type_ids: list[int | str] | None = None,
    vin: str | None = None,
    warranty_expires_in_days: int | None = None,
    work_center_ids: list[int | str] | None = None,
    year_built: list[int] | None = None,
    zone_ids: list[int | str] | None = None,
    hierarchy: str = "nested",
    id_accessible: bool = False,
    language: str | None = None,
) -> dict:
    """
    Retrieve meter reading history for selected equipment.

    Use get_meter_reading_lists() to discover valid ID/name values for
    any of the ID filter parameters.

    Args:
        reading_dates: (Required) Date range to retrieve readings within,
                       e.g. ["2024-01-01", "2024-01-31"].
        after_paint_date: Filter equipment painted after these dates.
        any_license_due_next_days: Return equipment with any license due within N days.
        asset_no: Fragment search on asset number.
        asset_no_multiple: Filter by multiple exact asset numbers.
        banner_status: Fragment search on banner status.
        battery_mgmt_id: Fragment search on battery management ID.
        city_ids: Filter by city IDs or names.
        city_no_like: Fragment search on city number.
        city_no_multiple: Filter by multiple exact city numbers.
        contractor: Filter by contractor status — "yes", "no", or "all".
        controller_ids: Filter by controller IDs or names.
        cost_center_ids: Filter by cost center IDs or names.
        customer_ids: Filter by customer IDs or names.
        department_ids: Filter by department IDs or names.
        ebis_ids: Filter by specific eBis equipment IDs.
        engine1_ids: Filter by primary engine IDs or names.
        engine1_serial: Fragment search on primary engine serial number.
        engine1_spec_no: Fragment search on primary engine spec number.
        fleet_config_ids: Filter by fleet configuration IDs or names.
        front_axel_serial: Fragment search on front axle serial number.
        has_date_based_schedule: If True, return only equipment with a date-based PM schedule.
        has_license_no: Filter by license number presence — "yes", "no", or "all".
        has_linked_parts_list_override: Filter by linked parts list override — "yes", "no", or "all".
        has_meter_based_schedule: If True, return only equipment with a meter-based PM schedule.
        has_pm_part_kit: Filter by PM part kit presence — "yes", "no", or "all".
        has_pm_part_kit_override: Filter by PM part kit override — "yes", "no", or "all".
        has_pm_schedules: Filter by PM schedule presence — "yes", "no", or "all".
        has_seatbelt: Filter by seatbelt presence — "yes", "no", or "all".
        inactive_include: If True, include inactive equipment.
        last_pm_over_days_ago: Return equipment whose last PM was more than N days ago.
        lease_expires_next_days: Return equipment whose lease expires within N days.
        license_no: Fragment search on license number.
        make1_ids: Filter by primary make IDs or names.
        meter_profile_ids: Filter by meter profile IDs or names.
        model1_ids: Filter by primary model IDs or names.
        motor_ids: Filter by motor IDs or names.
        only_inactive: If True, return only inactive equipment.
        only_with_telemetry: If True, return only equipment with telemetry.
        only_with_valid_warranty: If True, return only equipment with a valid warranty.
        parts_catalog_ids: Filter by parts catalog IDs or names.
        pm_doc_ids: Filter by PM document IDs or names.
        power1_ids: Filter by primary power source IDs or names.
        rear_axel_serial: Fragment search on rear axle serial number.
        reflectivity: Filter by reflectivity status — "yes", "no", or "all".
        region_ids: Filter by region IDs or names.
        rental_expires_next_days: Return equipment whose rental expires within N days.
        serial_no: Fragment search on equipment serial number.
        show_license_no: If True, include license number fields in the response.
        stationary_loc_multiple: Filter by multiple stationary location values.
        surplus: Filter by surplus status — "yes", "no", or "all".
        telemetry_integ_ids: Filter by telemetry integration IDs or names.
        telemetry_key: Fragment search on telemetry key.
        transmission_serial: Fragment search on transmission serial number.
        user_status_ids: Filter by user status IDs or names.
        vehicle_type_ids: Filter by vehicle type IDs or names.
        vin: Fragment search on VIN.
        warranty_expires_in_days: Return equipment whose warranty expires within N days.
        work_center_ids: Filter by work center IDs or names.
        year_built: Filter by year(s) built, e.g. [2001, 2002].
        zone_ids: Filter by zone IDs or names.
        hierarchy: Response structure — "nested" (default) or "flat".
                   Nested hierarchy: Equipment > Readings > Dates.
        id_accessible: If True, child lists are keyed by ID rather than returned as arrays.
        language: Language for generic list parameter lookups (default: "English").

    Returns:
        Meter reading history records for the matching equipment within the date range.
    """
    body: dict[str, Any] = {
        "ReadingDates": reading_dates,
    }

    if after_paint_date is not None:
        body["AfterPaintDate"] = after_paint_date
    if any_license_due_next_days is not None:
        body["AnyLicenseDueNextDays"] = any_license_due_next_days
    if asset_no is not None:
        body["AssetNo"] = asset_no
    if asset_no_multiple is not None:
        body["AssetNoMultiple"] = asset_no_multiple
    if banner_status is not None:
        body["BannerStatus"] = banner_status
    if battery_mgmt_id is not None:
        body["BatteryMgmtID"] = battery_mgmt_id
    if city_ids is not None:
        body["CityID"] = city_ids
    if city_no_like is not None:
        body["CityNoLike"] = city_no_like
    if city_no_multiple is not None:
        body["CityNoMultiple"] = city_no_multiple
    if contractor is not None:
        body["Contractor"] = contractor
    if controller_ids is not None:
        body["ControllerID"] = controller_ids
    if cost_center_ids is not None:
        body["CostCenterID"] = cost_center_ids
    if customer_ids is not None:
        body["CustomerID"] = customer_ids
    if department_ids is not None:
        body["DepartmentID"] = department_ids
    if ebis_ids is not None:
        body["EBisID"] = ebis_ids
    if engine1_ids is not None:
        body["Engine1ID"] = engine1_ids
    if engine1_serial is not None:
        body["Engine1Serial"] = engine1_serial
    if engine1_spec_no is not None:
        body["Engine1SpecNo"] = engine1_spec_no
    if fleet_config_ids is not None:
        body["FleetConfigID"] = fleet_config_ids
    if front_axel_serial is not None:
        body["FrontAxelSerial"] = front_axel_serial
    if has_date_based_schedule:
        body["HasDateBasedSchedule"] = True
    if has_license_no is not None:
        body["HasLicenseNo"] = has_license_no
    if has_linked_parts_list_override is not None:
        body["HasLinkedPartsListOverride"] = has_linked_parts_list_override
    if has_meter_based_schedule:
        body["HasMeterBasedSchedule"] = True
    if has_pm_part_kit is not None:
        body["HasPmPartKit"] = has_pm_part_kit
    if has_pm_part_kit_override is not None:
        body["HasPmPartKitOverride"] = has_pm_part_kit_override
    if has_pm_schedules is not None:
        body["HasPmSchedules"] = has_pm_schedules
    if has_seatbelt is not None:
        body["HasSeatbelt"] = has_seatbelt
    if inactive_include:
        body["InactiveInclude"] = True
    if last_pm_over_days_ago is not None:
        body["LastPmOverDaysAgo"] = last_pm_over_days_ago
    if lease_expires_next_days is not None:
        body["LeaseExpiresNextDays"] = lease_expires_next_days
    if license_no is not None:
        body["LicenseNo"] = license_no
    if make1_ids is not None:
        body["Make1ID"] = make1_ids
    if meter_profile_ids is not None:
        body["MeterProfileID"] = meter_profile_ids
    if model1_ids is not None:
        body["Model1ID"] = model1_ids
    if motor_ids is not None:
        body["MotorID"] = motor_ids
    if only_inactive:
        body["OnlyInactive"] = True
    if only_with_telemetry:
        body["OnlyWithTelemetry"] = True
    if only_with_valid_warranty:
        body["OnlyWithValidWarranty"] = True
    if parts_catalog_ids is not None:
        body["PartsCatalogID"] = parts_catalog_ids
    if pm_doc_ids is not None:
        body["PmDocID"] = pm_doc_ids
    if power1_ids is not None:
        body["Power1ID"] = power1_ids
    if rear_axel_serial is not None:
        body["RearAxelSerial"] = rear_axel_serial
    if reflectivity is not None:
        body["Reflectivity"] = reflectivity
    if region_ids is not None:
        body["RegionID"] = region_ids
    if rental_expires_next_days is not None:
        body["RentalExpiresNextDays"] = rental_expires_next_days
    if serial_no is not None:
        body["SerialNo"] = serial_no
    if show_license_no:
        body["ShowLicenseNo"] = True
    if stationary_loc_multiple is not None:
        body["StationaryLocMultiple"] = stationary_loc_multiple
    if surplus is not None:
        body["Surplus"] = surplus
    if telemetry_integ_ids is not None:
        body["TelemetryIntegID"] = telemetry_integ_ids
    if telemetry_key is not None:
        body["TelemetryKey"] = telemetry_key
    if transmission_serial is not None:
        body["TransmissionSerial"] = transmission_serial
    if user_status_ids is not None:
        body["UserStatusID"] = user_status_ids
    if vehicle_type_ids is not None:
        body["VehicleTypeID"] = vehicle_type_ids
    if vin is not None:
        body["Vin"] = vin
    if warranty_expires_in_days is not None:
        body["WarrantyExpiresInDays"] = warranty_expires_in_days
    if work_center_ids is not None:
        body["WorkCenterID"] = work_center_ids
    if year_built is not None:
        body["YearBuilt"] = year_built
    if zone_ids is not None:
        body["ZoneID"] = zone_ids
    if hierarchy != "nested":
        body["Hierarchy"] = hierarchy
    if id_accessible:
        body["IDAccessible"] = True
    if language is not None:
        body["Language"] = language

    return _post("equipment/meter", body)


# ---------------------------------------------------------------------------
# Equipment Batch Meter Reading Add/Update tool
# ---------------------------------------------------------------------------

@mcp.tool()
def add_update_meter_readings(
    assets: list[dict],
    apply_timezone_conversion: bool = False,
    use_reading_date: bool = False,
) -> dict:
    """
    Add or update meter readings for a batch of equipment.

    Each asset in the `assets` list must include one of: EBisID, RegNum, or
    TelemetryVendorAssetNo to identify the equipment, plus a Reading value.

    Reading formats (three options per asset):
    - **Primary only**: `{"EBisID": 101, "Reading": 6773}`
      Single decimal — interpreted as the primary reading.
    - **By name/sort**: `{"EBisID": 101, "Reading": [{"Name": "Run Hours", "Value": 0}, {"SortNum": 1, "Value": 1}]}`
      List of objects with Name or SortNum plus Value.
    - **By order**: `{"EBisID": 101, "Reading": [101, 202]}`
      List of decimals matched by position to the meter profile's readings.

    Optional per-asset fields:
    - LineNumber (int): Returned in the response to correlate results.
    - OverrideDate (str): Reading date override, e.g. "2021-01-01". Defaults to submission date.

    Args:
        assets: (Required) List of asset reading dicts. See above for format options.
        apply_timezone_conversion: If True, apply timezone conversion to reading timestamps.
        use_reading_date: If True, use the reading date rather than the submission date.

    Returns:
        Per-asset results, each with EBisID, LineNumber, ProfileName, MessageID,
        MessageText, and a Readings list with per-reading MessageID and MessageText.
        MessageID is "OK" if all readings for that asset succeeded.
    """
    body: dict[str, Any] = {
        "Assets": assets,
    }

    if apply_timezone_conversion:
        body["ApplyTimezoneConversion"] = True
    if use_reading_date:
        body["UseReadingDate"] = True

    return _post("equipment/meter/addupdate", body)


# ---------------------------------------------------------------------------
# Upcoming PM tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_upcoming_pm_lists(list_names: list[str] | None = None) -> dict:
    """
    Retrieve the supporting reference lists used when querying upcoming PMs.

    Available list names: CityID, RegionID, SummarizeBy, SummarizeByDateGroup,
    VehicleTypeID, ZoneID.

    Args:
        list_names: Optional list of specific list names to return,
                    e.g. ["CityID", "SummarizeBy"]. If omitted, all lists are returned.

    Returns:
        Dict of requested reference lists, each containing {ID, Name} entries.
    """
    params = {}
    if list_names:
        params["name"] = ",".join(list_names)
    return _get("equipment/pmupcoming/lists", params=params)


@mcp.tool()
def get_upcoming_pm(
    city_ids: list[int | str] | None = None,
    is_powered: str | None = None,
    region_ids: list[int | str] | None = None,
    show_all_upcoming_wo: bool = False,
    summarize_by: int | str | None = None,
    summarize_by_date_group: int | str | None = None,
    vehicle_type_ids: list[int | str] | None = None,
    zone_ids: list[int | str] | None = None,
    id_accessible: bool = False,
    language: str | None = None,
) -> dict:
    """
    Retrieve upcoming preventive maintenance (PM) information for equipment.

    Use get_upcoming_pm_lists() to discover valid ID/name values for any
    of the ID filter parameters, including SummarizeBy and SummarizeByDateGroup options.

    Args:
        city_ids: Filter by city IDs or names.
        is_powered: Filter by powered status — "yes", "no", or "all".
        region_ids: Filter by region IDs or names.
        show_all_upcoming_wo: If True, include all upcoming work orders, not just the next due.
        summarize_by: Group/summarize results by this field ID or name.
                      Use get_upcoming_pm_lists(["SummarizeBy"]) to see options.
        summarize_by_date_group: Secondary date grouping for the summary.
                                 Use get_upcoming_pm_lists(["SummarizeByDateGroup"]) to see options.
        vehicle_type_ids: Filter by vehicle type IDs or names.
        zone_ids: Filter by zone IDs or names.
        id_accessible: If True, child lists are keyed by ID rather than returned as arrays.
        language: Language for generic list parameter lookups (default: "English").

    Returns:
        Upcoming PM records for matching equipment.
    """
    body: dict[str, Any] = {}

    if city_ids is not None:
        body["CityID"] = city_ids
    if is_powered is not None:
        body["IsPowered"] = is_powered
    if region_ids is not None:
        body["RegionID"] = region_ids
    if show_all_upcoming_wo:
        body["ShowAllUpcomingWo"] = True
    if summarize_by is not None:
        body["SummarizeBy"] = summarize_by
    if summarize_by_date_group is not None:
        body["SummarizeByDateGroup"] = summarize_by_date_group
    if vehicle_type_ids is not None:
        body["VehicleTypeID"] = vehicle_type_ids
    if zone_ids is not None:
        body["ZoneID"] = zone_ids
    if id_accessible:
        body["IDAccessible"] = True
    if language is not None:
        body["Language"] = language

    return _post("equipment/pmupcoming", body)


# ---------------------------------------------------------------------------
# Master Part Listing tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_masterpart_listing_lists(list_names: list[str] | None = None) -> dict:
    """
    Retrieve the supporting reference lists used when querying the master part list.

    Available list names: PartComponentID, PartTypeID, SupplierID.

    Args:
        list_names: Optional list of specific list names to return,
                    e.g. ["PartComponentID", "SupplierID"]. If omitted, all lists are returned.

    Returns:
        Dict of requested reference lists, each containing {ID, Name} entries.
    """
    params = {}
    if list_names:
        params["name"] = ",".join(list_names)
    return _get("masterpart/listing/lists", params=params)


@mcp.tool()
def get_masterpart_listing(
    core_is: str | None = None,
    description_like: str | None = None,
    expiring_shelf_life: int | None = None,
    family_name: str | None = None,
    general_cost_range: list[int | float] | None = None,
    general_location_range: list[str] | None = None,
    has_alternate: str | None = None,
    has_general_cost: str | None = None,
    has_general_location: bool = False,
    has_media: str | None = None,
    has_superseded: str | None = None,
    has_unspsc: str | None = None,
    has_warranty_days: str | None = None,
    hazard_is: str | None = None,
    is_serial: str | None = None,
    line_code: str | None = None,
    no_inv_movement: bool = False,
    no_inv_movement_days: int | None = None,
    part_component_ids: list[int | str] | None = None,
    part_number_like: str | None = None,
    part_number_range: list[str] | None = None,
    part_type_ids: list[int | str] | None = None,
    specific_location_range: list[str] | None = None,
    supplier_ids: list[int | str] | None = None,
    unspsc: str | None = None,
    id_accessible: bool = False,
) -> dict:
    """
    Retrieve general master part list information including part number, description,
    part component, shelf life, costs, locations, and more.

    Use get_masterpart_listing_lists() to discover valid ID/name values for
    any of the ID filter parameters.

    Args:
        core_is: Filter by core part status — "yes", "no", or "all".
        description_like: Fragment search on part description.
        expiring_shelf_life: Return parts whose shelf life expires within N days.
        family_name: Fragment search on part family name.
        general_cost_range: Filter by general cost range as [min, max], e.g. [2.0, 10.5].
        general_location_range: Filter by general location range as [start, end].
        has_alternate: Filter by alternate part presence — "yes", "no", or "all".
        has_general_cost: Filter by general cost presence — "yes", "no", or "all".
        has_general_location: If True, return only parts that have a general location.
        has_media: Filter by media attachment presence — "yes", "no", or "all".
        has_superseded: Filter by superseded part presence — "yes", "no", or "all".
        has_unspsc: Filter by UNSPSC code presence — "yes", "no", or "all".
        has_warranty_days: Filter by warranty days presence — "yes", "no", or "all".
        hazard_is: Filter by hazardous material status — "yes", "no", or "all".
        is_serial: Filter by serialised part status — "yes", "no", or "all".
        line_code: Fragment search on part line code.
        no_inv_movement: If True, return only parts with no inventory movement.
        no_inv_movement_days: Return parts with no inventory movement in the last N days.
        part_component_ids: Filter by part component IDs or names.
        part_number_like: Fragment search on part number.
        part_number_range: Filter by part number range as [start, end].
        part_type_ids: Filter by part type IDs or names.
        specific_location_range: Filter by specific location range as [start, end].
        supplier_ids: Filter by supplier IDs or names.
        unspsc: Search on UNSPSC code.
        id_accessible: If True, child lists are keyed by ID rather than returned as arrays.

    Returns:
        Master part list records matching the requested filters.
    """
    body: dict[str, Any] = {}

    if core_is is not None:
        body["CoreIs"] = core_is
    if description_like is not None:
        body["DescriptionLike"] = description_like
    if expiring_shelf_life is not None:
        body["ExpiringShelfLife"] = expiring_shelf_life
    if family_name is not None:
        body["FamilyName"] = family_name
    if general_cost_range is not None:
        body["GeneralCostRange"] = general_cost_range
    if general_location_range is not None:
        body["GeneralLocationRange"] = general_location_range
    if has_alternate is not None:
        body["HasAlternate"] = has_alternate
    if has_general_cost is not None:
        body["HasGeneralCost"] = has_general_cost
    if has_general_location:
        body["HasGeneralLocation"] = True
    if has_media is not None:
        body["HasMedia"] = has_media
    if has_superseded is not None:
        body["HasSuperseded"] = has_superseded
    if has_unspsc is not None:
        body["HasUnspsc"] = has_unspsc
    if has_warranty_days is not None:
        body["HasWarrantyDays"] = has_warranty_days
    if hazard_is is not None:
        body["HazardIs"] = hazard_is
    if is_serial is not None:
        body["IsSerial"] = is_serial
    if line_code is not None:
        body["LineCode"] = line_code
    if no_inv_movement:
        body["NoInvMovement"] = True
    if no_inv_movement_days is not None:
        body["NoInvMovementDays"] = no_inv_movement_days
    if part_component_ids is not None:
        body["PartComponentID"] = part_component_ids
    if part_number_like is not None:
        body["PartNumberLike"] = part_number_like
    if part_number_range is not None:
        body["PartNumberRange"] = part_number_range
    if part_type_ids is not None:
        body["PartTypeID"] = part_type_ids
    if specific_location_range is not None:
        body["SpecificLocationRange"] = specific_location_range
    if supplier_ids is not None:
        body["SupplierID"] = supplier_ids
    if unspsc is not None:
        body["Unspsc"] = unspsc
    if id_accessible:
        body["IDAccessible"] = True

    return _post("masterpart/listing", body)


# ---------------------------------------------------------------------------
# Stock Quantity Detail tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_stock_quantity_detail_lists(list_names: list[str] | None = None) -> dict:
    """
    Retrieve the supporting reference lists used when querying stock quantity detail.

    Available list names: PartComponentID, PartTypeID, StockRoomID, SupplierID.

    Args:
        list_names: Optional list of specific list names to return,
                    e.g. ["StockRoomID", "SupplierID"]. If omitted, all lists are returned.

    Returns:
        Dict of requested reference lists, each containing {ID, Name} entries.
    """
    params = {}
    if list_names:
        params["name"] = ",".join(list_names)
    return _get("masterpart/quantity/detail/lists", params=params)


@mcp.tool()
def get_stock_quantity_detail(
    core_is: str | None = None,
    description_like: str | None = None,
    family_name: str | None = None,
    general_location_range: list[str] | None = None,
    has_alternate: str | None = None,
    has_media: str | None = None,
    has_superseded: str | None = None,
    has_warranty_days: str | None = None,
    hazard_is: str | None = None,
    is_serial: str | None = None,
    line_code: str | None = None,
    part_component_ids: list[int | str] | None = None,
    part_number_like: str | None = None,
    part_number_range: list[str] | None = None,
    part_type_ids: list[int | str] | None = None,
    qty_customer: int | None = None,
    qty_location_range: list[str] | None = None,
    qty_po_number: str | None = None,
    qty_serial: str | None = None,
    qty_vendor: str | None = None,
    shelf_life_expires_days: int | None = None,
    stock_qty: int | None = None,
    stock_room_ids: list[int | str] | None = None,
    supplier_ids: list[int | str] | None = None,
    id_accessible: bool = False,
) -> dict:
    """
    Retrieve basic part information and detailed stock quantity data.

    Use get_stock_quantity_detail_lists() to discover valid ID/name values for
    any of the ID filter parameters.

    Args:
        core_is: Filter by core part status — "yes", "no", or "all".
        description_like: Fragment search on part description.
        family_name: Fragment search on part family name.
        general_location_range: Filter by general location range as [start, end].
        has_alternate: Filter by alternate part presence — "yes", "no", or "all".
        has_media: Filter by media attachment presence — "yes", "no", or "all".
        has_superseded: Filter by superseded part presence — "yes", "no", or "all".
        has_warranty_days: Filter by warranty days presence — "yes", "no", or "all".
        hazard_is: Filter by hazardous material status — "yes", "no", or "all".
        is_serial: Filter by serialised part status — "yes", "no", or "all".
        line_code: Fragment search on part line code.
        part_component_ids: Filter by part component IDs or names.
        part_number_like: Fragment search on part number.
        part_number_range: Filter by part number range as [start, end].
        part_type_ids: Filter by part type IDs or names.
        qty_customer: Filter by stock quantity customer ID.
        qty_location_range: Filter stock rows by location range as [start, end].
        qty_po_number: Fragment search on the PO number associated with stock quantity rows.
        qty_serial: Fragment search on serial number within stock quantity rows.
        qty_vendor: Fragment search on vendor within stock quantity rows.
        shelf_life_expires_days: Return parts whose shelf life expires within N days.
        stock_qty: Filter by a specific stock quantity value.
        stock_room_ids: Filter by stock room IDs or names.
        supplier_ids: Filter by supplier IDs or names.
        id_accessible: If True, child lists are keyed by ID rather than returned as arrays.

    Returns:
        Stock quantity detail records matching the requested filters.
    """
    body: dict[str, Any] = {}

    if core_is is not None:
        body["CoreIs"] = core_is
    if description_like is not None:
        body["DescriptionLike"] = description_like
    if family_name is not None:
        body["FamilyName"] = family_name
    if general_location_range is not None:
        body["GeneralLocationRange"] = general_location_range
    if has_alternate is not None:
        body["HasAlternate"] = has_alternate
    if has_media is not None:
        body["HasMedia"] = has_media
    if has_superseded is not None:
        body["HasSuperseded"] = has_superseded
    if has_warranty_days is not None:
        body["HasWarrantyDays"] = has_warranty_days
    if hazard_is is not None:
        body["HazardIs"] = hazard_is
    if is_serial is not None:
        body["IsSerial"] = is_serial
    if line_code is not None:
        body["LineCode"] = line_code
    if part_component_ids is not None:
        body["PartComponentID"] = part_component_ids
    if part_number_like is not None:
        body["PartNumberLike"] = part_number_like
    if part_number_range is not None:
        body["PartNumberRange"] = part_number_range
    if part_type_ids is not None:
        body["PartTypeID"] = part_type_ids
    if qty_customer is not None:
        body["QtyCustomer"] = qty_customer
    if qty_location_range is not None:
        body["QtyLocationRange"] = qty_location_range
    if qty_po_number is not None:
        body["QtyPoNumber"] = qty_po_number
    if qty_serial is not None:
        body["QtySerial"] = qty_serial
    if qty_vendor is not None:
        body["QtyVendor"] = qty_vendor
    if shelf_life_expires_days is not None:
        body["ShelfLifeExpiresDays"] = shelf_life_expires_days
    if stock_qty is not None:
        body["StockQty"] = stock_qty
    if stock_room_ids is not None:
        body["StockRoomID"] = stock_room_ids
    if supplier_ids is not None:
        body["SupplierID"] = supplier_ids
    if id_accessible:
        body["IDAccessible"] = True

    return _post("masterpart/quantity/detail", body)


# ---------------------------------------------------------------------------
# Stock Quantity Log tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_stock_quantity_log_lists(list_names: list[str] | None = None) -> dict:
    """
    Retrieve the supporting reference lists used when querying the stock quantity log.

    Available list names: StockRoomID.

    Args:
        list_names: Optional list of specific list names to return,
                    e.g. ["StockRoomID"]. If omitted, all lists are returned.

    Returns:
        Dict of requested reference lists, each containing {ID, Name} entries.
    """
    params = {}
    if list_names:
        params["name"] = ",".join(list_names)
    return _get("masterpart/quantity/log/lists", params=params)


@mcp.tool()
def get_stock_quantity_log(
    dates: list[str],
    description_like: str | None = None,
    part_number_like: str | None = None,
    stock_room_ids: list[int | str] | None = None,
    user: str | None = None,
    id_accessible: bool = False,
    debug_sql: bool = False,
) -> dict:
    """
    Retrieve detailed information about inventory quantity and cost changes.

    Use get_stock_quantity_log_lists() to discover valid StockRoomID values.

    Args:
        dates: (Required) Date range to retrieve log entries within,
               e.g. ["2024-01-01", "2024-01-31"].
        description_like: Fragment search on part description.
        part_number_like: Fragment search on part number.
        stock_room_ids: Filter by stock room IDs or names.
        user: Fragment search on the username that made the inventory change.
        id_accessible: If True, child lists are keyed by ID rather than returned as arrays.
        debug_sql: Enable SQL debug output (dev/testing use).

    Returns:
        Stock quantity log records showing inventory quantity and cost changes
        within the requested date range.
    """
    body: dict[str, Any] = {
        "Date": dates,
    }

    if description_like is not None:
        body["DescriptionLike"] = description_like
    if part_number_like is not None:
        body["PartNumberLike"] = part_number_like
    if stock_room_ids is not None:
        body["StockRoomID"] = stock_room_ids
    if user is not None:
        body["User"] = user
    if id_accessible:
        body["IDAccessible"] = True
    if debug_sql:
        body["DebugSql"] = True

    return _post("masterpart/quantity/log", body)


# ---------------------------------------------------------------------------
# Purchase Order Export tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_purchase_order_lists(list_names: list[str] | None = None) -> dict:
    """
    Retrieve the supporting reference lists used when querying purchase orders.

    Available list names: CityID, IbsID, RegionID, StatusID, VendorID.

    Args:
        list_names: Optional list of specific list names to return,
                    e.g. ["CityID", "VendorID"]. If omitted, all lists are returned.

    Returns:
        Dict of requested reference lists, each containing {ID, Name} entries.
    """
    params = {}
    if list_names:
        params["name"] = ",".join(list_names)
    return _get("purchaseorder/lists", params=params)


@mcp.tool()
def export_purchase_orders(
    city_ids: list[int | str] | None = None,
    completed_dates: list[str] | None = None,
    created_by_user: str | None = None,
    ibs_ids: list[int | str] | None = None,
    include_item_destination_detail: bool = False,
    include_item_detail: bool = False,
    include_receiving_info: bool = False,
    inspect_dates: list[str] | None = None,
    ordered_dates: list[str] | None = None,
    part_number: str | None = None,
    received_dates: list[str] | None = None,
    region_ids: list[int | str] | None = None,
    rma_number: str | None = None,
    status_ids: list[int | str] | None = None,
    vendor_ids: list[int | str] | None = None,
    hierarchy: str = "flat",
    id_accessible: bool = False,
) -> dict:
    """
    Export purchase order listings including parts and destinations.

    Use get_purchase_order_lists() to discover valid ID/name values for
    any of the ID filter parameters.

    Args:
        city_ids: Filter by city IDs or names.
        completed_dates: Filter by PO completion date(s), e.g. ["2024-01-25"].
        created_by_user: Fragment search on the username that created the PO.
        ibs_ids: Filter by IBS IDs or names.
        include_item_destination_detail: If True, include destination detail for each PO item.
        include_item_detail: If True, include line item detail for each PO.
        include_receiving_info: If True, include receiving information for each PO.
        inspect_dates: Filter by inspection date(s), e.g. ["2024-01-25"].
        ordered_dates: Filter by order date(s), e.g. ["2024-01-25"].
        part_number: Fragment search on part number.
        received_dates: Filter by received date(s), e.g. ["2024-01-25"].
        region_ids: Filter by region IDs or names.
        rma_number: Fragment search on RMA number.
        status_ids: Filter by PO status IDs or names.
        vendor_ids: Filter by vendor IDs or names.
        hierarchy: Response structure — "flat" (default) or "nested".
                   Nested hierarchy: PurchaseOrders > PoItems > Destinations, Receiving, Media.
        id_accessible: If True, child lists are keyed by ID rather than returned as arrays.

    Returns:
        Purchase order records matching the requested filters, optionally including
        item detail, destination detail, and receiving information.
    """
    body: dict[str, Any] = {}

    if city_ids is not None:
        body["CityID"] = city_ids
    if completed_dates is not None:
        body["CompletedDate"] = completed_dates
    if created_by_user is not None:
        body["CreatedByUser"] = created_by_user
    if ibs_ids is not None:
        body["IbsID"] = ibs_ids
    if include_item_destination_detail:
        body["IncludeItemDestinationDetail"] = True
    if include_item_detail:
        body["IncludeItemDetail"] = True
    if include_receiving_info:
        body["IncludeReceivingInfo"] = True
    if inspect_dates is not None:
        body["InspectDate"] = inspect_dates
    if ordered_dates is not None:
        body["OrderedDate"] = ordered_dates
    if part_number is not None:
        body["PartNumber"] = part_number
    if received_dates is not None:
        body["ReceivedDate"] = received_dates
    if region_ids is not None:
        body["RegionID"] = region_ids
    if rma_number is not None:
        body["RmaNumber"] = rma_number
    if status_ids is not None:
        body["StatusID"] = status_ids
    if vendor_ids is not None:
        body["VendorID"] = vendor_ids
    if hierarchy != "flat":
        body["Hierarchy"] = hierarchy
    if id_accessible:
        body["IDAccessible"] = True

    return _post("purchaseorder", body)


# ---------------------------------------------------------------------------
# Service Request Add/Update tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_service_request_addupdate_lists(list_names: list[str] | None = None) -> dict:
    """
    Retrieve the supporting reference lists used when adding or updating service requests.

    Available list names: StatusID, CategoryID, PriorityID.

    Args:
        list_names: Optional list of specific list names to return,
                    e.g. ["CategoryID", "PriorityID"]. If omitted, all lists are returned.

    Returns:
        Dict of requested reference lists, each containing {ID, Name} entries.
    """
    params = {}
    if list_names:
        params["name"] = ",".join(list_names)
    return _get("servicerequest/addupdate/lists", params=params)


@mcp.tool()
def add_update_service_request(
    mode: str,
    asset_related_id: int | None = None,
    id: int | None = None,
    sr_number: str | None = None,
    status_id: int | None = None,
    category_id: int | None = None,
    priority_id: int | None = None,
    description: str | None = None,
    location: str | None = None,
    request_by_name: str | None = None,
    request_by_phone: str | None = None,
    request_by_email: str | None = None,
    request_by_location: str | None = None,
    did_tag_equipment: bool | None = None,
    defer_reject_notes: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    is_system_created: bool | None = None,
    is_invalid_telemetry_reason: str | None = None,
    extra_log_info: str | None = None,
    debug_notifications: bool = False,
) -> dict:
    """
    Add or update a service request in eBis Cloud.

    Use get_service_request_addupdate_lists() to find valid IDs for
    StatusID, CategoryID, and PriorityID. Name strings are also accepted
    (e.g. category_id="Abuse", priority_id="Red Tag").

    Mode values:
    - "Insert": Create a new service request. Requires asset_related_id, description,
                location, category_id, priority_id, request_by_name, request_by_location.
    - "Update": Update an existing service request. Requires id or sr_number.

    Args:
        mode: (Required) "Insert" to create, "Update" to modify an existing record.
        asset_related_id: Equipment ID to associate with the service request
                          (alias: EquipmentID). Required for Insert.
        id: eBis service request ID — used to identify the record for Update.
        sr_number: Service request number — alternative identifier for Update.
        status_id: Status ID for the service request.
        category_id: Category ID or name (e.g. "Abuse"). Required for Insert.
        priority_id: Priority ID or name (e.g. "Red Tag"). Required for Insert.
        description: Description / reason for the service request. Required for Insert.
        location: Physical location of the equipment. Required for Insert.
        request_by_name: Name of the person making the request. Required for Insert.
        request_by_phone: Phone number of the requestor.
        request_by_email: Email address of the requestor.
        request_by_location: Location of the requestor (e.g. "Terminal 1"). Required for Insert.
        did_tag_equipment: Whether the equipment was physically tagged.
        defer_reject_notes: Notes for a deferred or rejected service request.
        latitude: GPS latitude of the equipment location.
        longitude: GPS longitude of the equipment location.
        is_system_created: If True, mark the record as system-created.
        is_invalid_telemetry_reason: Reason string if the telemetry data is invalid.
        extra_log_info: Additional information to include in the log.
        debug_notifications: If True, enable debug output for notifications.

    Returns:
        Dict with Data containing:
        - MessageID / MessageText: "OK" on success, error code otherwise.
        - ID: The service request ID created or updated.
        - Mode: The mode that was applied.
    """
    body: dict[str, Any] = {
        "Mode": mode,
    }

    if asset_related_id is not None:
        body["AssetRelatedID"] = asset_related_id
    if id is not None:
        body["ID"] = id
    if sr_number is not None:
        body["SrNumber"] = sr_number
    if status_id is not None:
        body["StatusID"] = status_id
    if category_id is not None:
        body["CategoryID"] = category_id
    if priority_id is not None:
        body["PriorityID"] = priority_id
    if description is not None:
        body["Description"] = description
    if location is not None:
        body["Location"] = location
    if request_by_name is not None:
        body["RequestByName"] = request_by_name
    if request_by_phone is not None:
        body["RequestByPhone"] = request_by_phone
    if request_by_email is not None:
        body["RequestByEmail"] = request_by_email
    if request_by_location is not None:
        body["RequestByLocation"] = request_by_location
    if did_tag_equipment is not None:
        body["DidTagEquipment"] = did_tag_equipment
    if defer_reject_notes is not None:
        body["DeferRejectNotes"] = defer_reject_notes
    if latitude is not None:
        body["Latitude"] = latitude
    if longitude is not None:
        body["Longitude"] = longitude
    if is_system_created is not None:
        body["IsSystemCreated"] = is_system_created
    if is_invalid_telemetry_reason is not None:
        body["IsInvalidTelemetryReason"] = is_invalid_telemetry_reason
    if extra_log_info is not None:
        body["ExtraLogInfo"] = extra_log_info
    if debug_notifications:
        body["DebugNotifications"] = True

    return _post("servicerequest/addupdate", body)


# ---------------------------------------------------------------------------
# User List tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_user_lists(list_names: list[str] | None = None) -> dict:
    """
    Retrieve the supporting reference lists used when querying users.

    Available list names: TechGroupID, CityID, HomeCityID, PartInspectorCityID,
    PartInspectorStockRoomID.

    Args:
        list_names: Optional list of specific list names to return,
                    e.g. ["TechGroupID", "CityID"]. If omitted, all lists are returned.

    Returns:
        Dict of requested reference lists, each containing {ID, Name} entries.
    """
    params = {}
    if list_names:
        params["name"] = ",".join(list_names)
    return _get("user/lists", params=params)


@mcp.tool()
def get_users(
    show_inactive: bool = False,
    primary_city: str | None = None,
    has_access_city: str | None = None,
    home_city: str | None = None,
    profile_name: str | None = None,
    tech_group_ids: list[int | str] | None = None,
    mode: str | None = None,
    city_ids: list[int | str] | None = None,
    valid_emails: bool | None = None,
    home_city_ids: list[int | str] | None = None,
    filter_text: str | None = None,
    page_on: int | None = None,
    page_per: int | None = None,
    find: str | None = None,
    part_inspector: bool | None = None,
    part_inspector_city_ids: list[int | str] | None = None,
    part_inspector_stock_room_ids: list[int | str] | None = None,
    has_media: bool = False,
    id_accessible: bool = False,
) -> dict:
    """
    List users associated with this eBis tenant.

    Use get_user_lists() to discover valid ID/name values for any of the
    ID filter parameters.

    Args:
        show_inactive: If True, include inactive users in the results.
        primary_city: Filter by primary city name/abbreviation.
        has_access_city: Filter to users who have access to this city name/abbreviation.
        home_city: Filter by home city name/abbreviation.
        profile_name: Filter by user profile name.
        tech_group_ids: Filter by technician group IDs or names.
        mode: Filter by user mode string.
        city_ids: Filter by city IDs or names.
        valid_emails: If True, return only users with valid email addresses.
        home_city_ids: Filter by home city IDs or names.
        filter_text: General text filter applied across the user listing.
        page_on: Page number for paginated results (1-based).
        page_per: Number of results per page.
        find: General search string across user fields.
        part_inspector: If True, return only users who are part inspectors.
        part_inspector_city_ids: Filter part inspector users by city IDs or names.
        part_inspector_stock_room_ids: Filter part inspector users by stock room IDs or names.
        has_media: If True, return only users who have media attached.
        id_accessible: If True, child lists are keyed by ID rather than returned as arrays.

    Returns:
        User records matching the requested filters.
    """
    body: dict[str, Any] = {}

    if show_inactive:
        body["ShowInactive"] = True
    if primary_city is not None:
        body["PrimaryCity"] = primary_city
    if has_access_city is not None:
        body["HasAccessCity"] = has_access_city
    if home_city is not None:
        body["HomeCity"] = home_city
    if profile_name is not None:
        body["ProfileName"] = profile_name
    if tech_group_ids is not None:
        body["TechGroupID"] = tech_group_ids
    if mode is not None:
        body["Mode"] = mode
    if city_ids is not None:
        body["CityID"] = city_ids
    if valid_emails is not None:
        body["ValidEmails"] = valid_emails
    if home_city_ids is not None:
        body["HomeCityID"] = home_city_ids
    if filter_text is not None:
        body["FilterText"] = filter_text
    if page_on is not None:
        body["PageOn"] = page_on
    if page_per is not None:
        body["PagePer"] = page_per
    if find is not None:
        body["Find"] = find
    if part_inspector is not None:
        body["PartInspector"] = part_inspector
    if part_inspector_city_ids is not None:
        body["PartInspectorCityID"] = part_inspector_city_ids
    if part_inspector_stock_room_ids is not None:
        body["PartInspectorStockRoomID"] = part_inspector_stock_room_ids
    if has_media:
        body["HasMedia"] = True
    if id_accessible:
        body["IDAccessible"] = True

    return _post("user", body)


# ---------------------------------------------------------------------------
# User Logout tool
# ---------------------------------------------------------------------------

@mcp.tool()
def logout_users(
    user_batch: list[dict] | None = None,
    stop_active_timers: bool = False,
    session_logout: bool = False,
    logout_user_id: int | None = None,
    sso_id: str | None = None,
    username: str | None = None,
) -> dict:
    """
    Log one or more users out of eBis and optionally stop their active service timers.

    Supports two calling modes:
    - **Batch mode**: Pass a list of user dicts via `user_batch`. Each dict may contain
      any combination of: LineNumber, StopActiveTimers, SessionLogout, LogoutUserID,
      SsoID, Username. LineNumber is returned in the response to correlate results.
    - **Single-user mode**: Pass individual fields directly.

    At least one of logout_user_id, sso_id, or username is required to identify
    the user in single-user mode.

    Args:
        user_batch: List of user logout dicts for batch mode. Each dict should include
                    one user identifier (LogoutUserID, SsoID, or Username) and the
                    desired logout actions. Example:
                    [{"LineNumber": 1, "Username": "CaptainPicard", "SessionLogout": True},
                     {"LineNumber": 2, "SsoID": "abc123", "SessionLogout": True, "StopActiveTimers": True}]
        stop_active_timers: If True, stop all active service timers for the user.
        session_logout: If True, log the user out of their active eBis session.
        logout_user_id: eBis user ID of the user to log out.
        sso_id: SSO identifier of the user to log out.
        username: Username of the user to log out.

    Returns:
        Result of the logout operation, including per-user MessageID and MessageText.
    """
    if user_batch is not None:
        return _post("user/logout", {"UserBatch": user_batch})

    body: dict[str, Any] = {}

    if stop_active_timers:
        body["StopActiveTimers"] = True
    if session_logout:
        body["SessionLogout"] = True
    if logout_user_id is not None:
        body["LogoutUserID"] = logout_user_id
    if sso_id is not None:
        body["SsoID"] = sso_id
    if username is not None:
        body["Username"] = username

    return _post("user/logout", body)


# ---------------------------------------------------------------------------
# User Batch Add/Update tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_user_addupdate_lists(list_names: list[str] | None = None) -> dict:
    """
    Retrieve the supporting reference lists used when adding or updating users.

    Available list names: UserID, UserProfileID, TechGroupID, CityDefaultID, CityHomeID,
    StockRoomDefaultID, PaperSizeID, TimeZoneID, DstID, DateFormatID, TimeFormatID,
    NumberFormatID, CostAndRetailCurrencyID, BatchSetTechProfileID.

    Args:
        list_names: Optional list of specific list names to return,
                    e.g. ["UserProfileID", "CityDefaultID"]. If omitted, all lists are returned.

    Returns:
        Dict of requested reference lists, each containing {ID, Name} entries.
    """
    params = {}
    if list_names:
        params["name"] = ",".join(list_names)
    return _get("user/addupdate/lists", params=params)


@mcp.tool()
def add_update_users(
    # Batch mode
    user_batch: list[dict] | None = None,
    # Single-record mode
    mode: str | None = None,
    user_id: int | None = None,
    username: str | None = None,
    password: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    phone1: str | None = None,
    inspector_code: str | None = None,
    user_profile_id: int | None = None,
    tech_group_id: int | None = None,
    city_default_id: int | None = None,
    city_home_id: int | None = None,
    stock_room_default_id: int | None = None,
    is_contractor: bool | None = None,
    is_technician: bool | None = None,
    paper_size_id: int | None = None,
    time_zone_id: int | None = None,
    pdf_file_action_id: int | None = None,
    dst_id: int | None = None,
    ui_color_mode_id: int | None = None,
    date_format_id: int | None = None,
    time_format_id: int | None = None,
    number_format_id: int | None = None,
    limit_stock_room: bool | None = None,
    limit_work_center: bool | None = None,
    limit_fleet_make: bool | None = None,
    limit_city_admin: bool | None = None,
    limit_company: bool | None = None,
    limit_wo_item_signoff: bool | None = None,
    start_work_time_converted: str | None = None,
    end_work_time: int | None = None,
    end_work_time_converted: str | None = None,
    auto_end_timers_eod: bool | None = None,
    show_os_parts_counts: bool | None = None,
    show_sr_counts: bool | None = None,
    badge_count_type: int | None = None,
    cost: float | None = None,
    retail: float | None = None,
    cost_and_retail_currency_id: int | None = None,
    po_approval: bool | None = None,
    po_approval_amount: float | None = None,
    po_approval_always: bool | None = None,
    os_cities: str | None = None,
    general_account_is: bool | None = None,
    on_the_job_training_is: bool | None = None,
    time_clock_disable: bool | None = None,
    time_clock_log_in_when_sign_in: bool | None = None,
    city_time_clock_id: int | None = None,
    employee_id: str | None = None,
    regular_hrs_worked: float | None = None,
    time_clock_user_group_id: int | None = None,
    accept_click_thru: bool | None = None,
    batch_set_tech_profile_id: int | None = None,
    sso_id: str | None = None,
    set_retail_as_wo_rate: bool | None = None,
    account_type: int | None = None,
    new_password: str | None = None,
    old_password: str | None = None,
    new_inspector_code: str | None = None,
    old_inspector_code: str | None = None,
    tenant_url: str | None = None,
    token_extend_minutes: int | None = None,
    default_paging_max_size: bool | None = None,
    show_welcome_screen: bool | None = None,
    ignore_limit_ip_access: bool | None = None,
    subscription_last_alert: str | None = None,
) -> dict:
    """
    Add or update one or more users in eBis Cloud.

    Supports two calling modes:
    - **Batch mode**: Pass a list of user dicts via `user_batch`. Each dict must include
      `Mode` and the relevant fields for that user. `LineNumber` is returned in the
      response to correlate results.
    - **Single-record mode**: Pass `mode` and individual field parameters directly.

    Mode values:
    - **Insert**: Create a new user. Required: username, password, first_name, last_name,
      city_default_id, user_profile_id.
    - **Update**: Update general fields. Matches on username or user_id. Does not update password.
    - **ResetPassword**: Reset a user's password. Requires new_password. User is prompted
      to change password on next login.
    - **Inactivate**: Inactivate a user account.
    - **Activate**: Activate a user account.
    - **BatchSetTech**: Set all members of a user profile as technicians.
      Requires batch_set_tech_profile_id.

    Use get_user_addupdate_lists() to find valid IDs for any ID parameter.

    Args:
        user_batch: List of user dicts for batch mode. Each dict should include Mode
                    and the fields relevant to that operation.
        mode: Operation mode — Insert, Update, ResetPassword, Inactivate, Activate, BatchSetTech.
        user_id: eBis user ID — used to identify the user for Update/Inactivate/Activate.
        username: Username. Required for Insert; used as lookup key for Update.
        password: Password. Required for Insert.
        first_name: First name. Required for Insert.
        last_name: Last name. Required for Insert.
        email: Email address.
        phone1: Phone number.
        inspector_code: Inspector code for the user.
        user_profile_id: User profile ID. Required for Insert.
        tech_group_id: Technician group ID.
        city_default_id: Default city ID. Required for Insert.
        city_home_id: Home city ID.
        stock_room_default_id: Default stock room ID.
        is_contractor: If True, mark user as a contractor.
        is_technician: If True, mark user as a technician.
        paper_size_id: Preferred paper size ID.
        time_zone_id: Time zone ID.
        pdf_file_action_id: PDF file action preference ID.
        dst_id: Daylight saving time rule ID.
        ui_color_mode_id: UI color mode preference ID.
        date_format_id: Date format preference ID.
        time_format_id: Time format preference ID.
        number_format_id: Number format preference ID.
        limit_stock_room: If True, limit user to their default stock room.
        limit_work_center: If True, limit user to their assigned work center.
        limit_fleet_make: If True, limit user by fleet make.
        limit_city_admin: If True, limit user to city admin scope.
        limit_company: If True, limit user by company.
        limit_wo_item_signoff: If True, limit work order item signoff.
        start_work_time_converted: Work day start time, e.g. "08:00".
        end_work_time: Work day end time as integer.
        end_work_time_converted: Work day end time, e.g. "17:00".
        auto_end_timers_eod: If True, automatically end timers at end of day.
        show_os_parts_counts: If True, show outside parts counts.
        show_sr_counts: If True, show service request counts.
        badge_count_type: Badge count display type.
        cost: User cost rate.
        retail: User retail rate.
        cost_and_retail_currency_id: Currency ID for cost and retail rates.
        po_approval: If True, user can approve purchase orders.
        po_approval_amount: Maximum PO amount the user can approve.
        po_approval_always: If True, user must always approve POs.
        os_cities: Outside cities string.
        general_account_is: If True, mark as a general account.
        on_the_job_training_is: If True, mark user as on-the-job training.
        time_clock_disable: If True, disable time clock for this user.
        time_clock_log_in_when_sign_in: If True, log time clock when signing in.
        city_time_clock_id: City time clock ID.
        employee_id: Employee ID string.
        regular_hrs_worked: Regular hours worked per period.
        time_clock_user_group_id: Time clock user group ID.
        accept_click_thru: If True, user has accepted click-through agreement.
        batch_set_tech_profile_id: Profile ID for BatchSetTech mode — all members of
                                    this profile will be set as technicians.
        sso_id: SSO identifier for the user.
        set_retail_as_wo_rate: If True, use retail rate as the work order rate.
        account_type: Account type integer.
        new_password: New password — required for ResetPassword mode.
        old_password: Old password — used for password change verification.
        new_inspector_code: New inspector code.
        old_inspector_code: Old inspector code — used for inspector code change.
        tenant_url: Tenant URL override.
        token_extend_minutes: Number of minutes to extend the session token.
        default_paging_max_size: If True, use maximum page size by default.
        show_welcome_screen: If True, show the welcome screen on login.
        ignore_limit_ip_access: If True, bypass IP access restrictions.
        subscription_last_alert: Last subscription alert datetime.

    Returns:
        Per-user results, each with UserID, LineNumber, MessageID, MessageText,
        Action, and ID. MessageID is "OK" if the operation succeeded.
    """
    if user_batch is not None:
        return _post("user/addupdate", {"UserBatch": user_batch})

    body: dict[str, Any] = {}

    if mode is not None:
        body["Mode"] = mode
    if user_id is not None:
        body["UserID"] = user_id
    if username is not None:
        body["Username"] = username
    if password is not None:
        body["Password"] = password
    if first_name is not None:
        body["FirstName"] = first_name
    if last_name is not None:
        body["LastName"] = last_name
    if email is not None:
        body["Email"] = email
    if phone1 is not None:
        body["Phone1"] = phone1
    if inspector_code is not None:
        body["InspectorCode"] = inspector_code
    if user_profile_id is not None:
        body["UserProfileID"] = user_profile_id
    if tech_group_id is not None:
        body["TechGroupID"] = tech_group_id
    if city_default_id is not None:
        body["CityDefaultID"] = city_default_id
    if city_home_id is not None:
        body["CityHomeID"] = city_home_id
    if stock_room_default_id is not None:
        body["StockRoomDefaultID"] = stock_room_default_id
    if is_contractor is not None:
        body["IsContractor"] = is_contractor
    if is_technician is not None:
        body["IsTechnician"] = is_technician
    if paper_size_id is not None:
        body["PaperSizeID"] = paper_size_id
    if time_zone_id is not None:
        body["TimeZoneID"] = time_zone_id
    if pdf_file_action_id is not None:
        body["PdfFileActionID"] = pdf_file_action_id
    if dst_id is not None:
        body["DstID"] = dst_id
    if ui_color_mode_id is not None:
        body["UiColorModeID"] = ui_color_mode_id
    if date_format_id is not None:
        body["DateFormatID"] = date_format_id
    if time_format_id is not None:
        body["TimeFormatID"] = time_format_id
    if number_format_id is not None:
        body["NumberFormatID"] = number_format_id
    if limit_stock_room is not None:
        body["LimitStockRoom"] = limit_stock_room
    if limit_work_center is not None:
        body["LimitWorkCenter"] = limit_work_center
    if limit_fleet_make is not None:
        body["LimitFleetMake"] = limit_fleet_make
    if limit_city_admin is not None:
        body["LimitCityAdmin"] = limit_city_admin
    if limit_company is not None:
        body["LimitCompany"] = limit_company
    if limit_wo_item_signoff is not None:
        body["LimitWoItemSignoff"] = limit_wo_item_signoff
    if start_work_time_converted is not None:
        body["StartWorkTimeConverted"] = start_work_time_converted
    if end_work_time is not None:
        body["EndWorkTime"] = end_work_time
    if end_work_time_converted is not None:
        body["EndWorkTimeConverted"] = end_work_time_converted
    if auto_end_timers_eod is not None:
        body["AutoEndTimersEOD"] = auto_end_timers_eod
    if show_os_parts_counts is not None:
        body["ShowOsPartsCounts"] = show_os_parts_counts
    if show_sr_counts is not None:
        body["ShowSrCounts"] = show_sr_counts
    if badge_count_type is not None:
        body["BadgeCountType"] = badge_count_type
    if cost is not None:
        body["Cost"] = cost
    if retail is not None:
        body["Retail"] = retail
    if cost_and_retail_currency_id is not None:
        body["CostAndRetailCurrencyID"] = cost_and_retail_currency_id
    if po_approval is not None:
        body["PoApproval"] = po_approval
    if po_approval_amount is not None:
        body["PoApprovalAmount"] = po_approval_amount
    if po_approval_always is not None:
        body["PoApprovalAlways"] = po_approval_always
    if os_cities is not None:
        body["OsCities"] = os_cities
    if general_account_is is not None:
        body["GeneralAccountIs"] = general_account_is
    if on_the_job_training_is is not None:
        body["OnTheJobTrainingIs"] = on_the_job_training_is
    if time_clock_disable is not None:
        body["TimeClockDisable"] = time_clock_disable
    if time_clock_log_in_when_sign_in is not None:
        body["TimeClockLogInWhenSignIn"] = time_clock_log_in_when_sign_in
    if city_time_clock_id is not None:
        body["CityTimeClockID"] = city_time_clock_id
    if employee_id is not None:
        body["EmployeeID"] = employee_id
    if regular_hrs_worked is not None:
        body["RegularHrsWorked"] = regular_hrs_worked
    if time_clock_user_group_id is not None:
        body["TimeClockUserGroupID"] = time_clock_user_group_id
    if accept_click_thru is not None:
        body["AcceptClickThru"] = accept_click_thru
    if batch_set_tech_profile_id is not None:
        body["BatchSetTechProfileID"] = batch_set_tech_profile_id
    if sso_id is not None:
        body["SsoID"] = sso_id
    if set_retail_as_wo_rate is not None:
        body["SetRetailAsWoRate"] = set_retail_as_wo_rate
    if account_type is not None:
        body["AccountType"] = account_type
    if new_password is not None:
        body["NewPassword"] = new_password
    if old_password is not None:
        body["OldPassword"] = old_password
    if new_inspector_code is not None:
        body["NewInspectorCode"] = new_inspector_code
    if old_inspector_code is not None:
        body["OldInspectorCode"] = old_inspector_code
    if tenant_url is not None:
        body["TenantUrl"] = tenant_url
    if token_extend_minutes is not None:
        body["TokenExtendMinutes"] = token_extend_minutes
    if default_paging_max_size is not None:
        body["DefaultPagingMaxSize"] = default_paging_max_size
    if show_welcome_screen is not None:
        body["ShowWelcomeScreen"] = show_welcome_screen
    if ignore_limit_ip_access is not None:
        body["IgnoreLimitIpAccess"] = ignore_limit_ip_access
    if subscription_last_alert is not None:
        body["SubscriptionLastAlert"] = subscription_last_alert

    return _post("user/addupdate", body)


# ---------------------------------------------------------------------------
# Edit User Cities tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_user_cities_admin_lists(list_names: list[str] | None = None) -> dict:
    """
    Retrieve the supporting reference lists used when editing user city access.

    Available list names: UserID, AddToUsersWithProfileID, CityID, IbsID, RegionID.

    Args:
        list_names: Optional list of specific list names to return,
                    e.g. ["UserID", "CityID"]. If omitted, all lists are returned.

    Returns:
        Dict of requested reference lists, each containing {ID, Name} entries.
    """
    params = {}
    if list_names:
        params["name"] = ",".join(list_names)
    return _get("user/cities/admin/lists", params=params)


@mcp.tool()
def edit_user_cities(
    mode: str,
    user_batch: list[dict] | None = None,
    user_id: int | str | None = None,
    all_cities: bool | None = None,
    add_to_all_users: bool | None = None,
    add_to_users_with_profile_id: int | str | None = None,
    email: str | None = None,
    city_ids: list[int | str] | None = None,
    ibs_ids: list[int | str] | None = None,
    region_ids: list[int | str] | None = None,
) -> dict:
    """
    Edit city, IBS, and region access for one or more users.

    Supports two calling modes:
    - **Batch mode**: Pass a list of user-city operation dicts via `user_batch`.
      Each dict must include Mode and UserID, plus the city/IBS/region IDs to act on.
      Note: AddToAllUsers and AddToUsersWithProfileID are not allowed in batch mode.
    - **Single-operation mode**: Pass `mode` and individual parameters directly.

    Use get_user_cities_admin_lists() to discover valid IDs for UserID,
    AddToUsersWithProfileID, CityID, IbsID, and RegionID.

    Mode values:
    - **Insert**: Grant access to the specified cities/IBS/regions.
    - **Delete**: Remove access to the specified cities/IBS/regions.

    Args:
        mode: (Required) "Insert" to grant access, "Delete" to remove access.
        user_batch: List of per-user operation dicts for batch mode. Each dict
                    should include Mode, UserID, and the relevant city/IBS/region IDs.
                    Example: [{"LineNumber": 1, "Mode": "Insert", "UserID": "VivianThomas123",
                               "CityID": [37, 102, "HNL"]}]
        user_id: Target user by eBis ID or username. Used for single-user operations.
        all_cities: If True, apply the operation to all cities, IBS, and regions in the system.
        add_to_all_users: If True (Insert only), add the specified cities to all users.
                          Not allowed in batch mode.
        add_to_users_with_profile_id: Add the specified cities to all users with this
                                       UserProfile ID or name (Insert only).
                                       Not allowed in batch mode.
        email: Target user by email address.
        city_ids: City IDs or names to insert/delete access for.
        ibs_ids: IBS IDs or names to insert/delete access for.
        region_ids: Region IDs or names to insert/delete access for.

    Returns:
        Per-user/operation results with MessageID and MessageText.
    """
    if user_batch is not None:
        return _post("user/cities/admin", {"Mode": mode, "UserBatch": user_batch})

    body: dict[str, Any] = {
        "Mode": mode,
    }

    if user_id is not None:
        body["UserID"] = user_id
    if all_cities is not None:
        body["AllCities"] = all_cities
    if add_to_all_users is not None:
        body["AddToAllUsers"] = add_to_all_users
    if add_to_users_with_profile_id is not None:
        body["AddToUsersWithProfileID"] = add_to_users_with_profile_id
    if email is not None:
        body["Email"] = email
    if city_ids is not None:
        body["CityID"] = city_ids
    if ibs_ids is not None:
        body["IbsID"] = ibs_ids
    if region_ids is not None:
        body["RegionID"] = region_ids

    return _post("user/cities/admin", body)


# ---------------------------------------------------------------------------
# Vendor Listing tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_vendor_listing_lists(list_names: list[str] | None = None) -> dict:
    """
    Retrieve the supporting reference lists used when querying vendors.

    Available list names: LimitToCityID, ShipMethodID, TermsID, VendorClassID.

    Args:
        list_names: Optional list of specific list names to return,
                    e.g. ["ShipMethodID", "VendorClassID"]. If omitted, all lists are returned.

    Returns:
        Dict of requested reference lists, each containing {ID, Name} entries.
    """
    params = {}
    if list_names:
        params["name"] = ",".join(list_names)
    return _get("vendor/listing/lists", params=params)


@mcp.tool()
def get_vendor_listing(
    include_inactive: bool = False,
    account: str | None = None,
    address: str | None = None,
    address2: str | None = None,
    approval_expiring: int | None = None,
    approved: int | str | None = None,
    cities: list[str] | None = None,
    city: str | None = None,
    contact: str | None = None,
    countries: list[str] | None = None,
    country: str | None = None,
    do_not_create_po: str | None = None,
    email: str | None = None,
    gl_account_number: str | None = None,
    has_media: bool = False,
    has_warranty_claims: str | None = None,
    inactive: str | None = None,
    is_osr: str | None = None,
    is_supplier: str | None = None,
    is_tools: str | None = None,
    limit_to_city_id: int | str | None = None,
    phone: str | None = None,
    ship_method_ids: list[int | str] | None = None,
    state: str | None = None,
    states: list[str] | None = None,
    terms_ids: list[int | str] | None = None,
    url: str | None = None,
    vendor_class_ids: list[int | str] | None = None,
    vendor_name: str | None = None,
    zip: str | None = None,
    zips: list[str] | None = None,
    id_accessible: bool = False,
) -> dict:
    """
    Retrieve a comprehensive list of vendors.

    Use get_vendor_listing_lists() to discover valid ID/name values for
    any of the ID filter parameters.

    Args:
        include_inactive: If True, include inactive vendors in the results.
        account: Fragment search on vendor account number.
        address: Fragment search on address line 1.
        address2: Fragment search on address line 2.
        approval_expiring: Return vendors whose approval expires within N days.
        approved: Filter by approval status ID or name.
        cities: Filter by multiple exact city names, e.g. ["Dallas", "Charlotte"].
        city: Fragment search on vendor city.
        contact: Fragment search on vendor contact name.
        countries: Filter by multiple exact country names.
        country: Fragment search on vendor country.
        do_not_create_po: Filter by PO restriction — "yes", "no", or "all".
        email: Fragment search on vendor email address.
        gl_account_number: Fragment search on GL account number.
        has_media: If True, return only vendors with media attachments.
        has_warranty_claims: Filter by warranty claim presence — "yes", "no", or "all".
        inactive: Filter by inactive status — "yes", "no", or "all".
        is_osr: Filter by outside repair vendor status — "yes", "no", or "all".
        is_supplier: Filter by supplier status — "yes", "no", or "all".
        is_tools: Filter by tools vendor status — "yes", "no", or "all".
        limit_to_city_id: Limit results to vendors accessible to this city ID or name.
        phone: Fragment search on vendor phone number.
        ship_method_ids: Filter by shipping method IDs or names.
        state: Fragment search on vendor state.
        states: Filter by multiple exact state values.
        terms_ids: Filter by payment terms IDs or names.
        url: Fragment search on vendor website URL.
        vendor_class_ids: Filter by vendor class IDs or names.
        vendor_name: Fragment search on vendor name.
        zip: Fragment search on vendor ZIP/postal code.
        zips: Filter by multiple exact ZIP/postal codes.
        id_accessible: If True, child lists are keyed by ID rather than returned as arrays.

    Returns:
        Vendor records matching the requested filters.
    """
    body: dict[str, Any] = {}

    if include_inactive:
        body["IncludeInactive"] = True
    if account is not None:
        body["Account"] = account
    if address is not None:
        body["Address"] = address
    if address2 is not None:
        body["Address2"] = address2
    if approval_expiring is not None:
        body["ApprovalExpiring"] = approval_expiring
    if approved is not None:
        body["Approved"] = approved
    if cities is not None:
        body["Cities"] = cities
    if city is not None:
        body["City"] = city
    if contact is not None:
        body["Contact"] = contact
    if countries is not None:
        body["Countries"] = countries
    if country is not None:
        body["Country"] = country
    if do_not_create_po is not None:
        body["DoNotCreatePO"] = do_not_create_po
    if email is not None:
        body["Email"] = email
    if gl_account_number is not None:
        body["GLAccountNumber"] = gl_account_number
    if has_media:
        body["HasMedia"] = True
    if has_warranty_claims is not None:
        body["HasWarrantyClaims"] = has_warranty_claims
    if inactive is not None:
        body["Inactive"] = inactive
    if is_osr is not None:
        body["IsOsr"] = is_osr
    if is_supplier is not None:
        body["IsSupplier"] = is_supplier
    if is_tools is not None:
        body["IsTools"] = is_tools
    if limit_to_city_id is not None:
        body["LimitToCityID"] = limit_to_city_id
    if phone is not None:
        body["Phone"] = phone
    if ship_method_ids is not None:
        body["ShipMethodID"] = ship_method_ids
    if state is not None:
        body["State"] = state
    if states is not None:
        body["States"] = states
    if terms_ids is not None:
        body["TermsID"] = terms_ids
    if url is not None:
        body["Url"] = url
    if vendor_class_ids is not None:
        body["VendorClassID"] = vendor_class_ids
    if vendor_name is not None:
        body["VendorName"] = vendor_name
    if zip is not None:
        body["Zip"] = zip
    if zips is not None:
        body["Zips"] = zips
    if id_accessible:
        body["IDAccessible"] = True

    return _post("vendor/listing", body)


# ---------------------------------------------------------------------------
# Vendor Batch Add/Update tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_vendor_addupdate_lists(list_names: list[str] | None = None) -> dict:
    """
    Retrieve the supporting reference lists used when adding or updating vendors.

    Available list names: Phone1TypeID, Phone2TypeID, Phone3TypeID, Phone4TypeID,
    TermsID, VendorClassID, CurrencyID, ShipMethodID, ApproveTypeID, WarrantyMakeID,
    LimitToCityID, TaxID.

    Args:
        list_names: Optional list of specific list names to return,
                    e.g. ["TermsID", "ShipMethodID"]. If omitted, all lists are returned.

    Returns:
        Dict of requested reference lists, each containing {ID, Name} entries.
    """
    params = {}
    if list_names:
        params["name"] = ",".join(list_names)
    return _get("vendor/addupdate/lists", params=params)


@mcp.tool()
def add_update_vendors(
    # Batch mode
    vendor_batch: list[dict] | None = None,
    # Single-record mode
    mode: str | None = None,
    id: int | None = None,
    vendor_name: str | None = None,
    user_validate_temp_token: str | None = None,
    change_to_name: str | None = None,
    # Contact / address
    contact: str | None = None,
    address: str | None = None,
    address2: str | None = None,
    city: str | None = None,
    state: str | None = None,
    zip: str | None = None,
    country: str | None = None,
    country_use: bool | None = None,
    # Shipping address
    ship_address: str | None = None,
    ship_address2: str | None = None,
    ship_city: str | None = None,
    ship_state: str | None = None,
    ship_zip: str | None = None,
    ship_country: str | None = None,
    ship_country_use: bool | None = None,
    # Phone numbers
    phone1: str | None = None,
    phone2: str | None = None,
    phone3: str | None = None,
    phone4: str | None = None,
    phone1_type_id: int | None = None,
    phone2_type_id: int | None = None,
    phone3_type_id: int | None = None,
    phone4_type_id: int | None = None,
    # Online / account
    email: str | None = None,
    url: str | None = None,
    account: str | None = None,
    customer_code: str | None = None,
    notes: str | None = None,
    gl_account_number: str | None = None,
    supplier_site_name: str | None = None,
    # Classifications
    terms_id: int | None = None,
    vendor_class_id: int | None = None,
    currency_id: int | None = None,
    ship_method_id: int | None = None,
    tax_id: str | None = None,
    is_supplier: bool | None = None,
    is_osr: bool | None = None,
    is_tools: bool | None = None,
    do_not_create_po: bool | None = None,
    limit_to_city_id: int | None = None,
    # Approval / warranty
    approve_type_id: int | None = None,
    approve_expires: str | None = None,
    has_warranty_claims: bool | None = None,
    has_contract_pricing: bool | None = None,
    warranty_make_id: int | None = None,
    # Output
    id_accessible: bool = False,
    language: str | None = None,
) -> dict:
    """
    Add or update one or more vendors in eBis Cloud.

    Supports two calling modes:
    - **Batch mode**: Pass a list of vendor dicts via `vendor_batch`. Each dict must
      include `Mode` and the relevant fields. `LineNumber` is returned in the response.
    - **Single-record mode**: Pass `mode` and individual field parameters directly.

    Mode values:
    - **Insert**: Create a new vendor. Requires `vendor_name`.
    - **Update**: Update general fields. Matches on `id`; `vendor_name` used as fallback.
    - **Delete**: Delete a vendor. Returns a confirmation token (`UserValidateTempToken`).
      Resubmit with the token to confirm.
    - **Inactivate**: Inactivate a vendor. Also returns a confirmation token.
    - **Activate**: Activate a vendor.
    - **ChangeName**: Rename a vendor. Requires `change_to_name`.

    Use get_vendor_addupdate_lists() to find valid IDs for any ID parameter.

    Args:
        vendor_batch: List of vendor dicts for batch mode.
        mode: Operation mode — Insert, Update, Delete, Inactivate, Activate, ChangeName.
        id: Vendor ID — primary lookup key for Update/Delete/Inactivate/Activate/ChangeName.
        vendor_name: Vendor name. Required for Insert; fallback lookup for other modes.
        user_validate_temp_token: Confirmation token returned from a Delete/Inactivate
                                   request. Resubmit with this token to confirm the action.
        change_to_name: New vendor name for ChangeName mode.
        contact: Vendor contact name.
        address: Address line 1.
        address2: Address line 2.
        city: Vendor city.
        state: Vendor state.
        zip: Vendor ZIP/postal code.
        country: Vendor country.
        country_use: If True, use the country field in address formatting.
        ship_address: Shipping address line 1.
        ship_address2: Shipping address line 2.
        ship_city: Shipping city.
        ship_state: Shipping state.
        ship_zip: Shipping ZIP/postal code.
        ship_country: Shipping country.
        ship_country_use: If True, use the shipping country field.
        phone1: Primary phone number.
        phone2: Secondary phone number.
        phone3: Tertiary phone number.
        phone4: Quaternary phone number.
        phone1_type_id: Type ID for phone1.
        phone2_type_id: Type ID for phone2.
        phone3_type_id: Type ID for phone3.
        phone4_type_id: Type ID for phone4.
        email: Vendor email address.
        url: Vendor website URL.
        account: Vendor account number.
        customer_code: Customer code at the vendor.
        notes: Vendor notes.
        gl_account_number: GL account number.
        supplier_site_name: Supplier site name.
        terms_id: Payment terms ID.
        vendor_class_id: Vendor class ID.
        currency_id: Currency ID.
        ship_method_id: Shipping method ID.
        tax_id: Tax ID string.
        is_supplier: If True, mark as a parts supplier.
        is_osr: If True, mark as an outside repair vendor.
        is_tools: If True, mark as a tools vendor.
        do_not_create_po: If True, prevent PO creation for this vendor.
        limit_to_city_id: Limit this vendor to a specific city ID.
        approve_type_id: Approval type ID.
        approve_expires: Approval expiry date, e.g. "2025-12-31".
        has_warranty_claims: If True, vendor has warranty claims.
        has_contract_pricing: If True, vendor has contract pricing.
        warranty_make_id: Make ID associated with vendor warranty.
        id_accessible: If True, child lists are keyed by ID rather than returned as arrays.
        language: Language for generic list parameter lookups (default: "English").

    Returns:
        Per-vendor results with LineNumber, MessageID, MessageText, ID, and Action.
        For Delete/Inactivate, an unconfirmed response includes a UserValidateTempToken.
    """
    if vendor_batch is not None:
        return _post("vendor/addupdate", {"VendorBatch": vendor_batch})

    body: dict[str, Any] = {}

    if mode is not None:
        body["Mode"] = mode
    if id is not None:
        body["ID"] = id
    if vendor_name is not None:
        body["VendorName"] = vendor_name
    if user_validate_temp_token is not None:
        body["UserValidateTempToken"] = user_validate_temp_token
    if change_to_name is not None:
        body["ChangeToName"] = change_to_name
    if contact is not None:
        body["Contact"] = contact
    if address is not None:
        body["Address"] = address
    if address2 is not None:
        body["Address2"] = address2
    if city is not None:
        body["City"] = city
    if state is not None:
        body["State"] = state
    if zip is not None:
        body["Zip"] = zip
    if country is not None:
        body["Country"] = country
    if country_use is not None:
        body["CountryUse"] = country_use
    if ship_address is not None:
        body["ShipAddress"] = ship_address
    if ship_address2 is not None:
        body["ShipAddress2"] = ship_address2
    if ship_city is not None:
        body["ShipCity"] = ship_city
    if ship_state is not None:
        body["ShipState"] = ship_state
    if ship_zip is not None:
        body["ShipZip"] = ship_zip
    if ship_country is not None:
        body["ShipCountry"] = ship_country
    if ship_country_use is not None:
        body["ShipCountryUse"] = ship_country_use
    if phone1 is not None:
        body["Phone1"] = phone1
    if phone2 is not None:
        body["Phone2"] = phone2
    if phone3 is not None:
        body["Phone3"] = phone3
    if phone4 is not None:
        body["Phone4"] = phone4
    if phone1_type_id is not None:
        body["Phone1TypeID"] = phone1_type_id
    if phone2_type_id is not None:
        body["Phone2TypeID"] = phone2_type_id
    if phone3_type_id is not None:
        body["Phone3TypeID"] = phone3_type_id
    if phone4_type_id is not None:
        body["Phone4TypeID"] = phone4_type_id
    if email is not None:
        body["Email"] = email
    if url is not None:
        body["Url"] = url
    if account is not None:
        body["Account"] = account
    if customer_code is not None:
        body["CustomerCode"] = customer_code
    if notes is not None:
        body["Notes"] = notes
    if gl_account_number is not None:
        body["GLAccountNumber"] = gl_account_number
    if supplier_site_name is not None:
        body["SupplierSiteName"] = supplier_site_name
    if terms_id is not None:
        body["TermsID"] = terms_id
    if vendor_class_id is not None:
        body["VendorClassID"] = vendor_class_id
    if currency_id is not None:
        body["CurrencyID"] = currency_id
    if ship_method_id is not None:
        body["ShipMethodID"] = ship_method_id
    if tax_id is not None:
        body["TaxID"] = tax_id
    if is_supplier is not None:
        body["IsSupplier"] = is_supplier
    if is_osr is not None:
        body["IsOsr"] = is_osr
    if is_tools is not None:
        body["IsTools"] = is_tools
    if do_not_create_po is not None:
        body["DoNotCreatePO"] = do_not_create_po
    if limit_to_city_id is not None:
        body["LimitToCityID"] = limit_to_city_id
    if approve_type_id is not None:
        body["ApproveTypeID"] = approve_type_id
    if approve_expires is not None:
        body["ApproveExpires"] = approve_expires
    if has_warranty_claims is not None:
        body["HasWarrantyClaims"] = has_warranty_claims
    if has_contract_pricing is not None:
        body["HasContractPricing"] = has_contract_pricing
    if warranty_make_id is not None:
        body["WarrantyMakeID"] = warranty_make_id
    if id_accessible:
        body["IDAccessible"] = True
    if language is not None:
        body["Language"] = language

    return _post("vendor/addupdate", body)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
