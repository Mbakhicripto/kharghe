import os
import uuid
import datetime as dt

import pandas as pd
import streamlit as st

try:
    import jdatetime  # For Jalali (Shamsi) dates
except Exception as e:
    jdatetime = None

APP_TITLE = "دفترچه خرج روزانه (شمسی) — Streamlit"
DATA_FILE = "expenses.csv"

st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)
st.caption("ساده، سریع، آفلاین — تاریخ‌ها به شمسی ذخیره و نمایش داده می‌شوند.")

# ---------------------- Helpers ----------------------

def ensure_jdatetime():
    if jdatetime is None:
        st.error(
            "کتابخانه jdatetime نصب نیست. برای پشتیبانی تاریخ شمسی این دستور را اجرا کنید:\n\n"
            "`pip install jdatetime`"
        )
        st.stop()


def jalali_today_str() -> str:
    ensure_jdatetime()
    return jdatetime.date.today().strftime("%Y-%m-%d")


def jalali_to_gregorian(jalali_str: str) -> dt.date:
    """Convert 'YYYY-MM-DD' Jalali string to Gregorian date object."""
    ensure_jdatetime()
    try:
        jdate = jdatetime.date.fromisoformat(jalali_str)
        gdate = jdate.togregorian()
        return gdate
    except Exception as e:
        raise ValueError("فرمت تاریخ نامعتبر است. مثال: 1403-05-25") from e


def gregorian_to_jalali(gdate: dt.date) -> str:
    ensure_jdatetime()
    jdate = jdatetime.date.fromgregorian(date=gdate)
    return jdate.strftime("%Y-%m-%d")


def read_data() -> pd.DataFrame:
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE, encoding="utf-8")
        # Ensure expected columns exist (handle older files)
        expected = [
            "id",
            "date_jalali",
            "date_gregorian",
            "amount",
            "description",
            "card",
        ]
        for col in expected:
            if col not in df.columns:
                df[col] = None
        # Types
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
        return df[expected]
    else:
        return pd.DataFrame(
            columns=[
                "id",
                "date_jalali",
                "date_gregorian",
                "amount",
                "description",
                "card",
            ]
        )


def write_data(df: pd.DataFrame):
    df.to_csv(DATA_FILE, index=False, encoding="utf-8")


# ---------------------- Load state ----------------------
if "df" not in st.session_state:
    st.session_state.df = read_data()


df = st.session_state.df

# ---------------------- Sidebar: Add expense ----------------------
st.sidebar.header("افزودن خرج جدید")

with st.sidebar.form("add_expense_form", clear_on_submit=True):
    date_jalali = st.text_input(
        "تاریخ (شمسی)",
        value=jalali_today_str() if jdatetime else "",
        help="به صورت YYYY-MM-DD وارد کنید. مثال: 1403-05-25",
    )
    amount = st.number_input(
        "مبلغ (تومان)", min_value=0, step=1000, format="%d",
        help="مبلغ را به تومان وارد کنید"
    )
    description = st.text_input("چه چیزی خریدی؟", placeholder="مثلاً: خرید میوه")
    card = st.text_input("با کدام کارت؟", placeholder="مثلاً: ملت / سامان / نقدی")

    submitted = st.form_submit_button("ثبت خرج")

    if submitted:
        try:
            if not date_jalali:
                st.warning("لطفاً تاریخ شمسی را وارد کنید.")
                st.stop()
            if amount <= 0:
                st.warning("مبلغ باید بیشتر از صفر باشد.")
                st.stop()

            gdate = jalali_to_gregorian(date_jalali)
            new_row = {
                "id": str(uuid.uuid4()),
                "date_jalali": date_jalali,
                "date_gregorian": gdate.isoformat(),
                "amount": int(amount),
                "description": description.strip(),
                "card": card.strip(),
            }
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)
            write_data(st.session_state.df)
            st.success("خرج با موفقیت ثبت شد ✨")
        except Exception as e:
            st.error(f"خطا در ثبت: {e}")

# ---------------------- Filters ----------------------
st.subheader("فیلترها")
col_f1, col_f2, col_f3, col_f4 = st.columns([1.2, 1.2, 1, 1])
with col_f1:
    start_j = st.text_input("از تاریخ (شمسی)", value="")
with col_f2:
    end_j = st.text_input("تا تاریخ (شمسی)", value="")
with col_f3:
    card_filter = st.text_input("فیلتر کارت", value="")
with col_f4:
    search = st.text_input("جستجو در توضیحات", value="")

