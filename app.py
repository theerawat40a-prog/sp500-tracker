import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# ---------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="S&P 500 Stock Tracker",
    page_icon="📈",
    layout="wide"
)

st.title("📈 S&P 500 Stock Tracker & Valuation Dashboard")
st.caption("ระบบติดตามดัชนี หุ้น S&P 500 ข่าวมหภาค งบการเงิน และเครื่องมือประเมินมูลค่าหุ้น")

# ---------------------------------------------------------
# Sidebar Navigation & Settings
# ---------------------------------------------------------
st.sidebar.header("📌 เมนูหลัก (Navigation)")
menu = st.sidebar.radio(
    "เลือกหน้าการทำงาน:",
    [
        "1. Dashboard ภาพรวมดัชนี",
        "2. รายชื่อหุ้น S&P 500",
        "3. ข่าวเศรษฐกิจมหภาค & Guide",
        "4. งบการเงินรายไตรมาส (SEC 10-Q)",
        "5. Valuation & Growth Catalyst Calc"
    ]
)

# Sample S&P 500 Top Holdings / List
DEFAULT_TICKERS = [ 
# ---------------------------------------------------------
# Helper Function: Fetch Full S&P 500 List from Wikipedia
# ---------------------------------------------------------
@st.cache_data(ttl=86400)
def get_sp500_tickers():
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    tables = pd.read_html(url)
    df = tables[0]
    
    df_clean = df[['Symbol', 'Security', 'GICS Sector', 'CIK']].copy()
    df_clean.columns = ['Symbol', 'Company', 'Sector', 'CIK']
    df_clean['CIK'] = df_clean['CIK'].astype(str).str.zfill(10)
    df_clean['Symbol'] = df_clean['Symbol'].str.replace('.', '-', regex=False)
    
    return df_clean

df_sp500_base = get_sp500_tickers()
]
df_sp500_base = pd.DataFrame(DEFAULT_TICKERS)


# ---------------------------------------------------------
# Helper Function: Cache yfinance Data
# ---------------------------------------------------------
@st.cache_data(ttl=300)  # Refresh every 5 minutes
def get_index_data():
    indices = {"S&P 500": "^GSPC", "Dow Jones": "^DJI", "Nasdaq": "^IXIC"}
    data = []
    for name, ticker in indices.items():
        t = yf.Ticker(ticker)
        hist = t.history(period="5d")
        if not hist.empty:
            curr = hist['Close'].iloc[-1]
            prev = hist['Close'].iloc[-2]
            change = curr - prev
            pct_change = (change / prev) * 100
            data.append({
                "Index": name,
                "Symbol": ticker,
                "Price": curr,
                "Change": change,
                "Change %": pct_change,
                "High": hist['High'].iloc[-1],
                "Low": hist['Low'].iloc[-1]
            })
    return pd.DataFrame(data)

@st.cache_data(ttl=600)
def get_stock_metrics(tickers):
    results = []
    for sym in tickers:
        try:
            t = yf.Ticker(sym)
            info = t.info
            results.append({
                "Ticker": sym,
                "Price": info.get("currentPrice", info.get("regularMarketPrice", np.nan)),
                "Change %": info.get("regularMarketChangePercent", np.nan),
                "Market Cap ($B)": round(info.get("marketCap", 0) / 1e9, 2) if info.get("marketCap") else np.nan,
                "Volume": info.get("regularMarketVolume", np.nan),
                "P/E (TTM)": info.get("trailingPE", np.nan),
                "Forward P/E": info.get("forwardPE", np.nan),
                "P/B": info.get("priceToBook", np.nan),
                "P/S": info.get("priceToSalesTrailing12Months", np.nan),
                "EV/EBITDA": info.get("enterpriseToEbitda", np.nan),
                "Dividend Yield %": round(info.get("dividendYield", 0) * 100, 2) if info.get("dividendYield") else 0.0,
            })
        except Exception:
            results.append({"Ticker": sym})
    return pd.DataFrame(results)


