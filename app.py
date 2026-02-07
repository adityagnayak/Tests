import streamlit as st
import pandas as pd

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Retirement Engine v9.0",
    page_icon="📈",
    layout="wide"
)

# --- CLASS DEFINITION ---
class RetirementPlanner:
    def __init__(self, inputs):
        self.inputs = inputs
        self.lump_sum = inputs['lump_sum']
        self.horizon_months = int(inputs['horizon_years'] * 12)
        
    def calculate_viability(self, crash_rate=0.0, crash_years=0):
        balance = self.lump_sum
        current_div = self.inputs['current_dividends']
        current_expense = self.inputs['target_payout']
        
        data = []
        is_solvent = True
        insolvency_msg = "Solvent"
        
        for m in range(1, self.horizon_months + 1):
            year = (m - 1) // 12 + 1
            
            # Crash Logic
            if year <= crash_years:
                monthly_rate = crash_rate / 12
            else:
                monthly_rate = self.inputs['expected_return'] / 12

            # Inflation Adjustments
            if m > 1 and (m - 1) % 12 == 0:
                current_div *= (1 + self.inputs['gdp_growth'])
                current_expense *= (1 + self.inputs['inflation_rate'])

            # Core Logic
            balance += (balance * monthly_rate) # Interest
            total_income = self.inputs['other_income'] + current_div
            net_shortfall = max(0, current_expense - total_income)
            gross_withdrawal = net_shortfall / (1 - self.inputs['tax_rate']) # Tax Drag
            balance -= gross_withdrawal
            
            if balance <= 0 and is_solvent:
                is_solvent = False
                insolvency_msg = f"DEPLETED (Year {year})"
                balance = 0 

            if m % 12 == 0 or m == self.horizon_months:
                data.append({
                    "Year": year,
                    "Expenses (Net)": current_expense,
                    "Withdrawal (Gross)": gross_withdrawal,
                    "Balance": balance
                })

        return pd.DataFrame(data), is_solvent, insolvency_msg

    def solve_required_capital(self, crash_rate=0, crash_years=0):
        original_balance = self.lump_sum
        low = self.lump_sum
        high = self.lump_sum * 10
        
        for _ in range(30):
            mid = (low + high) / 2
            self.lump_sum = mid
            _, solvent, _ = self.calculate_viability(crash_rate, crash_years)
            if solvent: high = mid
            else: low = mid
            
        required = high
        self.lump_sum = original_balance
        return required

    def calculate_swr_health(self):
        initial_gap = self.inputs['target_payout'] - (self.inputs['other_income'] + self.inputs['current_dividends'])
        if initial_gap <= 0: return 0.0, "SECURE"
        
        gross_annual = (initial_gap * 12) / (1 - self.inputs['tax_rate'])
        if self.lump_sum <= 0: return 0.0, "CRITICAL"
        
        rate = gross_annual / self.lump_sum
        if rate <= 0.035: return rate, "EXCELLENT (< 3.5%)"
        elif rate <= 0.045: return rate, "GOOD (Industry Std)"
        elif rate <= 0.06: return rate, "RISKY (High Risk)"
        else: return rate, "DANGER (> 6.0%)"

# --- SIDEBAR: INPUTS ---
st.sidebar.header("📝 Financial Inputs")

# Group 1: Assets
with st.sidebar.expander("Assets & Income", expanded=True):
    lump_sum = st.number_input("Total Capital ($)", value=500000, step=10000)
    other_inc = st.number_input("Fixed Income ($/mo)", value=1500, step=100)
    curr_div = st.number_input("Dividend Income ($/mo)", value=500, step=50)

# Group 2: Goals
with st.sidebar.expander("Expenses & Taxes", expanded=True):
    target_payout = st.number_input("Target Spend ($/mo)", value=4000, step=100)
    tax_rate = st.slider("Tax Rate (%)", 0, 50, 15) / 100
    horizon = st.slider("Horizon (Years)", 10, 50, 25)

