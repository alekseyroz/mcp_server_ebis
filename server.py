"""MCP Server for Veryon Workcenter (WC) REST API.

Exposes 10 broad domain tools (rather than one tool per REST operation) to keep the
tool-selection surface small for LLM callers. Each domain tool takes an `action`
parameter naming the underlying `WcClient` method to invoke, plus a `params` dict
of keyword arguments for that method.
"""

from veryon_wc import WcClient
from mcp.server.fastmcp import FastMCP

from src.config import BASE_URL, PASSWORD, USERNAME

mcp = FastMCP("Veryon Workcenter (WC)")

_client = WcClient(base_url=BASE_URL, username=USERNAME, password=PASSWORD)


def _dispatch(domain: str, action: str, allowed: frozenset[str], params: dict | None = None):
    if action not in allowed:
        raise ValueError(f"Unknown action '{action}' for '{domain}'. Valid actions: {sorted(allowed)}")
    method = getattr(_client, action)
    return method(**(params or {}))


# ---------------------------------------------------------------------------
# Work Orders
# ---------------------------------------------------------------------------

_WORK_ORDER_ACTIONS = frozenset({
    "get_workorder_lists",
    "export_workorders",
    "get_workorder_addupdate_lists",
    "create_update_workorder",
    "get_workorder_totals_lists",
    "get_workorder_totals",
    "get_workorder_listing_lists",
    "get_workorder_listing",
    "get_workorder_compliance_lists",
    "get_workorder_compliance",
    "get_part_history_lists",
    "get_part_history",
    "get_tech_activity_lists",
    "get_tech_activity",
    "resync_billing_and_tax",
})