# =========================================================
# PAGE 1: DASHBOARD
# =========================================================
if menu == "1. Dashboard ภาพรวมดัชนี":
    st.header("📊 S&P 500 & Major Market Indices")
    st.write("ข้อมูลดัชนีหลักและบริบทตลาดอัปเดตแบบ Real-time / Delayed")
    
    with st.spinner("กำลังโหลดข้อมูลดัชนี..."):
        df_idx = get_index_data()
    
    if not df_idx.empty:
        # Metrics Row
        col1, col2, col3 = st.columns(3)
        for idx, row in df_idx.iterrows():
            target_col = [col1, col2, col3][idx % 3]
            target_col.metric(
                label=f"{row['Index']} ({row['Symbol']})",
                value=f"{row['Price']:,.2f}",
                delta=f"{row['Change']:+.2f} ({row['Change %']:+.2f}%)"
            )
        
        st.subheader("ตารางเปรียบเทียบดัชนี")
        st.dataframe(df_idx.style.format({
            "Price": "{:,.2f}",
            "Change": "{:+.2f}",
            "Change %": "{:+.2f}%",
            "High": "{:,.2f}",
            "Low": "{:,.2f}"
        }), use_container_width=True)

    # S&P 500 Historical Chart
    st.subheader("📈 แนวโน้มดัชนี S&P 500 (^GSPC)")
    period = st.selectbox("เลือกช่วงเวลา:", ["1mo", "3mo", "6mo", "1y", "5y"], index=3)
    sp_hist = yf.Ticker("^GSPC").history(period=period)
    st.line_chart(sp_hist['Close'])


# =========================================================
# PAGE 2: STOCK LIST & SCREENER
# =========================================================
elif menu == "2. รายชื่อหุ้น S&P 500":
    st.header("📋 รายชื่อหุ้นและคัดกรองหุ้น S&P 500")
    
    # Filter Controls
    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        selected_sector = st.selectbox(
            "Filter ตาม GICS Sector:",
            ["ทั้งหมด"] + list(df_sp500_base['Sector'].unique())
        )
    with col_f2:
        search_symbol = st.text_input("ค้นหา Ticker หรือชื่อบริษัท:", "").upper()
    
    filtered_df = df_sp500_base.copy()
    if selected_sector != "ทั้งหมด":
        filtered_df = filtered_df[filtered_df['Sector'] == selected_sector]
    if search_symbol:
        filtered_df = filtered_df[
            filtered_df['Symbol'].str.contains(search_symbol) | 
            filtered_df['Company'].str.contains(search_symbol, case=False)
        ]
    
    if st.button("🔄 โหลด/อัปเดตราคาหุ้นสด"):
        with st.spinner("กำลังดึงราคาหุ้นสดจาก yfinance..."):
            stock_data = get_stock_metrics(filtered_df['Symbol'].tolist())
            merged_df = pd.merge(filtered_df, stock_data, on="Ticker" if "Ticker" in filtered_df else "Symbol")
            st.session_state['stock_table'] = merged_df

    if 'stock_table' in st.session_state:
        df_show = st.session_state['stock_table']
    else:
        df_show = filtered_df

    st.write(f"แสดงรายการทั้งหมด: **{len(df_show)}** รายการ")
    st.dataframe(df_show, use_container_width=True)


