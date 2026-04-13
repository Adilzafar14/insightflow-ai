import pandas as pd
import numpy as np

def detect_industry(df):
    # Use exact column name matching — much more reliable
    cols = set([c.lower().strip() for c in df.columns])

    # Strict hospital indicators — unique to hospital data
    hospital_must = {"treatment_cost", "disease", "admission_date", "discharge_date", "doctor_name"}
    if len(hospital_must & cols) >= 2:
        return "hospital"

    # Strict logistics indicators
    logistics_must = {"shipment_cost", "shipment_id", "distance_km", "vehicle_type", "fuel_cost"}
    if len(logistics_must & cols) >= 2:
        return "logistics"

    # Strict ecommerce indicators
    ecommerce_must = {"product_price", "order_id", "order_date", "order_status", "discount"}
    if len(ecommerce_must & cols) >= 2:
        return "ecommerce"

    # Strict education indicators
    education_must = {"student_id", "cgpa", "attendance_percentage", "fees_paid", "placement_status", "backlogs", "semester"}
    if len(education_must & cols) >= 2:
        return "education"

    # Fallback: broader keyword matching
    col_str = " ".join(cols)
    if any(w in col_str for w in ["treatment", "prescription", "ward", "discharge"]):
        return "hospital"
    if any(w in col_str for w in ["shipment", "freight", "warehouse", "delivery_date"]):
        return "logistics"
    if any(w in col_str for w in ["product_price", "order_id", "cart", "sku"]):
        return "ecommerce"
    if any(w in col_str for w in ["cgpa", "semester", "enrollment", "backlog", "hostel"]):
        return "education"

    return "generic"

# ══════════════════════════════════════════════════════════════════
# DATA CLEANING
# ══════════════════════════════════════════════════════════════════
def clean_data(df):
    report = {"fixes": [], "warnings": []}
    orig_rows = len(df)

    # Strip column names (keep original case for detection)
    df.columns = [str(c).strip() for c in df.columns]

    # Remove duplicates
    before = len(df)
    df.drop_duplicates(inplace=True)
    removed = before - len(df)
    if removed: report["fixes"].append(f"✅ {removed} duplicate rows removed")

    # Drop all-empty rows
    df.dropna(how="all", inplace=True)

    # Parse date columns
    for col in df.columns:
        if any(k in col.lower() for k in ["date", "_at", "time", "dob"]):
            if df[col].dtype == object:
                parsed = pd.to_datetime(df[col], errors="coerce", infer_datetime_format=True)
                if parsed.notna().mean() > 0.7:
                    df[col] = parsed
                    report["fixes"].append(f"✅ '{col}' → datetime")

    # Fill missing values
    for col in df.columns:
        miss = df[col].isnull().mean()
        if miss == 0: continue
        if miss > 0.4: report["warnings"].append(f"⚠️ '{col}' has {miss*100:.0f}% missing values")
        if pd.api.types.is_numeric_dtype(df[col]):
            df[col].fillna(df[col].median(), inplace=True)
        else:
            mode = df[col].mode()
            df[col].fillna(mode[0] if len(mode) else "Unknown", inplace=True)

    score = max(0, min(100, round(100 - len(report["warnings"]) * 8 - (orig_rows - len(df)) / max(orig_rows, 1) * 20, 1)))
    report["score"] = score
    return df.reset_index(drop=True), report