filtered = df.copy()

# Date filtering
try:
    if start_j:
        start_g = jalali_to_gregorian(start_j)
        filtered = filtered[filtered["date_gregorian"] >= start_g.isoformat()]
    if end_j:
        end_g = jalali_to_gregorian(end_j)
        filtered = filtered[filtered["date_gregorian"] <= end_g.isoformat()]
except Exception as e:
    st.warning(f"فیلتر تاریخ اعمال نشد: {e}")

# Card filter
if card_filter:
    filtered = filtered[filtered["card"].fillna("").str.contains(card_filter, case=False, na=False)]

# Search in description
if search:
    filtered = filtered[filtered["description"].fillna("").str.contains(search, case=False, na=False)]

# Sort by date desc
if not filtered.empty:
    filtered = filtered.sort_values("date_gregorian", ascending=False)

# ---------------------- KPIs ----------------------
st.subheader("خلاصه")

total_spent = int(filtered["amount"].sum() if not filtered.empty else 0)

k1, k2, k3 = st.columns(3)
with k1:
    st.metric("مجموع خرج (فیلترشده)", f"{total_spent:,.0f} تومان")
with k2:
    if not filtered.empty:
        day_count = filtered["date_gregorian"].nunique()
    else:
        day_count = 0
    st.metric("تعداد روزهای هزینه‌دار", f"{day_count}")
with k3:
    if not filtered.empty:
        avg = int(filtered["amount"].mean())
    else:
        avg = 0
    st.metric("میانگین هر خرج", f"{avg:,.0f} تومان")

# Per-card aggregation
if not filtered.empty:
    st.write("**مجموع خرج بر اساس کارت:**")
    card_summary = (
        filtered.groupby(filtered["card"].replace('', '— مشخص نشده —'))["amount"].sum().reset_index().rename(columns={"card": "کارت", "amount": "مجموع (تومان)"})
    )
    st.dataframe(card_summary, use_container_width=True)

# ---------------------- Table ----------------------
st.subheader("لیست هزینه‌ها")
show_cols = ["date_jalali", "amount", "description", "card"]
renamed = {
    "date_jalali": "تاریخ (شمسی)",
    "amount": "مبلغ (تومان)",
    "description": "توضیحات",
    "card": "کارت",
}

st.dataframe(filtered[show_cols].rename(columns=renamed), use_container_width=True, height=420)

# ---------------------- Export / Import ----------------------
col_e1, col_e2, col_e3 = st.columns([1, 1, 1])
with col_e1:
    if not df.empty:
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="دانلود همه هزینه‌ها (CSV)",
            data=csv_bytes,
            file_name="expenses.csv",
            mime="text/csv",
        )
with col_e2:
    uploaded = st.file_uploader("درون‌ریزی CSV", type=["csv"], help="ستون‌ها: date_jalali, amount, description, card (اختیاری)")
    if uploaded is not None:
        try:
            imp = pd.read_csv(uploaded)
            # Minimal normalization
            needed = ["date_jalali", "amount"]
            for c in needed:
                if c not in imp.columns:
                    raise ValueError(f"ستون '{c}' در فایل نیست.")
            imp["description"] = imp.get("description", "")
            imp["card"] = imp.get("card", "")
            # Convert to full schema
            records = []
            for _, r in imp.iterrows():
                g = jalali_to_gregorian(str(r["date_jalali"]))
                records.append(
                    {
                        "id": str(uuid.uuid4()),
                        "date_jalali": str(r["date_jalali"]),
                        "date_gregorian": g.isoformat(),
                        "amount": int(pd.to_numeric(r["amount"], errors="coerce") or 0),
                        "description": str(r.get("description", "")),
                        "card": str(r.get("card", "")),
                    }
                )
            merged = pd.concat([df, pd.DataFrame(records)], ignore_index=True)
            st.session_state.df = merged
            write_data(merged)
            st.success("درون‌ریزی با موفقیت انجام شد ✅")
        except Exception as e:
            st.error(f"مشکل در درون‌ریزی: {e}")
with col_e3:
    if st.button("🔁 بازنشانی همه داده‌ها", type="secondary"):
        st.session_state.df = pd.DataFrame(columns=df.columns)
        write_data(st.session_state.df)
        st.success("داده‌ها پاک شدند.")

st.divider()
st.caption("نکته: فایل `expenses.csv` در همان پوشهٔ برنامه ذخیره می‌شود. برای پشتیبان‌گیری از آن کپی بگیرید.")