# =========================================================
# PAGE 3: MACRO NEWS & BOND YIELD GUIDE
# =========================================================
elif menu == "3. ข่าวเศรษฐกิจมหภาค & Guide":
    st.header("🌍 Macro Economy Tracker & Impact Guide")
    st.write("ติดตามตัวชี้วัดเศรษฐกิจมหภาคและไกด์ไลน์ผลกระทบต่อกลุ่มหุ้น")
    
    # Static Guide Table
    st.subheader("💡 Guide: ผลกระทบของตัวชี้วัดมหภาคต่อกลุ่มหุ้น")
    guide_data = [
        {
            "ตัวชี้วัดมหภาค": "US 10-Year Treasury Yield",
            "แนวโน้ม": "ขาขึ้น (> 4.5%)",
            "กลุ่มที่ได้ผลบวก (+)": "Financials, Insurance (NIM กว้างขึ้น)",
            "กลุ่มที่ได้ผลลบ (-)": "Utilities, REITs, High-Debt Growth Tech",
            "เหตุผลเชิงวิเคราะห์": "ยีลด์บอนด์สูงขึ้น เพิ่มต้นทุนการกู้ยืม และกดดัน Valuation แบบ DCF ของหุ้นเติบโต"
        },
        {
            "ตัวชี้วัดมหภาค": "US 30-Year Treasury Yield",
            "แนวโน้ม": "ขาขึ้น",
            "กลุ่มที่ได้ผลบวก (+)": "Financials (Spread กว้างขึ้น)",
            "กลุ่มที่ได้ผลลบ (-)": "Homebuilders, Real Estate",
            "เหตุผลเชิงวิเคราะห์": "ยีลด์ยาวสูงขึ้นทำให้อัตราดอกเบี้ยจำนองบ้านแพงขึ้น กระทบยอดขายบ้าน"
        },
        {
            "ตัวชี้วัดมหภาค": "Fed Funds Rate",
            "แนวโน้ม": "Higher for Longer (คงที่ระดับสูง)",
            "กลุ่มที่ได้ผลบวก (+)": "Money Market, Banks",
            "กลุ่มที่ได้ผลลบ (-)": "Consumer Discretionary, Small-Cap",
            "เหตุผลเชิงวิเคราะห์": "กำลังซื้อผู้บริโภคชะลอตัว และบริษัทขนาดเล็กมีต้นทุนรีไฟแนนซ์หนี้สูงขึ้น"
        },
        {
            "ตัวชี้วัดมหภาค": "ราคาน้ำมันดิบ (WTI/Brent)",
            "แนวโน้ม": "ขาขึ้น",
            "กลุ่มที่ได้ผลบวก (+)": "Energy (Upstream E&P, Oilfield)",
            "กลุ่มที่ได้ผลลบ (-)": "Airlines, Transportation, Packaging",
            "เหตุผลเชิงวิเคราะห์": "ต้นทุนเชื้อเพลิงแพงขึ้นกระทบอัตรากำไรของกลุ่มขนส่งและสายการบิน"
        }
    ]
    st.table(pd.DataFrame(guide_data))
    
    # Real-time Bond Yields Fetcher
    st.subheader("📊 ดึงตัวชี้วัดบอนด์ยิลด์ปัจจุบัน")
    if st.button("ดึงข้อมูล บอนด์ยิลด์สด"):
        try:
            tnx = yf.Ticker("^TNX").history(period="1d")['Close'].iloc[-1]
            tyx = yf.Ticker("^TYX").history(period="1d")['Close'].iloc[-1]
            
            c1, c2 = st.columns(2)
            c1.metric("US 10-Year Treasury Yield (^TNX)", f"{tnx:.3f}%")
            c2.metric("US 30-Year Treasury Yield (^TYX)", f"{tyx:.3f}%")
        except Exception as e:
            st.error("ไม่สามารถดึงข้อมูลยิลด์ได้ในขณะนี้")


# =========================================================
# PAGE 4: FINANCIAL STATEMENTS & SEC FILINGS
# =========================================================
elif menu == "4. งบการเงินรายไตรมาส (SEC 10-Q)":
    st.header("📄 อัปเดตงบการเงินรายไตรมาส & ลิงก์ดาวน์โหลด 10-Q")
    st.write("เลือกรหัสหุ้นเพื่อเข้าถึงหน้าลิงก์ดาวน์โหลดเอกสาร 10-Q / 10-K จาก SEC EDGAR โดยตรง")
    
    selected_sym = st.selectbox("เลือกหุ้นที่ต้องการดูงบ:", df_sp500_base['Symbol'].tolist())
    company_info = df_sp500_base[df_sp500_base['Symbol'] == selected_sym].iloc[0]
    
    st.subheader(f"📌 {company_info['Company']} ({selected_sym})")
    cik = company_info['CIK']
    
    # Direct SEC EDGAR Links
    sec_url = f"https://www.sec.gov/edgar/browse/?CIK={cik}"
    st.markdown(f"🔗 **[เปิดหน้า SEC EDGAR Filings ทั้งหมดของ {selected_sym}]({sec_url})**")
    
    # Fetch Financials via yfinance
    if st.button("ดึงงบการเงินรายไตรมาสล่าสุด"):
        with st.spinner("กำลังดึงงบการเงิน..."):
            t = yf.Ticker(selected_sym)
            q_stmt = t.quarterly_financials
            if not q_stmt.empty:
                st.subheader("ตารางงบกำไรขาดทุนรายไตรมาส ($)")
                st.dataframe(q_stmt, use_container_width=True)
            else:
                st.warning("ไม่พบข้อมูลทางการเงินแบบสรุป")