# ══════════════════════════════════════════════════════════════════
# INDUSTRY PROCESSORS
# ══════════════════════════════════════════════════════════════════
def process_hospital(df):
    kpis = {}; charts = {}; insights = []

    # Find columns
    def fc(*keys):
        for k in keys:
            for c in df.columns:
                if k.lower() == c.lower(): return c
                if k.lower() in c.lower(): return c
        return None

    cost_col   = fc("Treatment_Cost", "Cost", "Revenue", "Amount", "Fee")
    dept_col   = fc("Department", "Dept", "Ward")
    dis_col    = fc("Disease", "Diagnosis", "Condition")
    status_col = fc("Status")
    age_col    = fc("Age")
    gender_col = fc("Gender", "Sex")
    pay_col    = fc("Payment_Mode", "Payment", "Pay_Mode")
    doc_col    = fc("Doctor_Name", "Doctor", "Physician")
    city_col   = fc("City", "Location")
    adm_col    = fc("Admission_Date", "Admission", "Admit_Date")
    dis_date   = fc("Discharge_Date", "Discharge")

    kpis["Total Patients"] = len(df)

    if age_col:
        kpis["Avg Age"] = round(df[age_col].mean(), 1)

    if cost_col and df[cost_col].dtype != object:
        kpis["Total Revenue"] = round(df[cost_col].sum(), 0)
        kpis["Avg Cost/Patient"] = round(df[cost_col].mean(), 0)
        kpis["Max Cost"] = round(df[cost_col].max(), 0)

    if adm_col and dis_date:
        df["_LOS"] = (pd.to_datetime(df[dis_date], errors="coerce") - pd.to_datetime(df[adm_col], errors="coerce")).dt.days.abs()
        kpis["Avg Length of Stay"] = round(df["_LOS"].mean(), 1)

    if status_col:
        sv = df[status_col].value_counts()
        for s in sv.index:
            if "critical" in str(s).lower():
                kpis["Critical Rate"] = round(sv[s] / len(df) * 100, 1)
            if "recover" in str(s).lower():
                kpis["Recovery Rate"] = round(sv[s] / len(df) * 100, 1)
        charts["status"] = {"type": "pie", "data": sv.reset_index().rename(columns={status_col: "Status", "count": "Count"}).to_dict("records"), "names": "Status", "values": "Count", "title": "Patient Status"}

    if dept_col:
        if cost_col:
            dr = df.groupby(dept_col)[cost_col].sum().sort_values(ascending=False)
            charts["dept_revenue"] = {"type": "bar_h", "data": dr.reset_index().rename(columns={dept_col: "Department", cost_col: "Revenue"}).to_dict("records"), "x": "Revenue", "y": "Department", "title": "Revenue by Department"}
        dp = df[dept_col].value_counts()
        kpis["Top Department"] = dp.idxmax()
        charts["dept_patients"] = {"type": "bar_h", "data": dp.reset_index().rename(columns={dept_col: "Department", "count": "Patients"}).to_dict("records"), "x": "Patients", "y": "Department", "title": "Patients by Department"}

    if dis_col:
        dv = df[dis_col].value_counts().head(8)
        kpis["Top Disease"] = dv.idxmax()
        charts["diseases"] = {"type": "bar_h", "data": dv.reset_index().rename(columns={dis_col: "Disease", "count": "Cases"}).to_dict("records"), "x": "Cases", "y": "Disease", "title": "Top Diseases"}

    if gender_col:
        gv = df[gender_col].value_counts()
        charts["gender"] = {"type": "pie", "data": gv.reset_index().rename(columns={gender_col: "Gender", "count": "Count"}).to_dict("records"), "names": "Gender", "values": "Count", "title": "Gender Distribution"}

    if pay_col:
        pv = df[pay_col].value_counts()
        charts["payment"] = {"type": "pie", "data": pv.reset_index().rename(columns={pay_col: "Mode", "count": "Count"}).to_dict("records"), "names": "Mode", "values": "Count", "title": "Payment Mode"}

    if city_col:
        cv = df[city_col].value_counts().head(8)
        charts["city"] = {"type": "bar_h", "data": cv.reset_index().rename(columns={city_col: "City", "count": "Patients"}).to_dict("records"), "x": "Patients", "y": "City", "title": "Patients by City"}

    if adm_col:
        df["_month"] = pd.to_datetime(df[adm_col], errors="coerce").dt.to_period("M").astype(str)
        mt = df.groupby("_month").size().reset_index(name="Patients")
        mt.columns = ["Month", "Patients"]
        charts["monthly_patients"] = {"type": "line", "data": mt.to_dict("records"), "x": "Month", "y": "Patients", "title": "Monthly Patients"}
        if cost_col:
            mr = df.groupby("_month")[cost_col].sum().reset_index()
            mr.columns = ["Month", "Revenue"]
            charts["monthly_revenue"] = {"type": "line", "data": mr.to_dict("records"), "x": "Month", "y": "Revenue", "title": "Monthly Revenue"}

    # Bivariate
    if age_col and cost_col:
        charts["age_vs_cost"] = {"type": "scatter", "df_x": age_col, "df_y": cost_col, "color": dept_col, "title": "Age vs Treatment Cost"}

    if dept_col and "_LOS" in df.columns:
        lb = df.groupby(dept_col)["_LOS"].mean().sort_values(ascending=False).reset_index()
        lb.columns = ["Department", "Avg_LOS"]
        charts["dept_los"] = {"type": "bar_h", "data": lb.to_dict("records"), "x": "Avg_LOS", "y": "Department", "title": "Avg Length of Stay by Dept"}

    # Insights
    rev = kpis.get("Total Revenue", 0)
    pts = kpis.get("Total Patients", 0)
    cr  = kpis.get("Critical Rate", 0)
    rr  = kpis.get("Recovery Rate", 0)
    los = kpis.get("Avg Length of Stay", 0)

    insights.append(("info", f"🏥 **{pts:,} patients** analyzed | Total Revenue: **₹{rev/1e7:.2f}Cr** | Avg Cost: **₹{kpis.get('Avg Cost/Patient', 0):,.0f}**"))
    if cr: insights.append(("danger" if cr > 25 else "warn" if cr > 15 else "good", f"{'🚨' if cr>25 else '⚠️' if cr>15 else '✅'} Critical Rate: **{cr:.1f}%** {'— Very high! ICU protocols review karo' if cr>25 else '— Monitor closely' if cr>15 else '— Under control'}"))
    if rr: insights.append(("good" if rr > 30 else "warn", f"{'✅' if rr>30 else '⚠️'} Recovery Rate: **{rr:.1f}%** {'— Good outcomes!' if rr>30 else '— Improve treatment protocols'}"))
    if los: insights.append(("warn" if los > 7 else "good", f"{'⚠️' if los>7 else '✅'} Avg Stay: **{los:.1f} days** {'— High, optimize discharge planning' if los>7 else '— Optimal range'}"))
    if dept_col: insights.append(("info", f"🏨 Busiest Department: **{kpis.get('Top Department', '—')}** | Top Disease: **{kpis.get('Top Disease', '—')}**"))

    return kpis, charts, insights