@mcp.tool()
def work_orders(action: str, params: dict | None = None) -> dict:
    """Work order operations. Set `action` to one of:
    - get_workorder_lists(list_name: str | None = None): Reference lists (e.g. CityID) for filtering work order exports.
    - export_workorders(city_ids=None, completed_dates=None, created_dates=None, include_billing_option=False, include_invoice_media=False, include_invoice_totals=False, include_meter_reading=False, include_outside_repair=False, include_parts=False, include_service=False, include_service_logs=False, include_signoffs=False, include_wo_item_media=False, include_wo_media=False, hierarchy="flat", id_accessible=False): Export detailed work order information with optional sections (parts, invoices, media, signoffs, etc).
    - get_workorder_addupdate_lists(list_names: list[str] | None = None): Reference lists (CityID, CustomerID, AircraftID, BillingProfileID, MeterProfileID) for creating/updating work orders.
    - create_update_workorder(city_id=None, city_abbr=None, create_city_if_not_exists=False, default_to_aircraft_city=True, customer_id=None, customer_name=None, create_customer_if_not_exists=False, default_to_aircraft_primary_customer=True, aircraft_id=None, reg_num=None, create_aircraft_if_not_exists=False, add_customer_to_aircraft_if_not_attached=False, billing_profile_id=None, billing_profile_name=None, use_any_billing_profile=True, meter_profile_id=None, meter_profile_name=None, use_any_meter_profile=True, items=None, priority_id=None): Create or update a work order, resolving city/customer/aircraft/billing profile in order.
    - get_workorder_totals_lists(list_names: list[str] | None = None): Reference lists for filtering work order totals.
    - get_workorder_totals(completed_dates=None, created_dates=None, ac_reg_num=None, ac_serial_no=None, city_ids=None, city_nos=None, created_by_username_like=None, currency_ids=None, customer_ids=None, department_ids=None, ebis_ids=None, every_item=False, fleet_object_ids=None, group_by_invoice=False, include_open_wos=False, maintained_by_ids=None, make_ids=None, model_ids=None, region_ids=None, vehicle_type_ids=None, void_work_orders=False, wo_cat1_ids=None, wo_cat2_ids=None, wo_cat3_ids=None, wo_corr_action=None, wo_department_ids=None, wo_discrep=None, work_center_ids=None, work_orders=None, wo_status_ids=None, wo_type_ids=None, hierarchy="flat", id_accessible=False, full_debug=False, unit_test=False): Retrieve work order totals based on custom criteria.
    - get_workorder_listing_lists(list_names: list[str] | None = None): Reference lists for querying work order listings.
    - get_workorder_listing(wo_status_id, wo_type_id, city_group_ids=None, city_ids=None, city_no=None, completed_dates=None, created_dates=None, customer_ids=None, detailed_export=False, due_dates=None, engine_ids=None, export_all_items=False, export_invoice_totals=False, has_customer_po=None, maintained_by_ids=None, make_ids=None, model_ids=None, pm_doc_ids=None, region_ids=None, sort_by_id=None, vehicle_type_ids=None, wo_action_category_ids=None, wo_category_ids=None, work_center_ids=None, wo_sub_category_ids=None, zone_ids=None, hierarchy="flat", id_accessible=False, language=None): Retrieve work order listing information (wo_status_id and wo_type_id required).
    - get_workorder_compliance_lists(list_names: list[str] | None = None): Reference lists for querying work order compliance.
    - get_workorder_compliance(summary_group_by_id, city_ids=None, completed_dates=None, customer_ids=None, due_dates=None, maintained_by_ids=None, region_ids=None, show_unassigned_workcenter=False, work_center_ids=None, zone_ids=None, id_accessible=False, language=None): Compliance info on whether work orders were created on time (summary_group_by_id required).
    - get_part_history_lists(list_names: list[str] | None = None): Reference lists for querying work order part history.
    - get_part_history(added_by_user_like=None, all_accessible_cities=False, city_ids=None, city_no_like=None, completed_dates=None, cost_center_ids=None, customer_ids=None, date_added=None, date_used=None, department_ids=None, engine1_ids=None, engine1_serial=None, ibs_ids=None, line_code=None, make1_ids=None, model1_ids=None, part_component_ids=None, part_description=None, part_number=None, parts_not_in_master_parts=False, parts_with_serial_numbers=False, part_type_ids=None, region_ids=None, reg_nums=None, serial_no=None, show_deleted_only=False, status_type_id=None, user_status_ids=None, vehicle_type_abbrs=None, vehicle_type_ids=None, vin=None, wo_action_category_ids=None, wo_category_ids=None, wo_date_created=None, wo_ebis_main_type_ids=None, work_center_ids=None, work_order_like=None, wo_status_ids=None, wo_sub_category_ids=None, wo_type_ids=None, year_built=None, id_accessible=False, language=None): Work order part usage history based on custom criteria.
    - get_tech_activity_lists(list_names: list[str] | None = None): Reference lists (TechGroupID) for querying technician activity.
    - get_tech_activity(dates, city_ids=None, tech_group_ids=None, technician_ids=None, id_accessible=False, full_debug=False): Detailed logs of technician activity on work orders (dates required).
    - resync_billing_and_tax(wo_id_list, full_debug=False): Resynchronize billing, tax, and invoice info for the given work order IDs.

    Pass action-specific keyword arguments via `params`.
    """
    return _dispatch("work_orders", action, _WORK_ORDER_ACTIONS, params)


# ---------------------------------------------------------------------------
# Outside Repair
# ---------------------------------------------------------------------------

_OUTSIDE_REPAIR_ACTIONS = frozenset({
    "get_outside_repair_lists",
    "search_outside_repair",
})