# =========================================================
# PAGE 5: VALUATION & GROWTH CATALYST CALCULATOR
# =========================================================
elif menu == "5. Valuation & Growth Catalyst Calc":
    st.header("🎯 เครื่องมือประเมินมูลค่าหุ้นถูก/แพง (Valuation Screener)")
    
    tab1, tab2 = st.tabs(["A) Relative Valuation (หุ้นถูก/แพง)", "B) Project-based Valuation (Growth Catalyst)"])
    
    # TAB 1: RELATIVE VALUATION
    with tab1:
        st.subheader("คำนวณอัตราส่วนการเงินเปรียบเทียบกับ Sector")
        symbol_val = st.selectbox("เลือกหุ้นประเมินราคา:", df_sp500_base['Symbol'].tolist(), key="val_sym")
        
        if st.button("ประเมินอัตราส่วนทางการเงิน"):
            t = yf.Ticker(symbol_val)
            info = t.info
            
            pe_ttm = info.get("trailingPE", None)
            fwd_pe = info.get("forwardPE", None)
            pb = info.get("priceToBook", None)
            
            st.write(f"**ราคาปัจจุบัน:** ${info.get('currentPrice', 'N/A')}")
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("P/E (TTM)", f"{pe_ttm:.2f}" if pe_ttm else "N/A")
            col_b.metric("Forward P/E", f"{fwd_pe:.2f}" if fwd_pe else "N/A")
            col_c.metric("P/B Ratio", f"{pb:.2f}" if pb else "N/A")
            
            # Simple Assessment Logic
            if pe_ttm:
                if pe_ttm < 15:
                    st.success("🟢 **การประเมินเบื้องต้น:** P/E ต่ำกว่า 15 เท่า (หุ้นน่าจะมีราคาถูก/Value Stock)")
                elif pe_ttm > 35:
                    st.warning("🟡 **การประเมินเบื้องต้น:** P/E สูงกว่า 35 เท่า (เป็นหุ้น Growth หรือราคาสูงกว่าปกติ)")
                else:
                    st.info("🔵 **การประเมินเบื้องต้น:** P/E อยู่ในระดับปานกลาง (15 - 35 เท่า)")

    # TAB 2: GROWTH CATALYST CALCULATOR
    with tab2:
        st.subheader("💡 เครื่องคำนวณมูลค่าเพิ่มจากโปรเจกต์ใหม่ (Growth Catalyst -> Implied Fair Value)")
        st.write("คำนวณราคาที่ควรจะเป็นเมื่อบริษัทประกาศทำโปรเจกต์ใหม่")
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            project_name = st.text_input("ชื่อโปรเจกต์ / แผนธุรกิจ:", "ตัวอย่าง: ขยายศูนย์ข้อมูล AI เพิ่มรายได้")
            curr_mkt_cap = st.number_input("มูลค่าตลาดปัจจุบัน ($B):", value=3000.0, step=10.0)
            proj_val = st.number_input("มูลค่าเพิ่มที่คาดจากโปรเจกต์ ($B):", value=200.0, step=10.0)
        
        with col_c2:
            prob = st.slider("ความน่าจะเป็นที่โปรเจกต์จะสำเร็จ (%):", min_value=0, max_value=100, value=60) / 100.0
            weighted_val = proj_val * prob
            implied_fair = curr_mkt_cap + weighted_val
            upside_pct = (weighted_val / curr_mkt_cap) * 100
        
        st.divider()
        st.markdown("### 📊 ผลลัพธ์การคำนวณ")
        res_c1, res_c2, res_c3 = st.columns(3)
        res_c1.metric("มูลค่าเพิ่มถ่วงน้ำหนัก ($B)", f"${weighted_val:,.2f} B")
        res_c2.metric("Implied Fair Market Cap ($B)", f"${implied_fair:,.2f} B")
        res_c3.metric("Upside / Downside (%)", f"{upside_pct:+.2f}%")