def process_ecommerce(df):
    kpis = {}; charts = {}; insights = []

    def fc(*keys):
        for k in keys:
            for c in df.columns:
                if k.lower() == c.lower(): return c
                if k.lower() in c.lower(): return c
        return None

    price_col  = fc("Product_Price", "Price", "Unit_Price", "Amount")
    qty_col    = fc("Quantity", "Qty", "Units")
    disc_col   = fc("Discount", "Discount_Pct", "Disc")
    date_col   = fc("Order_Date", "Date", "Created_At")
    cat_col    = fc("Category", "Product_Category", "Type")
    pay_col    = fc("Payment_Mode", "Payment_Method", "Payment")
    city_col   = fc("City", "Location", "State")
    status_col = fc("Order_Status", "Status")
    cust_col   = fc("Customer_ID", "Customer", "Cust_ID")

    kpis["Total Orders"] = len(df)

    if cust_col:
        kpis["Unique Customers"] = df[cust_col].nunique()

    # Core revenue calculation
    if price_col and qty_col:
        df["_revenue"] = pd.to_numeric(df[price_col], errors="coerce") * pd.to_numeric(df[qty_col], errors="coerce")
        df["_revenue"].fillna(0, inplace=True)
        if disc_col:
            df["_discount_pct"] = pd.to_numeric(df[disc_col], errors="coerce").fillna(0)
            df["_net_revenue"] = df["_revenue"] * (1 - df["_discount_pct"] / 100)
        else:
            df["_net_revenue"] = df["_revenue"]

        kpis["Gross Revenue"]     = round(float(df["_revenue"].sum()), 0)
        kpis["Net Revenue"]       = round(float(df["_net_revenue"].sum()), 0)
        kpis["Avg Order Value"]   = round(float(df["_revenue"].mean()), 0)

        if disc_col:
            kpis["Avg Discount"] = round(float(df["_discount_pct"].mean()), 1)

    # Date trends
    if date_col:
        df["_month"] = pd.to_datetime(df[date_col], errors="coerce").dt.to_period("M").astype(str)
        mt = df.groupby("_month").size().reset_index(name="Orders")
        mt.columns = ["Month", "Orders"]
        charts["monthly_orders"] = {"type": "line", "data": mt.to_dict("records"), "x": "Month", "y": "Orders", "title": "Monthly Orders"}
        if "_net_revenue" in df.columns:
            mr = df.groupby("_month")["_net_revenue"].sum().reset_index()
            mr.columns = ["Month", "Revenue"]
            charts["monthly_revenue"] = {"type": "line", "data": mr.to_dict("records"), "x": "Month", "y": "Revenue", "title": "Monthly Net Revenue"}

    if cat_col and "_net_revenue" in df.columns:
        cr = df.groupby(cat_col)["_net_revenue"].sum().sort_values(ascending=False)
        kpis["Top Category"] = cr.idxmax()
        charts["category_revenue"] = {"type": "bar_h", "data": cr.reset_index().rename(columns={cat_col: "Category", "_net_revenue": "Revenue"}).to_dict("records"), "x": "Revenue", "y": "Category", "title": "Net Revenue by Category"}
        co = df[cat_col].value_counts()
        charts["category_orders"] = {"type": "pie", "data": co.reset_index().rename(columns={cat_col: "Category", "count": "Orders"}).to_dict("records"), "names": "Category", "values": "Orders", "title": "Orders by Category"}

    if pay_col:
        pv = df[pay_col].value_counts()
        charts["payment"] = {"type": "pie", "data": pv.reset_index().rename(columns={pay_col: "Mode", "count": "Orders"}).to_dict("records"), "names": "Mode", "values": "Orders", "title": "Payment Mode"}

    if status_col:
        sv = df[status_col].value_counts()
        charts["order_status"] = {"type": "pie", "data": sv.reset_index().rename(columns={status_col: "Status", "count": "Orders"}).to_dict("records"), "names": "Status", "values": "Orders", "title": "Order Status"}
        returned = df[status_col].str.lower().isin(["returned", "cancelled", "cancel"]).mean() * 100
        kpis["Return/Cancel Rate"] = round(returned, 1)

    if city_col and "_net_revenue" in df.columns:
        cv = df.groupby(city_col)["_net_revenue"].sum().sort_values(ascending=False).head(8)
        kpis["Top City"] = cv.idxmax()
        charts["city_revenue"] = {"type": "bar_h", "data": cv.reset_index().rename(columns={city_col: "City", "_net_revenue": "Revenue"}).to_dict("records"), "x": "Revenue", "y": "City", "title": "Revenue by City"}

    # Bivariate: Price vs Quantity
    if price_col and qty_col:
        charts["price_vs_qty"] = {"type": "scatter", "df_x": price_col, "df_y": qty_col, "color": cat_col, "title": "Price vs Quantity"}

    # Insights
    gr  = kpis.get("Gross Revenue", 0)
    nr  = kpis.get("Net Revenue", 0)
    aov = kpis.get("Avg Order Value", 0)
    rc  = kpis.get("Return/Cancel Rate", 0)
    ad  = kpis.get("Avg Discount", 0)

    insights.append(("info", f"🛒 **{kpis['Total Orders']:,} orders** | Gross: **₹{gr/1e7:.2f}Cr** | Net (after discount): **₹{nr/1e7:.2f}Cr**"))
    if ad: insights.append(("warn" if ad > 20 else "good", f"{'⚠️' if ad>20 else '✅'} Avg Discount: **{ad:.1f}%** {'— High! Margin impact hoga' if ad>20 else '— Reasonable'}"))
    insights.append(("info", f"📦 Avg Order Value: **₹{aov:,.0f}** | Unique Customers: **{kpis.get('Unique Customers', 'N/A')}**"))
    if rc: insights.append(("danger" if rc > 15 else "warn" if rc > 8 else "good", f"{'🔴' if rc>15 else '⚠️' if rc>8 else '✅'} Return/Cancel Rate: **{rc:.1f}%** {'— Very high!' if rc>15 else '— Monitor' if rc>8 else '— Good'}"))
    if cat_col: insights.append(("info", f"⭐ Top Category: **{kpis.get('Top Category', '—')}** | Top City: **{kpis.get('Top City', '—')}**"))

    return kpis, charts, insights