@mcp.tool()
def outside_repair(action: str, params: dict | None = None) -> dict:
    """Outside repair operations. Set `action` to one of:
    - get_outside_repair_lists(list_names: list[str] | None = None): Reference lists (CityID, CostCenterID, CustomerID, DepartmentID, EngineID, IbsID, MakeID, ModelID, RegionID, StatusTypeID, UserStatusID, VehicleTypeID, WoActionCategoryID, WoCategoryID, WorkCenterID, WoStatusID, WoSubCategoryID, WoTypeID) for filtering outside repair searches.
    - search_outside_repair(completed_dates=None, date_added=None, added_by_user_like=None, all_accessible_cities=False, city_ids=None, city_no_like=None, cost_center_ids=None, customer_ids=None, department_ids=None, engine1_serial=None, engine_ids=None, ibs_ids=None, make_ids=None, model_ids=None, output_only_detail=False, part_description=None, part_number=None, region_ids=None, reg_nums=None, serial_no=None, show_deleted_only=False, status_type_id=None, user_status_ids=None, vehicle_type_abbrs=None, vehicle_type_ids=None, vendor_name=None, vin=None, wo_action_category_ids=None, wo_category_ids=None, work_center_ids=None, work_order_like=None, wo_status_ids=None, wo_sub_category_ids=None, wo_type_ids=None, year_built=None, hierarchy="flat", id_accessible=False, language=None): Search outside repair items based on custom criteria.

    Pass action-specific keyword arguments via `params`.
    """
    return _dispatch("outside_repair", action, _OUTSIDE_REPAIR_ACTIONS, params)


# ---------------------------------------------------------------------------
# Equipment
# ---------------------------------------------------------------------------

_EQUIPMENT_ACTIONS = frozenset({
    "get_equipment_listing_lists",
    "get_equipment_listing",
    "get_out_of_service_lists",
    "get_out_of_service_detail",
    "get_out_of_service_summary",
    "get_equipment_transfer_lists",
    "get_equipment_transfers",
    "get_equipment_addupdate_lists",
    "add_update_equipment",
    "get_otc_listing_lists",
    "get_otc_listing",
})