# Group 3: Market
with st.sidebar.expander("Market Assumptions", expanded=False):
    inflation = st.slider("Inflation Rate (%)", 0.0, 10.0, 2.5) / 100
    gdp = st.slider("Div Growth Rate (%)", 0.0, 10.0, 3.0) / 100

# --- MAIN PAGE: PORTFOLIO ARCHITECT ---
st.title("Retirement Engine v9.0")
st.markdown("### 🏛️ Portfolio Architect")

col1, col2 = st.columns(2)

with col1:
    strategy = st.selectbox("Select Strategy", ["Aggressive Growth", "Conservative Income", "Custom Allocation"])

est_return = 0.07

if strategy == "Aggressive Growth":
    alloc = {'Equity': 60, 'Metals': 20, 'Debt': 10, 'Cash': 10}
    est_return = 0.08
elif strategy == "Conservative Income":
    alloc = {'Equity': 20, 'Metals': 10, 'Debt': 40, 'Cash': 30}
    est_return = 0.05
else:
    st.info("Define Custom Mix (Must sum to 100)")
    c1, c2, c3, c4 = st.columns(4)
    e = c1.number_input("Equity %", 0, 100, 50)
    m = c2.number_input("Metals %", 0, 100, 10)
    d = c3.number_input("Debt %", 0, 100, 30)
    c = c4.number_input("Cash %", 0, 100, 10)
    alloc = {'Equity': e, 'Metals': m, 'Debt': d, 'Cash': c}
    # Simple weighted calc
    est_return = (e*0.09 + m*0.04 + d*0.04 + c*0.02) / 100

with col2:
    st.write(f"**Target Allocation:** {alloc}")
    final_return = st.number_input(f"Expected Return (Hist: {est_return*100:.1f}%)", value=est_return)

# --- RUN SIMULATION ---
inputs = {
    'lump_sum': lump_sum, 'other_income': other_inc, 'current_dividends': curr_div,
    'target_payout': target_payout, 'tax_rate': tax_rate, 'horizon_years': horizon,
    'inflation_rate': inflation, 'gdp_growth': gdp, 'expected_return': final_return
}

planner = RetirementPlanner(inputs)
df_base, solv_base, msg_base = planner.calculate_viability()
swr, swr_status = planner.calculate_swr_health()

# --- DASHBOARD RESULTS ---
st.markdown("---")
m1, m2, m3 = st.columns(3)
m1.metric("Initial Withdrawal Rate", f"{swr*100:.2f}%", swr_status)
m2.metric("Base Scenario Result", msg_base, delta_color="normal" if solv_base else "inverse")

if not solv_base:
    req = planner.solve_required_capital()
    m3.metric("Required Capital", f"${req:,.0f}", f"+${req-lump_sum:,.0f} needed")
else:
    m3.metric("Ending Balance", f"${df_base.iloc[-1]['Balance']:,.0f}")

# Charts
st.subheader("📊 Capital Trajectory (Base Case)")
st.line_chart(df_base, x="Year", y="Balance")

# --- STRESS TEST SECTION ---
st.markdown("---")
st.subheader("🌪️ Dynamic Stress Test")

with st.expander("Configure Crash Scenario", expanded=True):
    sc1, sc2 = st.columns(2)
    crash_pct = sc1.slider("Crash Magnitude (%)", -50, 0, -20) / 100
    crash_yrs = sc2.slider("Crash Duration (Years)", 0, 10, 2)
    
    if st.button("Run Stress Test"):
        df_stress, solv_stress, msg_stress = planner.calculate_viability(crash_pct, crash_yrs)
        
        st.write(f"**Outcome:** {msg_stress}")
        
        # Comparison Chart
        combined_df = pd.DataFrame({
            "Year": df_base["Year"],
            "Base Case": df_base["Balance"],
            "Stress Test": df_stress["Balance"]
        })
        st.line_chart(combined_df, x="Year", y=["Base Case", "Stress Test"])
        
        if not solv_stress:
            req_stress = planner.solve_required_capital(crash_pct, crash_yrs)
            st.error(f"🚨 To survive this crash, you need a Total Capital of **${req_stress:,.0f}**")