def process_logistics(df):
    kpis = {}; charts = {}; insights = []

    def fc(*keys):
        for k in keys:
            for c in df.columns:
                if k.lower() == c.lower(): return c
                if k.lower() in c.lower(): return c
        return None

    cost_col    = fc("Shipment_Cost", "Freight_Cost", "Cost", "Revenue")
    fuel_col    = fc("Fuel_Cost", "Fuel")
    dist_col    = fc("Distance_KM", "Distance", "KM")
    ship_date   = fc("Shipment_Date", "Dispatch_Date", "Ship_Date")
    del_date    = fc("Delivery_Date", "Delivered_Date")
    status_col  = fc("Status")
    vehicle_col = fc("Vehicle_Type", "Vehicle", "Transport")
    wh_col      = fc("Warehouse", "Hub", "Depot")
    origin_col  = fc("Origin", "Source", "From_City")
    dest_col    = fc("Destination", "Dest", "To_City")

    kpis["Total Shipments"] = len(df)

    if cost_col:
        kpis["Total Revenue"]   = round(float(df[cost_col].sum()), 0)
        kpis["Avg Cost"]        = round(float(df[cost_col].mean()), 0)

    if fuel_col:
        kpis["Total Fuel Cost"] = round(float(df[fuel_col].sum()), 0)
        if cost_col:
            kpis["Fuel % of Revenue"] = round(float(df[fuel_col].sum() / df[cost_col].sum() * 100), 1)

    if dist_col and cost_col:
        kpis["Avg Cost/KM"] = round(float((pd.to_numeric(df[cost_col], errors="coerce") / pd.to_numeric(df[dist_col], errors="coerce")).mean()), 0)

    if ship_date and del_date:
        df["_transit"] = (pd.to_datetime(df[del_date], errors="coerce") - pd.to_datetime(df[ship_date], errors="coerce")).dt.days.abs()
        kpis["Avg Transit Days"] = round(float(df["_transit"].mean()), 1)
        kpis["Max Transit Days"] = int(df["_transit"].max())

    if status_col:
        sv = df[status_col].value_counts()
        charts["status"] = {"type": "pie", "data": sv.reset_index().rename(columns={status_col: "Status", "count": "Count"}).to_dict("records"), "names": "Status", "values": "Count", "title": "Shipment Status"}
        delivered = df[status_col].str.lower().isin(["delivered"]).mean() * 100
        delayed   = df[status_col].str.lower().isin(["delayed"]).mean() * 100
        kpis["Delivery Rate"] = round(delivered, 1)
        kpis["Delay Rate"]    = round(delayed, 1)

    if vehicle_col and cost_col:
        vr = df.groupby(vehicle_col)[cost_col].sum().sort_values(ascending=False)
        charts["vehicle_revenue"] = {"type": "bar_h", "data": vr.reset_index().rename(columns={vehicle_col: "Vehicle", cost_col: "Revenue"}).to_dict("records"), "x": "Revenue", "y": "Vehicle", "title": "Revenue by Vehicle"}
        vc = df[vehicle_col].value_counts()
        charts["vehicle_count"] = {"type": "pie", "data": vc.reset_index().rename(columns={vehicle_col: "Vehicle", "count": "Shipments"}).to_dict("records"), "names": "Vehicle", "values": "Shipments", "title": "Shipments by Vehicle"}

    if wh_col and cost_col:
        wr = df.groupby(wh_col)[cost_col].sum().sort_values(ascending=False)
        charts["warehouse"] = {"type": "bar_h", "data": wr.reset_index().rename(columns={wh_col: "Warehouse", cost_col: "Revenue"}).to_dict("records"), "x": "Revenue", "y": "Warehouse", "title": "Revenue by Warehouse"}

    if origin_col and dest_col:
        df["_route"] = df[origin_col].astype(str) + " → " + df[dest_col].astype(str)
        rv = df["_route"].value_counts().head(10)
        kpis["Busiest Route"] = rv.idxmax()
        charts["routes"] = {"type": "bar_h", "data": rv.reset_index().rename(columns={"_route": "Route", "count": "Shipments"}).to_dict("records"), "x": "Shipments", "y": "Route", "title": "Top Routes"}

    if ship_date:
        df["_month"] = pd.to_datetime(df[ship_date], errors="coerce").dt.to_period("M").astype(str)
        mt = df.groupby("_month").size().reset_index(name="Shipments")
        mt.columns = ["Month", "Shipments"]
        charts["monthly"] = {"type": "line", "data": mt.to_dict("records"), "x": "Month", "y": "Shipments", "title": "Monthly Shipments"}
        if cost_col:
            mr = df.groupby("_month")[cost_col].sum().reset_index()
            mr.columns = ["Month", "Revenue"]
            charts["monthly_revenue"] = {"type": "line", "data": mr.to_dict("records"), "x": "Month", "y": "Revenue", "title": "Monthly Revenue"}

    # Bivariate
    if dist_col and cost_col:
        charts["dist_vs_cost"] = {"type": "scatter", "df_x": dist_col, "df_y": cost_col, "color": vehicle_col, "title": "Distance vs Cost"}

    # Insights
    rev = kpis.get("Total Revenue", 0)
    dr  = kpis.get("Delivery Rate", 0)
    dlr = kpis.get("Delay Rate", 0)
    tr  = kpis.get("Avg Transit Days", 0)
    fp  = kpis.get("Fuel % of Revenue", 0)

    insights.append(("info", f"🚚 **{kpis['Total Shipments']:,} shipments** | Revenue: **₹{rev/1e5:.1f}L** | Avg: **₹{kpis.get('Avg Cost', 0):,.0f}**"))
    if dr: insights.append(("good" if dr > 80 else "warn" if dr > 50 else "danger", f"{'✅' if dr>80 else '⚠️' if dr>50 else '🔴'} Delivery Rate: **{dr:.1f}%** {'— Excellent!' if dr>80 else '— Needs improvement' if dr>50 else '— Critical!'}"))
    if dlr: insights.append(("good" if dlr < 10 else "warn" if dlr < 20 else "danger", f"{'✅' if dlr<10 else '⚠️' if dlr<20 else '🔴'} Delay Rate: **{dlr:.1f}%** {'— Low delays!' if dlr<10 else '— Monitor' if dlr<20 else '— Very high delays!'}"))
    if tr: insights.append(("info", f"📅 Avg Transit: **{tr:.1f} days** | Max: **{kpis.get('Max Transit Days', '—')} days**"))
    if fp: insights.append(("warn" if fp > 35 else "good", f"{'⚠️' if fp>35 else '✅'} Fuel Cost: **{fp:.1f}% of revenue** {'— Optimize routes!' if fp>35 else '— Efficient'}"))
    insights.append(("info", f"🛣️ Avg Cost/KM: **₹{kpis.get('Avg Cost/KM', 0)}** | Busiest Route: **{kpis.get('Busiest Route', '—')}**"))

    return kpis, charts, insights