@mcp.tool()
def equipment(action: str, params: dict | None = None) -> dict:
    """Equipment, out-of-service, transfer, and OTC (over-the-counter) operations. Set `action` to one of:
    - get_equipment_listing_lists(list_names: list[str] | None = None): Reference lists (CityID, ControllerID, CostCenterID, CustomerID, DepartmentID, Engine1ID, FleetConfigID, Make1ID, MeterProfileID, Model1ID, MotorID, PartsCatalogID, PmDocID, Power1ID, RegionID, TelemetryIntegID, UserStatusID, VehicleTypeID, WorkCenterID, ZoneID) for equipment listings.
    - get_equipment_listing(after_paint_date=None, any_license_due_next_days=None, asset_no=None, asset_no_multiple=None, banner_status=None, battery_mgmt_id=None, city_ids=None, city_no_like=None, city_no_multiple=None, contractor=None, controller_ids=None, cost_center_ids=None, customer_ids=None, department_ids=None, ebis_ids=None, engine1_ids=None, engine1_serial=None, engine1_spec_no=None, fleet_config_ids=None, front_axel_serial=None, has_date_based_schedule=False, has_license_no=None, has_linked_parts_list_override=None, has_meter_based_schedule=False, has_pm_part_kit=None, has_pm_part_kit_override=None, has_pm_schedules=None, has_seatbelt=None, inactive_include=False, last_pm_over_days_ago=None, lease_expires_next_days=None, license_no=None, make1_ids=None, meter_profile_ids=None, model1_ids=None, motor_ids=None, only_inactive=False, only_with_telemetry=False, only_with_valid_warranty=False, parts_catalog_ids=None, pm_doc_ids=None, power1_ids=None, rear_axel_serial=None, reflectivity=None, region_ids=None, rental_expires_next_days=None, serial_no=None, show_license_no=False, stationary_loc_multiple=None, surplus=None, telemetry_integ_ids=None, telemetry_key=None, transmission_serial=None, user_status_ids=None, vehicle_type_ids=None, vin=None, warranty_expires_in_days=None, work_center_ids=None, year_built=None, zone_ids=None, id_accessible=False, language=None): General equipment listing based on custom criteria.
    - get_out_of_service_lists(list_names: list[str] | None = None): Reference lists (CityID, CustomerID, DepartmentGroupID, DepartmentID, MaintainedByID, MakeID, ModelID, PowerID, RegionID, VehicleTypeID, WorkCenterID) for out-of-service detail queries.
    - get_out_of_service_detail(city_ids=None, customer_ids=None, department_group_ids=None, department_ids=None, maintained_by_ids=None, make_ids=None, model_ids=None, power_ids=None, region_ids=None, show_detail=False, vehicle_type_ids=None, work_center_ids=None, id_accessible=False): Detailed list of equipment currently out of service.
    - get_out_of_service_summary(id_accessible=False): Live and snapshot out-of-service summary for all accessible equipment (no filters).
    - get_equipment_transfer_lists(list_names: list[str] | None = None): Reference lists (CityID) for equipment transfer queries.
    - get_equipment_transfers(transfer_dates, city_ids=None, id_accessible=False): History of equipment transferred between cities (transfer_dates required).
    - get_equipment_addupdate_lists(list_names: list[str] | None = None): Reference lists (many, e.g. EquipTypeID, CityID, MeterProfileID, VehicleTypeID, WorkCenterID, VendorID, etc.) for adding/updating equipment.
    - add_update_equipment(equipment_batch=None, mode=None, id=None, ebis_id=None, asset_id_lookup=None, city_abbr_lookup=None, city_id=None, city_no=None, equip_type_id=None, meter_profile_id=None, vehicle_type_id=None, ...many optional fields...): Add or update one or more pieces of equipment. Batch mode via equipment_batch, or single-record mode via mode + fields. Modes: Insert, Update, Activate, Inactivate, PowerChange, ChangeEquipType, ChangeCityNo, Transfer.
    - get_otc_listing_lists(list_names: list[str] | None = None): Reference lists (EBisMainTypeID, CityID, StatusID, CustomerID, TypeID, DepartmentID) for OTC (over-the-counter) listings. EBisMainTypeID: 1=Quote, 2=Invoice, 3=CoreInvoice.
    - get_otc_listing(ebis_main_type_ids=None, back_order_is=None, return_is=None, original_quote_number=None, reminder_due_next_days=None, filter_text=None, include_parts=False, include_misc_charges=False, otc_id=None, city_ids=None, status_ids=None, customer_ids=None, type_ids=None, department_ids=None, show_mine_only=False, accounting_invoice_num=None, buyer_contact=None, buyer_purchase_order=None, created_dates=None, display_dates=None, est_ship_dates=None, has_media=None, has_misc_charges=None, misc_charge=None, notes=None, part_description=None, part_number=None, part_serial_no=None, payment_due_dates=None, processed_dates=None, shipped_dates=None, tracking_number=None, rpt_sort=None, hierarchy="nested", id_accessible=False, language=None, debug_sql=False): Items and totals for OTC transactions (Quotes, Invoices, Core Invoices).

    Pass action-specific keyword arguments via `params`.
    """
    return _dispatch("equipment", action, _EQUIPMENT_ACTIONS, params)


# ---------------------------------------------------------------------------
# Meters
# ---------------------------------------------------------------------------

_METER_ACTIONS = frozenset({
    "get_meter_reading_lists",
    "get_meter_readings",
    "add_update_meter_readings",
})


