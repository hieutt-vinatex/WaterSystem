# blueprints/history.py
import logging
from flask import Blueprint, request, jsonify
from models import db, WellProduction, CleanWaterPlant, WaterTank,WaterTankLevel, WastewaterPlant,Customer,CustomerReading,Well
from sqlalchemy import func
from datetime import timedelta
from collections import defaultdict

bp = Blueprint("history", __name__, url_prefix="/api") 
logger = logging.getLogger(__name__)


@bp.route("/well-productions/history", methods=["GET"])
def well_productions_history():
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 30))
    except ValueError:
        return jsonify({"error": "page/per_page must be integers"}), 400

    q = db.session.query(WellProduction)

    well_id = request.args.get("well_id")
    if well_id:
        q = q.filter(WellProduction.well_id == int(well_id))

    q = q.order_by(WellProduction.date.desc(), WellProduction.id.desc())
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)

    items = [
        {
            "id": row.id,
            "well_id": row.well_id,
            "date": row.date.isoformat() if row.date else None,
            "production": float(row.production or 0),
        }
        for row in pagination.items
    ]

    return jsonify(
        {
            "items": items,
            "meta": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "pages": pagination.pages or 1,
                "total": pagination.total,
            },
        }
    )


# blueprints/history.py
@bp.route("/well-productions/history/pivot", methods=["GET"])
def well_productions_history_pivot():
    """
    Bảng pivot: mỗi dòng = 1 ngày, phân trang theo ngày (mặc định 20/ngày).
    Lọc theo 30/60/90 ngày gần nhất qua param range_days (default 30).
    Optional: start_date/end_date sẽ OVERRIDE range_days nếu truyền.
    """
    try:
        page = int(request.args.get("page", 1))
        per_page = 20  # cố định 20 bản ghi / trang
        if page < 1:
            raise ValueError
    except ValueError:
        return jsonify({"error": "page must be a positive integer"}), 400

    # --- Base query ---
    q_base = db.session.query(WellProduction)

    # --- Phạm vi ngày ---
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")
    range_days = int(request.args.get("range_days", 30))
    if range_days not in (30, 60, 90):
        range_days = 30

    if start_date_str or end_date_str:
        # Ưu tiên khoảng ngày truyền vào (nếu có)
        if start_date_str:
            q_base = q_base.filter(WellProduction.date >= start_date_str)
        if end_date_str:
            q_base = q_base.filter(WellProduction.date <= end_date_str)
    else:
        # Dựa trên ngày MỚI NHẤT có trong DB, lấy về N ngày gần nhất
        latest_date = db.session.query(func.max(WellProduction.date)).scalar()
        if latest_date:
            cutoff = latest_date - timedelta(days=range_days - 1)
            q_base = q_base.filter(WellProduction.date >= cutoff)
        else:
            # Không có dữ liệu
            return jsonify(
                {
                    "columns": ["date"],
                    "rows": [],
                    "meta": {"page": 1, "pages": 1, "per_page": per_page, "total": 0},
                }
            )

    # --- Lọc theo danh sách giếng (optional) ---
    well_ids_param = request.args.get("well_ids")
    well_id_list = None
    if well_ids_param:
        try:
            well_id_list = [int(x) for x in well_ids_param.split(",") if x.strip()]
        except Exception:
            return jsonify({"error": "well_ids must be comma-separated integers"}), 400
        if well_id_list:
            q_base = q_base.filter(WellProduction.well_id.in_(well_id_list))

    # --- Lấy danh sách NGÀY distinct để phân trang ---
    dates_q = (
        q_base.with_entities(WellProduction.date)
        .distinct()
        .order_by(WellProduction.date.desc())
    )

    all_dates = [row.date for row in dates_q.all()]  # đã được filter theo range_days
    total_dates = len(all_dates)
    if total_dates == 0:
        return jsonify(
            {
                "columns": ["date"],
                "rows": [],
                "meta": {"page": 1, "pages": 1, "per_page": per_page, "total": 0},
            }
        )

    pages = max(1, (total_dates + per_page - 1) // per_page)
    page = min(page, pages)

    page_dates = all_dates[(page - 1) * per_page : (page - 1) * per_page + per_page]

    # --- Lấy dữ liệu các ngày trong trang và pivot ---
    rs = (db.session.query(
            WellProduction.date,
            Well.code.label('well_code'),
            WellProduction.production
         )
         .join(Well, WellProduction.well_id == Well.id)
         .filter(WellProduction.date.in_(page_dates)))

    if well_id_list:
        rs = rs.filter(WellProduction.well_id.in_(well_id_list))

    rows = rs.all()

    # Danh sách cột = code giếng
    well_codes_in_data = sorted({r.well_code for r in rows})
    well_columns = well_codes_in_data

    from collections import defaultdict
    day_map = defaultdict(dict)  # {date: {well_code: production}}
    for r in rows:
        day_map[r.date][r.well_code] = float(r.production or 0.0)

    page_dates_sorted = sorted(page_dates, reverse=True)

    table_rows = []
    for d in page_dates_sorted:
        row = {"date": d.strftime("%d/%m/%Y")}
        for code in well_codes_in_data:
            row[code] = day_map.get(d, {}).get(code, 0.0)
        table_rows.append(row)

    return jsonify({
        "columns": ["date"] + well_columns,
        "rows": table_rows,
        "meta": {
            "page": page,
            "pages": pages,
            "per_page": per_page,
            "total": total_dates,
            "range_days": range_days,
        },
    })

@bp.route("/clean-water/consumption/history", methods=["GET"])
def clean_water_consumption_history():
    """
    Lịch sử theo ngày cho Nhà máy nước sạch:
    - Cột: date, electricity(kWh), pac_usage(kg), naoh_usage(kg), polymer_usage(kg), clean_water_output(m3), raw_water_jasan(m3)
    - Lọc: range_days in {30,60,90} (mặc định 30) hoặc start_date/end_date override.
    - Phân trang: page (mặc định 1), per_page = 20 (cố định).
    """
    # --- phân trang 20 dòng/trang ---
    try:
        page = int(request.args.get("page", 1))
        if page < 1:
            raise ValueError
    except ValueError:
        return jsonify({"error": "page must be a positive integer"}), 400
    per_page = 20

    # --- base query ---
    q_base = db.session.query(CleanWaterPlant)

    # --- phạm vi ngày ---
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")
    try:
        range_days = int(request.args.get("range_days", 30))
    except ValueError:
        range_days = 30
    if range_days not in (30, 60, 90):
        range_days = 30

    if start_date_str or end_date_str:
        if start_date_str:
            q_base = q_base.filter(CleanWaterPlant.date >= start_date_str)
        if end_date_str:
            q_base = q_base.filter(CleanWaterPlant.date <= end_date_str)
    else:
        latest_date = db.session.query(func.max(CleanWaterPlant.date)).scalar()
        if latest_date:
            cutoff = latest_date - timedelta(days=range_days - 1)
            q_base = q_base.filter(CleanWaterPlant.date >= cutoff)
        else:
            return jsonify(
                {
                    "columns": [
                        "date",
                        "electricity",
                        "pac_usage",
                        "naoh_usage",
                        "polymer_usage",
                        "clean_water_output",
                        "raw_water_jasan",
                    ],
                    "rows": [],
                    "meta": {
                        "page": 1,
                        "pages": 1,
                        "per_page": per_page,
                        "total": 0,
                        "range_days": range_days,
                    },
                }
            )

    # --- danh sách ngày distinct để phân trang (đÃ áp filter) ---
    dates_q = (
        q_base.with_entities(CleanWaterPlant.date)
        .distinct()
        .order_by(CleanWaterPlant.date.desc())
    )
    all_dates = [r.date for r in dates_q.all()]
    total_dates = len(all_dates)
    if total_dates == 0:
        return jsonify(
            {
                "columns": [
                    "date",
                    "electricity",
                    "pac_usage",
                    "naoh_usage",
                    "polymer_usage",
                    "clean_water_output",
                    "raw_water_jasan",
                ],
                "rows": [],
                "meta": {
                    "page": 1,
                    "pages": 1,
                    "per_page": per_page,
                    "total": 0,
                    "range_days": range_days,
                },
            }
        )

    pages = max(1, (total_dates + per_page - 1) // per_page)
    page = min(page, pages)
    page_dates = all_dates[(page - 1) * per_page : (page - 1) * per_page + per_page]

    # --- lấy dữ liệu cho các ngày trong trang ---
    rs = (
        db.session.query(
            CleanWaterPlant.date,
            CleanWaterPlant.electricity,
            CleanWaterPlant.pac_usage,
            CleanWaterPlant.naoh_usage,
            CleanWaterPlant.polymer_usage,
            CleanWaterPlant.clean_water_output,
            CleanWaterPlant.raw_water_jasan,
        )
        .filter(CleanWaterPlant.date.in_(page_dates))
        .order_by(CleanWaterPlant.date.desc())
        .all()
    )

    # --- dựng rows: format ngày dd/mm/YYYY, số -> float ---
    rows = []
    for r in rs:
        rows.append(
            {
                "date": r.date.strftime("%d/%m/%Y"),
                "electricity": float(r.electricity or 0),
                "pac_usage": float(r.pac_usage or 0),
                "naoh_usage": float(r.naoh_usage or 0),
                "polymer_usage": float(r.polymer_usage or 0),
                "clean_water_output": float(r.clean_water_output or 0),
                "raw_water_jasan": float(r.raw_water_jasan or 0),
            }
        )

    # đảm bảo desc theo ngày
    rows.sort(
        key=lambda x: tuple(int(p) for p in x["date"].split("/")[::-1]), reverse=True
    )

    return jsonify(
        {
            "columns": [
                "date",
                "electricity",
                "pac_usage",
                "naoh_usage",
                "polymer_usage",
                "clean_water_output",
                "raw_water_jasan",
            ],
            "rows": rows,
            "meta": {
                "page": page,
                "pages": pages,
                "per_page": per_page,
                "total": total_dates,
                "range_days": range_days,
            },
        }
    )

@bp.route("/water-tanks/history/pivot", methods=["GET"])
def water_tanks_history_pivot():
    """
    Bảng pivot bể chứa: mỗi dòng = 1 ngày, mỗi cột = 1 bể.
    - Lọc: range_days in {30,60,90} (mặc định 30) hoặc start_date/end_date override.
    - Phân trang: page (mặc định 1), per_page = 20 (cố định).
    - Lọc theo danh sách bể: tank_ids="1,2,3" (optional).
    """
    # 1) Phân trang
    try:
        page = int(request.args.get("page", 1))
        if page < 1:
            raise ValueError
    except ValueError:
        return jsonify({"error": "page must be a positive integer"}), 400
    per_page = 20

    # 2) Base query
    q_base = db.session.query(WaterTankLevel)

    # 3) Phạm vi ngày
    start_date_str = request.args.get("start_date")
    end_date_str   = request.args.get("end_date")
    try:
        range_days = int(request.args.get("range_days", 30))
    except ValueError:
        range_days = 30
    if range_days not in (30, 60, 90):
        range_days = 30

    if start_date_str or end_date_str:
        if start_date_str:
            q_base = q_base.filter(WaterTankLevel.date >= start_date_str)
        if end_date_str:
            q_base = q_base.filter(WaterTankLevel.date <= end_date_str)
    else:
        latest_date = db.session.query(func.max(WaterTankLevel.date)).scalar()
        if latest_date:
            cutoff = latest_date - timedelta(days=range_days - 1)
            q_base = q_base.filter(WaterTankLevel.date >= cutoff)
        else:
            return jsonify({
                "columns": ["date"],
                "rows": [],
                "meta": {"page": 1, "pages": 1, "per_page": per_page, "total": 0, "range_days": range_days}
            })

    # 4) Lọc theo danh sách bể (optional)
    tank_ids_param = request.args.get("tank_ids")
    tank_id_list = None
    if tank_ids_param:
        try:
            tank_id_list = [int(x) for x in tank_ids_param.split(",") if x.strip()]
        except Exception:
            return jsonify({"error": "tank_ids must be comma-separated integers"}), 400
        if tank_id_list:
            q_base = q_base.filter(WaterTankLevel.tank_id.in_(tank_id_list))

    # 5) Lấy danh sách NGÀY distinct (đã áp filter) để phân trang
    dates_q = (q_base.with_entities(WaterTankLevel.date)
                     .distinct()
                     .order_by(WaterTankLevel.date.desc()))
    all_dates = [r.date for r in dates_q.all()]
    total_dates = len(all_dates)
    if total_dates == 0:
        return jsonify({
            "columns": ["date"],
            "rows": [],
            "meta": {"page": 1, "pages": 1, "per_page": per_page, "total": 0, "range_days": range_days}
        })

    pages = max(1, (total_dates + per_page - 1) // per_page)
    page = min(page, pages)
    page_dates = all_dates[(page - 1) * per_page : (page - 1) * per_page + per_page]

    # 6) Lấy dữ liệu các ngày trong trang + join để lấy tên bể
    rs = (db.session.query(
            WaterTankLevel.date,
            WaterTankLevel.tank_id,
            WaterTankLevel.level,
            WaterTank.name
          )
          .join(WaterTank, WaterTank.id == WaterTankLevel.tank_id)
          .filter(WaterTankLevel.date.in_(page_dates))
          .all())

    if not rs:
        return jsonify({
            "columns": ["date"],
            "rows": [],
            "meta": {"page": page, "pages": pages, "per_page": per_page, "total": total_dates, "range_days": range_days}
        })

    # 7) Xác định danh sách bể trong trang, giữ thứ tự theo tank_id
    tanks_in_data = sorted({(r.tank_id, r.name) for r in rs}, key=lambda x: x[0])
    # Map tank_id -> label hiển thị
    tank_label = {tid: (name or f"Bể {tid}") for tid, name in tanks_in_data}

    # 8) Pivot: map theo ngày -> {tank_id: level}
    day_map = defaultdict(dict)
    for r in rs:
        day_map[r.date][r.tank_id] = float(r.level or 0.0)

    # 9) Dựng rows theo ngày desc
    page_dates_sorted = sorted(page_dates, reverse=True)
    table_rows = []
    for d in page_dates_sorted:
        row = {"date": d.strftime("%d/%m/%Y")}
        for tid, _name in tanks_in_data:
            row[tank_label[tid]] = day_map.get(d, {}).get(tid, 0.0)
        table_rows.append(row)

    # 10) Columns
    columns = ["date"] + [tank_label[tid] for tid, _ in tanks_in_data]

    return jsonify({
        "columns": columns,
        "rows": table_rows,
        "meta": {
            "page": page, "pages": pages, "per_page": per_page,
            "total": total_dates, "range_days": range_days
        }
    })

@bp.route("/wastewater/history/pivot", methods=["GET"])
def wastewater_history_pivot():
    """
    Lịch sử nước thải (pivot theo ngày).
    Params:
      - range_days: 30|60|90 (default 30)
      - page: trang (default 1), per_page cố định 20
      - plant_numbers: "1,2" (optional) -> lọc theo NMNT
      - aggregate: true|false (default false) -> gộp tổng
      - include_extra: true|false (default false) -> thêm cột nâng cao
    """
    per_page = 20
    page = max(1, int(request.args.get("page", 1)))
    range_days = int(request.args.get("range_days", 30))
    if range_days not in (30, 60, 90): range_days = 30

    # lọc nhà máy
    plant_param = request.args.get("plant_numbers", "")
    plant_list = [int(x) for x in plant_param.split(",") if x.strip().isdigit()] or [1, 2]

    aggregate = (request.args.get("aggregate", "false").lower() == "true")
    include_extra = (request.args.get("include_extra", "false").lower() == "true")

    q_base = db.session.query(WastewaterPlant).filter(WastewaterPlant.plant_number.in_(plant_list))

    # phạm vi ngày
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    if start_date or end_date:
        if start_date: q_base = q_base.filter(WastewaterPlant.date >= start_date)
        if end_date:   q_base = q_base.filter(WastewaterPlant.date <= end_date)
    else:
        latest = db.session.query(func.max(WastewaterPlant.date)).scalar()
        if not latest:
            return jsonify({"columns":["date"], "rows":[], "meta":{"page":1,"pages":1,"per_page":per_page,"total":0,"range_days":range_days}})
        cutoff = latest - timedelta(days=range_days-1)
        q_base = q_base.filter(WastewaterPlant.date >= cutoff)

    # ngày distinct để phân trang
    dates_q = (q_base.with_entities(WastewaterPlant.date).distinct().order_by(WastewaterPlant.date.desc()))
    all_dates = [r.date for r in dates_q.all()]
    total_dates = len(all_dates)
    pages = max(1, (total_dates + per_page - 1) // per_page)
    page = min(page, pages)
    page_dates = all_dates[(page-1)*per_page:(page-1)*per_page+per_page]

    # lấy dữ liệu trang
    rs = (db.session.query(
            WastewaterPlant.date,
            WastewaterPlant.plant_number,
            WastewaterPlant.wastewater_meter,
            WastewaterPlant.input_flow_tqt,
            WastewaterPlant.output_flow_tqt,
            WastewaterPlant.sludge_output,
            WastewaterPlant.electricity,
            WastewaterPlant.chemical_usage,
        )
        .filter(WastewaterPlant.date.in_(page_dates),
                WastewaterPlant.plant_number.in_(plant_list))
        .all())

    # pivot
    from collections import defaultdict
    day_map = defaultdict(lambda: defaultdict(dict))
    for r in rs:
        p = r.plant_number
        d = r.date
        day_map[d][p] = {
            "meter": float(r.wastewater_meter or 0),
            "in": float(r.input_flow_tqt or 0),
            "out": float(r.output_flow_tqt or 0),
            "sludge": float(r.sludge_output or 0),
            "elec": float(r.electricity or 0),
            "chem": float(r.chemical_usage or 0),
        }

    # columns
    columns = ["date"]
    if aggregate:
        columns += ["Tổng — Đầu vào (m³)", "Tổng — Đầu ra (m³)"]
        if include_extra:
            columns += ["Tổng — Đồng hồ (m³)", "Tổng — Bùn thải (m³)", "Tổng — Điện (kWh)", "Tổng — Hóa chất (kg)"]
    else:
        for p in sorted(set(plant_list)):
            columns += [f"NMNT{p} — Đầu vào (m³)", f"NMNT{p} — Đầu ra (m³)"]
        if include_extra:
            for p in sorted(set(plant_list)):
                columns += [f"NMNT{p} — Đồng hồ (m³)", f"NMNT{p} — Bùn (m³)", f"NMNT{p} — Điện (kWh)", f"NMNT{p} — Hóa chất (kg)"]

    # rows
    rows = []
    for d in sorted(page_dates, reverse=True):
        row = {"date": d.strftime("%d/%m/%Y")}
        if aggregate:
            total = {"meter":0,"in":0,"out":0,"sludge":0,"elec":0,"chem":0}
            for p in plant_list:
                for k in total:
                    total[k] += day_map[d].get(p, {}).get(k, 0.0)
            row["Tổng — Đầu vào (m³)"] = total["in"]
            row["Tổng — Đầu ra (m³)"] = total["out"]
            if include_extra:
                row["Tổng — Đồng hồ (m³)"] = total["meter"]
                row["Tổng — Bùn thải (m³)"] = total["sludge"]
                row["Tổng — Điện (kWh)"]    = total["elec"]
                row["Tổng — Hóa chất (kg)"] = total["chem"]
        else:
            for p in sorted(set(plant_list)):
                vals = day_map[d].get(p, {})
                row[f"NMNT{p} — Đầu vào (m³)"] = vals.get("in", 0.0)
                row[f"NMNT{p} — Đầu ra (m³)"]  = vals.get("out", 0.0)
            if include_extra:
                for p in sorted(set(plant_list)):
                    vals = day_map[d].get(p, {})
                    row[f"NMNT{p} — Đồng hồ (m³)"] = vals.get("meter", 0.0)
                    row[f"NMNT{p} — Bùn (m³)"]     = vals.get("sludge", 0.0)
                    row[f"NMNT{p} — Điện (kWh)"]   = vals.get("elec", 0.0)
                    row[f"NMNT{p} — Hóa chất (kg)"]= vals.get("chem", 0.0)
        rows.append(row)

    return jsonify({
        "columns": columns,
        "rows": rows,
        "meta": {
            "page": page, "pages": pages, "per_page": per_page,
            "total": total_dates, "range_days": range_days,
            "aggregate": aggregate, "plants": plant_list,
            "include_extra": include_extra
        }
    })

@bp.route("/customer-readings/history", methods=["GET"])
def customer_readings_history():
    """
    Lịch sử chỉ số khách hàng (dạng danh sách).
    - range_days: 30|60|90 (default 30), hoặc start_date/end_date override
    - page: mặc định 1 (per_page cố định 20)
    - q: chuỗi tìm kiếm (company_name LIKE)
    - type: daily | monthly (lọc theo customer.daily_reading)
    - customer_ids: "1,2,3" (optional)
    Trả về: (date, company_name, type, ratio, clean_1, clean_2, wastewater_value, source)
      wastewater_value = wastewater_reading (nếu có) else wastewater_calculated
      source = "actual" | "calculated"
    """
    # phân trang
    try:
        page = int(request.args.get("page", 1))
        if page < 1:
            raise ValueError
    except ValueError:
        return jsonify({"error": "page must be a positive integer"}), 400
    per_page = 20

    # base query join khách hàng
    q = (db.session.query(
            CustomerReading.id,
            CustomerReading.date,
            Customer.company_name,
            Customer.daily_reading,
            Customer.water_ratio,
            CustomerReading.clean_water_reading,
            CustomerReading.clean_water_reading_2,
            CustomerReading.wastewater_reading,
            CustomerReading.wastewater_calculated,
        )
        .join(Customer, Customer.id == CustomerReading.customer_id)
    )

    # phạm vi ngày
    start_date_str = request.args.get("start_date")
    end_date_str   = request.args.get("end_date")
    try:
        range_days = int(request.args.get("range_days", 30))
    except ValueError:
        range_days = 30
    if range_days not in (30, 60, 90):
        range_days = 30

    if start_date_str or end_date_str:
        if start_date_str:
            q = q.filter(CustomerReading.date >= start_date_str)
        if end_date_str:
            q = q.filter(CustomerReading.date <= end_date_str)
    else:
        latest = db.session.query(func.max(CustomerReading.date)).scalar()
        if latest:
            cutoff = latest - timedelta(days=range_days - 1)
            q = q.filter(CustomerReading.date >= cutoff)
        else:
            return jsonify({
                "columns": ["date","company","type","ratio","clean_1","clean_2","wastewater","source"],
                "rows": [],
                "meta": {"page":1,"pages":1,"per_page":per_page,"total":0,"range_days":range_days}
            })

    # lọc theo type
    type_filter = (request.args.get("type") or "").strip().lower()
    if type_filter in ("daily","monthly"):
        is_daily = (type_filter == "daily")
        q = q.filter(Customer.daily_reading == is_daily)

    # lọc theo customer_ids
    ids_param = request.args.get("customer_ids")
    if ids_param:
        try:
            id_list = [int(x) for x in ids_param.split(",") if x.strip()]
        except Exception:
            return jsonify({"error":"customer_ids must be comma-separated integers"}), 400
        if id_list:
            q = q.filter(CustomerReading.customer_id.in_(id_list))

    # search theo tên công ty
    q_text = (request.args.get("q") or "").strip()
    if q_text:
        like_expr = f"%{q_text}%"
        q = q.filter(Customer.company_name.ilike(like_expr))

    # order mới nhất trước
    q = q.order_by(CustomerReading.date.desc(), CustomerReading.id.desc())

    # paginate
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)

    def _row_to_dict(row):
        # tính nước thải hiển thị & nguồn
        if row.wastewater_reading is not None:
            ww_val = float(row.wastewater_reading or 0)
            source = "actual"
        else:
            ww_val = float(row.wastewater_calculated or 0)
            source = "calculated"
        return {
            "date": row.date.strftime("%d/%m/%Y") if row.date else None,
            "company": row.company_name,
            "type": "Hàng ngày" if row.daily_reading else "Hàng tháng",
            "ratio": float(row.water_ratio or 0),
            "clean_1": float(row.clean_water_reading or 0),
            "clean_2": float(row.clean_water_reading_2 or 0),
            "wastewater": ww_val,
            "source": source
        }

    items = [_row_to_dict(row) for row in pagination.items]

    return jsonify({
        "columns": ["date","company","type","ratio","clean_1","clean_2","wastewater","source"],
        "rows": items,
        "meta": {
            "page": pagination.page,
            "pages": pagination.pages or 1,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "range_days": range_days,
            "type": type_filter or ""
        }
    })