def process_education(df):
    kpis = {}; charts = {}; insights = []

    def fc(*keys):
        for k in keys:
            for c in df.columns:
                if k.lower() == c.lower(): return c
                if k.lower() in c.lower(): return c
        return None

    att_col     = fc("Attendance_Percentage", "Attendance", "Att_Pct")
    cgpa_col    = fc("CGPA", "GPA", "Score", "Marks")
    fee_col     = fc("Fees_Paid", "Fee", "Amount", "Fees")
    dept_col    = fc("Department", "Branch", "Stream", "Course")
    place_col   = fc("Placement_Status", "Placement", "Placed")
    company_col = fc("Company_Name", "Company", "Employer")
    pkg_col     = fc("Package_LPA", "Package", "LPA", "Salary")
    gender_col  = fc("Gender", "Sex")
    city_col    = fc("City", "Location")
    scholar_col = fc("Scholarship")
    hostel_col  = fc("Hostel")
    intern_col  = fc("Internship_Status", "Internship")
    backlog_col = fc("Backlogs", "Backlog")
    year_col    = fc("Year")

    kpis["Total Students"] = len(df)

    if att_col:
        kpis["Avg Attendance %"]   = round(float(df[att_col].mean()), 1)
        low_att = int((df[att_col] < 75).sum())
        kpis[f"Low Attendance ({low_att} students)"] = round(low_att/len(df)*100, 1)
        d = pd.DataFrame({"Category": ["≥75% Regular", "<75% Low"], "Students": [int((df[att_col] >= 75).sum()), int((df[att_col] < 75).sum())]})
        charts["attendance_split"] = {"type": "pie", "data": d.to_dict("records"), "names": "Category", "values": "Students", "title": "Attendance Split"}

    if cgpa_col:
        kpis["Avg CGPA"]     = round(float(df[cgpa_col].mean()), 2)
        kpis["Highest CGPA"] = round(float(df[cgpa_col].max()), 2)

    if fee_col:
        kpis["Total Fees Collected"] = round(float(df[fee_col].sum()), 0)
        kpis["Avg Fee/Student"]      = round(float(df[fee_col].mean()), 0)

    if place_col:
        placed = df[place_col].str.lower().isin(["placed", "yes", "1", "true"])
        kpis["Placement Rate"] = round(placed.mean() * 100, 1)
        kpis["Placed Students"] = int(placed.sum())
        pv = df[place_col].value_counts()
        charts["placement"] = {"type": "pie", "data": pv.reset_index().rename(columns={place_col: "Status", "count": "Students"}).to_dict("records"), "names": "Status", "values": "Students", "title": "Placement Status"}

    if pkg_col:
        placed_pkg = df[df[pkg_col] > 0][pkg_col] if pkg_col else None
        if placed_pkg is not None and len(placed_pkg) > 0:
            kpis["Avg Package (LPA)"] = round(float(placed_pkg.mean()), 2)

    if backlog_col:
        kpis["Students with Backlogs"] = int((df[backlog_col] > 0).sum())
        kpis["Backlog %"]              = round((df[backlog_col] > 0).mean() * 100, 1)

    if scholar_col:
        kpis["Scholarship %"] = round((df[scholar_col].str.lower() == "yes").mean() * 100, 1)

    if intern_col:
        kpis["Internship %"] = round((df[intern_col].str.lower() == "yes").mean() * 100, 1)

    if dept_col:
        de = df[dept_col].value_counts()
        charts["dept_enrollment"] = {"type": "bar_h", "data": de.reset_index().rename(columns={dept_col: "Department", "count": "Students"}).to_dict("records"), "x": "Students", "y": "Department", "title": "Enrollment by Department"}
        if cgpa_col:
            dc = df.groupby(dept_col)[cgpa_col].mean().sort_values(ascending=False).reset_index()
            dc.columns = ["Department", "Avg_CGPA"]
            charts["dept_cgpa"] = {"type": "bar_h", "data": dc.to_dict("records"), "x": "Avg_CGPA", "y": "Department", "title": "Avg CGPA by Department"}
        if place_col:
            dp = df.groupby(dept_col)[place_col].apply(lambda x: (x.str.lower() == "placed").mean() * 100).sort_values(ascending=False).reset_index()
            dp.columns = ["Department", "Placement_%"]
            charts["dept_placement"] = {"type": "bar_h", "data": dp.to_dict("records"), "x": "Placement_%", "y": "Department", "title": "Placement % by Department"}

    if company_col:
        cv = df[company_col].dropna().value_counts().head(8).reset_index()
        cv.columns = ["Company", "Placements"]
        charts["companies"] = {"type": "bar_h", "data": cv.to_dict("records"), "x": "Placements", "y": "Company", "title": "Top Recruiting Companies"}

    if gender_col:
        gv = df[gender_col].value_counts()
        charts["gender"] = {"type": "pie", "data": gv.reset_index().rename(columns={gender_col: "Gender", "count": "Students"}).to_dict("records"), "names": "Gender", "values": "Students", "title": "Gender Split"}

    if city_col:
        cv = df[city_col].value_counts().head(8)
        charts["city"] = {"type": "bar_h", "data": cv.reset_index().rename(columns={city_col: "City", "count": "Students"}).to_dict("records"), "x": "Students", "y": "City", "title": "Students by City"}

    if year_col:
        yv = df[year_col].value_counts()
        charts["year"] = {"type": "pie", "data": yv.reset_index().rename(columns={year_col: "Year", "count": "Students"}).to_dict("records"), "names": "Year", "values": "Students", "title": "Year-wise Students"}

    # Trend by Admission Year
    yr_col = fc("Admission_Year", "Year", "Batch")
    if yr_col:
        try:
            yv = df[yr_col].value_counts().sort_index().reset_index()
            yv.columns = ["Year", "Students"]
            charts["yearly_trend"] = {"type": "line", "data": yv.to_dict("records"), "x": "Year", "y": "Students", "title": "Students by Admission Year"}
        except: pass

    # Bivariate: CGPA vs Attendance
    if cgpa_col and att_col:
        charts["cgpa_vs_att"] = {"type": "scatter", "df_x": att_col, "df_y": cgpa_col, "color": dept_col, "title": "Attendance vs CGPA"}

    # Insights
    at  = kpis.get("Avg Attendance %", 0)
    la  = 0
    pr  = kpis.get("Placement Rate", 0)
    bg  = kpis.get("Backlog %", 0)
    tf  = kpis.get("Total Fees Collected", 0)

    insights.append(("info", f"🎓 **{kpis['Total Students']:,} students** | Total Fees: **₹{tf/1e7:.2f}Cr** | Avg CGPA: **{kpis.get('Avg CGPA', 0):.2f}**"))
    at = kpis.get("Avg Attendance %", 0)
    la = int((df[att_col] < 75).sum()) if att_col else 0
    if at: insights.append(("warn" if at < 75 else "good", f"{'⚠️' if at<75 else '✅'} Avg Attendance: **{at:.1f}%** | **{la} students** below 75% {'— Action needed!' if at<75 else '— Good'}"))
    if pr: insights.append(("good" if pr > 60 else "warn" if pr > 30 else "danger", f"{'✅' if pr>60 else '⚠️' if pr>30 else '🔴'} Placement Rate: **{pr:.1f}%** ({kpis.get('Placed Students', 0)} students) {'— Good!' if pr>60 else '— Needs industry partnerships' if pr>30 else '— Very low!'}"))
    if kpis.get("Avg Package (LPA)"): insights.append(("info", f"💼 Avg Package: **₹{kpis['Avg Package (LPA)']:.2f} LPA**"))
    if bg: insights.append(("warn" if bg > 40 else "info", f"{'⚠️' if bg>40 else 'ℹ️'} Students with Backlogs: **{bg:.1f}%** {'— High! Extra coaching needed' if bg>40 else ''}"))
    if kpis.get("Internship %"): insights.append(("good" if kpis["Internship %"] > 50 else "warn", f"{'✅' if kpis['Internship %']>50 else '⚠️'} Internship Rate: **{kpis['Internship %']:.1f}%**"))

    return kpis, charts, insights