@mcp.tool()
def meters(action: str, params: dict | None = None) -> dict:
    """Meter reading operations. Set `action` to one of:
    - get_meter_reading_lists(list_names: list[str] | None = None): Reference lists (CityID, ControllerID, CostCenterID, CustomerID, DepartmentID, Engine1ID, FleetConfigID, Make1ID, MeterProfileID, Model1ID, MotorID, PartsCatalogID, PmDocID, Power1ID, RegionID, TelemetryIntegID, UserStatusID, VehicleTypeID, WorkCenterID, ZoneID) for meter reading queries.
    - get_meter_readings(reading_dates, after_paint_date=None, any_license_due_next_days=None, asset_no=None, asset_no_multiple=None, banner_status=None, battery_mgmt_id=None, city_ids=None, city_no_like=None, city_no_multiple=None, contractor=None, controller_ids=None, cost_center_ids=None, customer_ids=None, department_ids=None, ebis_ids=None, engine1_ids=None, engine1_serial=None, engine1_spec_no=None, fleet_config_ids=None, front_axel_serial=None, has_date_based_schedule=False, has_license_no=None, has_linked_parts_list_override=None, has_meter_based_schedule=False, has_pm_part_kit=None, has_pm_part_kit_override=None, has_pm_schedules=None, has_seatbelt=None, inactive_include=False, last_pm_over_days_ago=None, lease_expires_next_days=None, license_no=None, make1_ids=None, meter_profile_ids=None, model1_ids=None, motor_ids=None, only_inactive=False, only_with_telemetry=False, only_with_valid_warranty=False, parts_catalog_ids=None, pm_doc_ids=None, power1_ids=None, rear_axel_serial=None, reflectivity=None, region_ids=None, rental_expires_next_days=None, serial_no=None, show_license_no=False, stationary_loc_multiple=None, surplus=None, telemetry_integ_ids=None, telemetry_key=None, transmission_serial=None, user_status_ids=None, vehicle_type_ids=None, vin=None, warranty_expires_in_days=None, work_center_ids=None, year_built=None, zone_ids=None, hierarchy="nested", id_accessible=False, language=None): Meter reading history for equipment within a date range (reading_dates required).
    - add_update_meter_readings(assets, apply_timezone_conversion=False, use_reading_date=False): Add or update meter readings for a batch of equipment (each asset needs EBisID/RegNum/TelemetryVendorAssetNo plus a Reading).

    Pass action-specific keyword arguments via `params`.
    """
    return _dispatch("meters", action, _METER_ACTIONS, params)


# ---------------------------------------------------------------------------
# Preventive Maintenance
# ---------------------------------------------------------------------------

_PM_ACTIONS = frozenset({
    "get_upcoming_pm_lists",
    "get_upcoming_pm",
})


@mcp.tool()
def preventive_maintenance(action: str, params: dict | None = None) -> dict:
    """Preventive maintenance (PM) operations. Set `action` to one of:
    - get_upcoming_pm_lists(list_names: list[str] | None = None): Reference lists (CityID, RegionID, SummarizeBy, SummarizeByDateGroup, VehicleTypeID, ZoneID) for upcoming PM queries.
    - get_upcoming_pm(city_ids=None, is_powered=None, region_ids=None, show_all_upcoming_wo=False, summarize_by=None, summarize_by_date_group=None, vehicle_type_ids=None, zone_ids=None, id_accessible=False, language=None): Upcoming preventive maintenance information for equipment.

    Pass action-specific keyword arguments via `params`.
    """
    return _dispatch("preventive_maintenance", action, _PM_ACTIONS, params)


# ---------------------------------------------------------------------------
# Parts & Inventory
# ---------------------------------------------------------------------------

_PARTS_INVENTORY_ACTIONS = frozenset({
    "get_masterpart_listing_lists",
    "get_masterpart_listing",
    "get_stock_quantity_detail_lists",
    "get_stock_quantity_detail",
    "get_stock_quantity_log_lists",
    "get_stock_quantity_log",
})


