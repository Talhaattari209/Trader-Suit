"""Technical Analysis (Indicator Builder) — Custom indicators with advanced math (Fourier, wavelet, etc.)."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

from src.dashboard.config import LAYOUT_SIDEBAR_MAIN, COLAB_NOTEBOOK_URL
from src.dashboard.components import apply_theme, plotly_layout
from src.dashboard.session_state import init_session_state

st.set_page_config(page_title="Technical Analysis — Trader-Suit", page_icon="📐", layout="wide")
apply_theme()
init_session_state()

# Sidebar 1:5
with st.sidebar:
    st.markdown("## 📐 Indicator Builder")
    st.selectbox("Math library", options=["NumPy/SciPy", "SymPy", "statsmodels", "PyWavelets"], key="ta_math_lib", index=0)
    st.caption("Preview: denoised EMA, Fourier filter, Hurst.")
    st.divider()
    st.multiselect("Preview techniques", options=["Normalization", "Fourier", "Wavelet", "Hurst"], default=["Normalization"], key="ta_preview")

sidebar_col, main_col = st.columns((1, 5))
with main_col:
    st.markdown("# 📐 Technical Analysis — Indicator Builder")
    st.markdown("Build custom indicators with advanced math (Fourier, wavelet, stochastic).")
    tab_build, tab_variants = st.tabs(["Build Indicator", "Variants"])

    with tab_build:
        builder_col, chart_col = st.columns([2, 1])
        with builder_col:
            st.markdown("#### Specs / Formula")
            specs_formula = st.text_area(
                "Indicator Specs/Formula",
                value="EMA variant with wavelet denoising via scipy",
                height=100,
                key="ta_specs",
                placeholder="e.g. EMA variant with wavelet denoising via scipy",
            )
            base_indicator = st.selectbox(
                "Base Indicator",
                options=["SMA", "EMA", "RSI", "MACD", "Bollinger", "ATR", "Stochastic", "ADX", "CCI", "OBV"] + [f"Custom_{i}" for i in range(10)],
                key="ta_base",
                index=1,
            )
            st.multiselect(
                "Advanced Math Techniques",
                options=["Normalization", "Fourier Transform", "Pooling", "Hurst Exponent", "Wavelet Denoise", "SVD"],
                default=["Normalization"],
                key="ta_techniques",
            )
            period = st.slider("Period", 5, 50, 20, key="ta_period")
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                generate_variant = st.button("Generate Variant Code")
            with col_btn2:
                test_on_data = st.button("Test on Data")
            with st.expander("Code Description (auto-gen)"):
                st.markdown("This computes denoised EMA using wavelet decomposition; period and threshold can be tuned.")
            st.checkbox("Auto-Optimize Params (via PuLP)", value=False, key="ta_auto_optim")
            st.file_uploader("Upload Math Docs (PDF/DOCX)", type=["pdf", "docx"], key="ta_upload", label_visibility="collapsed")
            if st.button("Trigger Colab for Compute"):
                st.info("Heavy math (e.g. pyscf) runs on Colab.")
                st.link_button("Open Colab", url=COLAB_NOTEBOOK_URL, type="secondary")
            progress_ta = st.progress(0.0)
            if generate_variant or test_on_data:
                progress_ta.progress(1.0)
            progress_ta.empty()
            st.markdown("**Generated Code Snippet**")
            st.code(
                "def denoised_ema(close, period=20):\n    from scipy.signal import welch\n    # wavelet denoise + EMA\n    return ema(close, period)",
                language="python",
            )
            st.download_button("Export Indicator Code (Python)", data="def denoised_ema(close, period=20): ...", file_name="indicator_variant.py", mime="text/plain")

        with chart_col:
            st.markdown("#### Test on US30 sample")
            n = 200
            t = np.linspace(0, 4 * np.pi, n)
            close = 35000 + np.cumsum(np.random.randn(n) * 10)
            _period = st.session_state.get("ta_period", 20)
            ema = pd.Series(close).ewm(span=_period, adjust=False).values
            fig_candle = go.Figure()
            fig_candle.add_trace(go.Scatter(x=list(range(n)), y=close, name="Close", line=dict(color="#8b949e")))
            fig_candle.add_trace(go.Scatter(x=list(range(n)), y=ema, name="EMA (denoised)", line=dict(color="#58a6ff")))
            fig_candle.update_layout(**plotly_layout(height=320), xaxis_title="Bar", yaxis_title="Price")
            st.plotly_chart(fig_candle, use_container_width=True)
            # Param sensitivity heatmap (placeholder)
            st.markdown("**Param Sensitivity**")
            sens = np.random.rand(6, 6)
            fig_heat = go.Figure(go.Heatmap(z=sens, x=[f"P{i}" for i in range(6)], y=[f"S{i}" for i in range(6)], colorscale="Blues"))
            fig_heat.update_layout(**plotly_layout(height=220))
            st.plotly_chart(fig_heat, use_container_width=True)
            # Math validation scatter
            st.markdown("**Math Validation (Fourier spectrum)**")
            freq = np.linspace(0, 1, 50)
            spec = np.exp(-freq * 2) + 0.1 * np.random.rand(50)
            fig_scatter = go.Figure(go.Scatter(x=freq, y=spec, mode="lines+markers", marker=dict(color="#3fb950")))
            fig_scatter.update_layout(**plotly_layout(height=220), xaxis_title="Freq", yaxis_title="Magnitude")
            st.plotly_chart(fig_scatter, use_container_width=True)

        # Metrics
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Signal-to-Noise Ratio", "2.4", ">2")
        with m2:
            st.metric("Lag (candles)", "3", "<5")
        with m3:
            st.metric("Correlation to Price", "0.82", None)
        with m4:
            st.metric("e-ratio", "1.6", ">1.5 edge")

        if generate_variant and "sympy" in specs_formula.lower() and "error" in specs_formula.lower():
            st.warning("Math invalid (e.g. sympy error). Check formula.")

    with tab_variants:
        st.markdown("#### Variant list")
        variants_data = [
            {"Name": "EMA_Wavelet_20", "Formula": "EMA + wavelet denoise", "Params": "period=20", "Test Metrics": "SNR 2.4"},
            {"Name": "RSI_Fourier_14", "Formula": "RSI + FFT filter", "Params": "period=14", "Test Metrics": "Lag 2"},
        ]
        df_v = pd.DataFrame(variants_data)
        st.dataframe(df_v, use_container_width=True, hide_index=True)
        if st.button("Save to Library"):
            st.success("Saved to edges/ (wire to your edges folder).")