def process_generic(df):
    kpis = {}; charts = {}; insights = []
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    cat_cols  = [c for c in df.columns if df[c].dtype == object and 2 <= df[c].nunique() <= 50]
    date_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]

    kpis["Total Records"] = len(df)
    for col in num_cols[:4]:
        kpis[f"Total {col}"] = round(float(df[col].sum()), 2)
    for col in cat_cols[:4]:
        vc = df[col].value_counts()
        d  = vc.reset_index(); d.columns = [col, "Count"]
        charts[f"cat_{col}"] = {"type": "pie" if len(vc) <= 7 else "bar_h", "data": d.to_dict("records"), "names": col, "values": "Count", "x": "Count", "y": col, "title": f"{col} Distribution"}
    for dc in date_cols[:1]:
        df["_month"] = df[dc].dt.to_period("M").astype(str)
        mt = df.groupby("_month").size().reset_index(name="Count")
        mt.columns = ["Month", "Count"]
        charts["trend"] = {"type": "line", "data": mt.to_dict("records"), "x": "Month", "y": "Count", "title": "Monthly Trend"}
    insights.append(("info", f"📊 **{len(df):,} records** analyzed across **{len(df.columns)} columns**"))
    for col in num_cols[:3]:
        insights.append(("info", f"💡 **{col}**: Total={df[col].sum():,.1f} | Avg={df[col].mean():,.1f} | Max={df[col].max():,.1f}"))
    return kpis, charts, insights

# ══════════════════════════════════════════════════════════════════
# CHART RENDERER
# ══════════════════════════════════════════════════════════════════