@mcp.tool()
def parts_inventory(action: str, params: dict | None = None) -> dict:
    """Master parts list and stock quantity/inventory operations. Set `action` to one of:
    - get_masterpart_listing_lists(list_names: list[str] | None = None): Reference lists (PartComponentID, PartTypeID, SupplierID) for the master part list.
    - get_masterpart_listing(core_is=None, description_like=None, expiring_shelf_life=None, family_name=None, general_cost_range=None, general_location_range=None, has_alternate=None, has_general_cost=None, has_general_location=False, has_media=None, has_superseded=None, has_unspsc=None, has_warranty_days=None, hazard_is=None, is_serial=None, line_code=None, no_inv_movement=False, no_inv_movement_days=None, part_component_ids=None, part_number_like=None, part_number_range=None, part_type_ids=None, specific_location_range=None, supplier_ids=None, unspsc=None, id_accessible=False): General master part list information.
    - get_stock_quantity_detail_lists(list_names: list[str] | None = None): Reference lists (PartComponentID, PartTypeID, StockRoomID, SupplierID) for stock quantity detail queries.
    - get_stock_quantity_detail(core_is=None, description_like=None, family_name=None, general_location_range=None, has_alternate=None, has_media=None, has_superseded=None, has_warranty_days=None, hazard_is=None, is_serial=None, line_code=None, part_component_ids=None, part_number_like=None, part_number_range=None, part_type_ids=None, qty_customer=None, qty_location_range=None, qty_po_number=None, qty_serial=None, qty_vendor=None, shelf_life_expires_days=None, stock_qty=None, stock_room_ids=None, supplier_ids=None, id_accessible=False): Basic part info plus detailed stock quantity data.
    - get_stock_quantity_log_lists(list_names: list[str] | None = None): Reference lists (StockRoomID) for the stock quantity log.
    - get_stock_quantity_log(dates, description_like=None, part_number_like=None, stock_room_ids=None, user=None, id_accessible=False, debug_sql=False): Inventory quantity and cost change log entries within a date range (dates required).

    Pass action-specific keyword arguments via `params`.
    """
    return _dispatch("parts_inventory", action, _PARTS_INVENTORY_ACTIONS, params)


# ---------------------------------------------------------------------------
# Purchase Orders
# ---------------------------------------------------------------------------

_PURCHASE_ORDER_ACTIONS = frozenset({
    "get_purchase_order_lists",
    "export_purchase_orders",
})


@mcp.tool()
def purchase_orders(action: str, params: dict | None = None) -> dict:
    """Purchase order operations. Set `action` to one of:
    - get_purchase_order_lists(list_names: list[str] | None = None): Reference lists (CityID, IbsID, RegionID, StatusID, VendorID) for purchase order queries.
    - export_purchase_orders(city_ids=None, completed_dates=None, created_by_user=None, ibs_ids=None, include_item_destination_detail=False, include_item_detail=False, include_receiving_info=False, inspect_dates=None, ordered_dates=None, part_number=None, received_dates=None, region_ids=None, rma_number=None, status_ids=None, vendor_ids=None, hierarchy="flat", id_accessible=False): Export purchase order listings including parts and destinations.

    Pass action-specific keyword arguments via `params`.
    """
    return _dispatch("purchase_orders", action, _PURCHASE_ORDER_ACTIONS, params)


# ---------------------------------------------------------------------------
# Service Requests
# ---------------------------------------------------------------------------

_SERVICE_REQUEST_ACTIONS = frozenset({
    "get_service_request_addupdate_lists",
    "add_update_service_request",
})


@mcp.tool()
def service_requests(action: str, params: dict | None = None) -> dict:
    """Service request operations. Set `action` to one of:
    - get_service_request_addupdate_lists(list_names: list[str] | None = None): Reference lists (StatusID, CategoryID, PriorityID) for adding/updating service requests.
    - add_update_service_request(mode, asset_related_id=None, id=None, sr_number=None, status_id=None, category_id=None, priority_id=None, description=None, location=None, request_by_name=None, request_by_phone=None, request_by_email=None, request_by_location=None, did_tag_equipment=None, defer_reject_notes=None, latitude=None, longitude=None, is_system_created=None, is_invalid_telemetry_reason=None, extra_log_info=None, debug_notifications=False): Create ("Insert") or update ("Update") a service request. mode is required.

    Pass action-specific keyword arguments via `params`.
    """
    return _dispatch("service_requests", action, _SERVICE_REQUEST_ACTIONS, params)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

_USER_ACTIONS = frozenset({
    "get_user_lists",
    "get_users",
    "logout_users",
    "get_user_addupdate_lists",
    "add_update_users",
    "get_user_cities_admin_lists",
    "edit_user_cities",
})


@mcp.tool()
def users(action: str, params: dict | None = None) -> dict:
    """User account and access operations. Set `action` to one of:
    - get_user_lists(list_names: list[str] | None = None): Reference lists (TechGroupID, CityID, HomeCityID, PartInspectorCityID, PartInspectorStockRoomID) for querying users.
    - get_users(show_inactive=False, primary_city=None, has_access_city=None, home_city=None, profile_name=None, tech_group_ids=None, mode=None, city_ids=None, valid_emails=None, home_city_ids=None, filter_text=None, page_on=None, page_per=None, find=None, part_inspector=None, part_inspector_city_ids=None, part_inspector_stock_room_ids=None, has_media=False, id_accessible=False): List users for this eBis tenant.
    - logout_users(user_batch=None, stop_active_timers=False, session_logout=False, logout_user_id=None, sso_id=None, username=None): Log one or more users out of eBis, optionally stopping active service timers. Batch mode via user_batch or single-user mode via individual params.
    - get_user_addupdate_lists(list_names: list[str] | None = None): Reference lists (UserID, UserProfileID, TechGroupID, CityDefaultID, CityHomeID, StockRoomDefaultID, PaperSizeID, TimeZoneID, DstID, DateFormatID, TimeFormatID, NumberFormatID, CostAndRetailCurrencyID, BatchSetTechProfileID) for adding/updating users.
    - add_update_users(user_batch=None, mode=None, user_id=None, username=None, password=None, first_name=None, last_name=None, email=None, phone1=None, ...many optional preference/permission fields...): Add or update one or more users. Modes: Insert, Update, ResetPassword, Inactivate, Activate, BatchSetTech. Batch mode via user_batch.
    - get_user_cities_admin_lists(list_names: list[str] | None = None): Reference lists (UserID, AddToUsersWithProfileID, CityID, IbsID, RegionID) for editing user city access.
    - edit_user_cities(mode, user_batch=None, user_id=None, all_cities=None, add_to_all_users=None, add_to_users_with_profile_id=None, email=None, city_ids=None, ibs_ids=None, region_ids=None): Grant ("Insert") or remove ("Delete") city/IBS/region access for one or more users. mode is required.

    Pass action-specific keyword arguments via `params`.
    """
    return _dispatch("users", action, _USER_ACTIONS, params)


# ---------------------------------------------------------------------------
# Vendors
# ---------------------------------------------------------------------------

_VENDOR_ACTIONS = frozenset({
    "get_vendor_listing_lists",
    "get_vendor_listing",
    "get_vendor_addupdate_lists",
    "add_update_vendors",
})


@mcp.tool()
def vendors(action: str, params: dict | None = None) -> dict:
    """Vendor operations. Set `action` to one of:
    - get_vendor_listing_lists(list_names: list[str] | None = None): Reference lists (LimitToCityID, ShipMethodID, TermsID, VendorClassID) for querying vendors.
    - get_vendor_listing(include_inactive=False, account=None, address=None, address2=None, approval_expiring=None, approved=None, cities=None, city=None, contact=None, countries=None, country=None, do_not_create_po=None, email=None, gl_account_number=None, has_media=False, has_warranty_claims=None, inactive=None, is_osr=None, is_supplier=None, is_tools=None, limit_to_city_id=None, phone=None, ship_method_ids=None, state=None, states=None, terms_ids=None, url=None, vendor_class_ids=None, vendor_name=None, zip=None, zips=None, id_accessible=False): Comprehensive list of vendors matching filters.
    - get_vendor_addupdate_lists(list_names: list[str] | None = None): Reference lists (Phone1-4TypeID, TermsID, VendorClassID, CurrencyID, ShipMethodID, ApproveTypeID, WarrantyMakeID, LimitToCityID, TaxID) for adding/updating vendors.
    - add_update_vendors(vendor_batch=None, mode=None, id=None, vendor_name=None, user_validate_temp_token=None, change_to_name=None, contact=None, address=None, address2=None, city=None, state=None, zip=None, country=None, ...many optional fields...): Add or update one or more vendors. Modes: Insert, Update, Delete, Inactivate, Activate, ChangeName. Delete/Inactivate return a confirmation token to resubmit.

    Pass action-specific keyword arguments via `params`.
    """
    return _dispatch("vendors", action, _VENDOR_ACTIONS, params)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
