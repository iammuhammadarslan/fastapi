# ─────────────────────────────────────────────────────────────────────────────
# Stock Price Predictor
# Uses yfinance to pull real stock data, engineers features, trains a Linear
# Regression model, and visualizes actual vs predicted vs future prices.
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st          # Web UI framework — turns this script into a dashboard
import yfinance as yf           # Yahoo Finance API wrapper for fetching stock data
import pandas as pd             # DataFrame manipulation
import numpy as np              # Numerical operations (arrays, means, etc.)
import matplotlib.pyplot as plt # Plotting library for the price chart
from sklearn.linear_model import LinearRegression   # Our ML model
from sklearn.model_selection import train_test_split # Splits data into train/test sets
from sklearn.metrics import mean_absolute_error, r2_score  # Model evaluation metrics
from datetime import date, timedelta                # Date arithmetic for default ranges

# ── Page config ───────────────────────────────────────────────────────────────
# Must be the FIRST Streamlit call — sets browser tab title, icon, and layout.
st.set_page_config(
    page_title="Stock Price Predictor",
    page_icon="📈",
    layout="wide",   # Use full browser width instead of the narrow centered default
)

st.title("📈 Stock Price Predictor")
st.markdown("Fetch real stock data, train a regression model, and visualize predictions.")

# ── Sidebar controls ──────────────────────────────────────────────────────────
# All user inputs live in the sidebar so the main area stays clean for results.
st.sidebar.header("⚙️ Settings")

# Stock ticker symbol — uppercased and stripped so "aapl " → "AAPL"
ticker = st.sidebar.text_input("Stock Ticker", value="AAPL").upper().strip()

today = date.today()
default_start = today - timedelta(days=365 * 3)  # Default: 3 years of history

# Date range for historical data download
start_date = st.sidebar.date_input("Start Date", value=default_start)
end_date   = st.sidebar.date_input("End Date",   value=today)

# How many business days ahead to forecast after the last known date
forecast_days = st.sidebar.slider("Days to Forecast", min_value=7, max_value=90, value=30, step=1)

# Fraction of data held back for testing (e.g. 20 → 0.20)
test_size = st.sidebar.slider("Test Split (%)", min_value=10, max_value=40, value=20, step=5) / 100

# Nothing runs until the user clicks this button
run = st.sidebar.button("🚀 Run Prediction", use_container_width=True)

# ── Helper functions ──────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def fetch_data(ticker: str, start: str, end: str) -> pd.DataFrame:
    """
    Download OHLCV (Open/High/Low/Close/Volume) data from Yahoo Finance.

    @st.cache_data means Streamlit stores the result so re-running the app
    with the same inputs skips the network call entirely — much faster.
    auto_adjust=True applies corporate-action adjustments (splits, dividends).
    """
    df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
    return df


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build the feature matrix the model will train on.

    Features created:
      Day    — ordinal integer (0, 1, 2 …) capturing the overall time trend
      Lag_1  — yesterday's close price (short-term momentum signal)
      Lag_5  — close price 5 days ago (weekly momentum signal)
      MA_10  — 10-day rolling average (short-term smoothed trend)
      MA_30  — 30-day rolling average (medium-term smoothed trend)

    Why these features?
      Linear Regression needs numeric inputs. Raw dates don't work, so we
      convert them to an integer index. Lag and moving-average features give
      the model information about recent price direction without look-ahead bias.
    """
    # Keep only the Close column to avoid carrying unused OHLCV columns
    df = df[["Close"]].copy()

    # yfinance v0.2+ returns a MultiIndex (metric, ticker) — flatten it so
    # df["Close"] is a plain Series, not a one-column DataFrame.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df["Close"] = df["Close"].squeeze()

    df.dropna(inplace=True)  # Remove any NaN rows before feature creation

    # Ordinal day index — gives the model a sense of "how far along in time"
    df["Day"] = np.arange(len(df))

    # Lag features: shift the Close column forward by N days.
    # Row i gets the Close value from i-N days ago.
    df["Lag_1"] = df["Close"].shift(1)
    df["Lag_5"] = df["Close"].shift(5)

    # Rolling means: average of the last N closing prices at each row.
    # .rolling(N).mean() produces NaN for the first N-1 rows.
    df["MA_10"] = df["Close"].rolling(10).mean()
    df["MA_30"] = df["Close"].rolling(30).mean()

    # Drop rows where any feature is still NaN (the first ~30 rows)
    df.dropna(inplace=True)
    return df


def train_model(df: pd.DataFrame, test_size: float):
    """
    Split data chronologically and fit a LinearRegression model.

    Why shuffle=False?
      Stock data is time-ordered. Shuffling would let the model "see the future"
      during training (data leakage), making metrics unrealistically good.
      shuffle=False keeps the split strictly chronological: train on older data,
      test on newer data — just like real-world deployment.

    Returns the trained model, the four split arrays, and the feature column names.
    """
    feature_cols = ["Day", "Lag_1", "Lag_5", "MA_10", "MA_30"]
    X = df[feature_cols].values  # 2-D array: rows = days, cols = features
    y = df["Close"].values        # 1-D array: target closing prices

    # Chronological split — last `test_size` fraction of rows become the test set
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, shuffle=False
    )

    model = LinearRegression()
    model.fit(X_train, y_train)  # Learn the best-fit line through training data

    return model, X_train, X_test, y_train, y_test, feature_cols


def forecast_future(model, df: pd.DataFrame, forecast_days: int) -> pd.DataFrame:
    """
    Predict closing prices for the next `forecast_days` business days.

    Strategy — iterative (autoregressive) forecasting:
      1. Start from the last known row.
      2. Predict day N+1 using real historical lags/MAs.
      3. Append that prediction to the rolling windows.
      4. Predict day N+2 using the prediction from step 3 as the new lag.
      5. Repeat until all forecast days are filled.

    This avoids look-ahead bias: we never use future real prices as inputs.
    The trade-off is that errors compound — forecasts get less reliable further out.
    """
    close_col  = df["Close"].squeeze()          # Ensure plain Series
    last_close = float(close_col.iloc[-1])      # Most recent known closing price
    last_day   = int(df["Day"].iloc[-1])        # Most recent day index

    # Seed the rolling windows with the last 30 real closing prices
    recent_closes = list(close_col.values[-30:])

    predictions = []

    # pd.bdate_range generates business days only (skips weekends)
    future_dates = pd.bdate_range(
        start=df.index[-1] + timedelta(days=1),
        periods=forecast_days
    )

    lag1       = last_close                     # Will update each iteration
    lag5_window = list(close_col.values[-5:])   # Sliding 5-day window

    for i, fdate in enumerate(future_dates):
        day_idx = last_day + i + 1              # Increment the ordinal day index

        # Compute rolling means from the current window (mix of real + predicted)
        ma10 = float(np.mean(recent_closes[-10:]))
        ma30 = float(np.mean(recent_closes[-30:]))

        # Build the feature row and predict
        X_pred     = np.array([[day_idx, lag1, lag5_window[0], ma10, ma30]])
        pred_close = float(model.predict(X_pred)[0])

        predictions.append({"Date": fdate, "Predicted_Close": pred_close})

        # ── Slide all windows forward by one day ──────────────────────────────
        recent_closes.append(pred_close)        # Add new prediction to MA window
        lag5_window.append(pred_close)          # Add to 5-day lag window
        lag5_window.pop(0)                      # Drop the oldest entry (FIFO)
        lag1 = pred_close                       # New lag_1 = today's prediction

    return pd.DataFrame(predictions).set_index("Date")


# ── Main app logic ────────────────────────────────────────────────────────────
# Everything below only executes when the user clicks "Run Prediction".
# Streamlit re-runs the entire script on every interaction, so the `if run:`
# guard prevents expensive computation on every widget change.

if run:
    # Basic validation before hitting the network
    if start_date >= end_date:
        st.error("Start date must be before end date.")
        st.stop()

    with st.spinner(f"Fetching data for **{ticker}**…"):
        raw_df = fetch_data(ticker, str(start_date), str(end_date))

    # Flatten MultiIndex columns that newer yfinance versions return
    # e.g. ("Close", "AAPL") → "Close"
    if isinstance(raw_df.columns, pd.MultiIndex):
        raw_df.columns = raw_df.columns.get_level_values(0)

    if raw_df.empty:
        st.error(f"No data found for ticker **{ticker}**. Check the symbol and try again.")
        st.stop()

    # ── Summary metrics ───────────────────────────────────────────────────────
    st.subheader(f"📊 {ticker} — Historical Data")
    col1, col2, col3, col4 = st.columns(4)

    close_series = raw_df["Close"].squeeze()  # Plain Series of closing prices

    col1.metric("Latest Close", f"${float(close_series.iloc[-1]):.2f}")
    col2.metric("Period High",  f"${float(close_series.max()):.2f}")
    col3.metric("Period Low",   f"${float(close_series.min()):.2f}")
    col4.metric("Trading Days", str(len(raw_df)))

    # Collapsible raw data table — useful for sanity-checking the download
    with st.expander("Raw Data (last 10 rows)"):
        st.dataframe(raw_df.tail(10))

    # ── Feature engineering & model training ──────────────────────────────────
    df = prepare_features(raw_df)   # Build lag/MA features
    model, X_train, X_test, y_train, y_test, feature_cols = train_model(df, test_size)

    # Evaluate on the held-out test set
    y_pred_test = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred_test)  # Average dollar error
    r2  = r2_score(y_test, y_pred_test)             # 1.0 = perfect, 0 = baseline mean

    st.subheader("🤖 Model Performance")
    m1, m2, m3 = st.columns(3)
    m1.metric("R² Score",         f"{r2:.4f}")       # Closer to 1 is better
    m2.metric("MAE",              f"${mae:.2f}")     # Average prediction error in dollars
    m3.metric("Training Samples", str(len(X_train))) # How many rows the model learned from

    # ── Future forecast ───────────────────────────────────────────────────────
    # Iteratively predict the next `forecast_days` business days
    forecast_df = forecast_future(model, df, forecast_days)

    # ── Chart: Actual vs Test Predictions vs Future Forecast ──────────────────
    st.subheader("📉 Actual vs Predicted vs Forecast")

    fig, ax = plt.subplots(figsize=(14, 5))

    # Blue solid line — real historical closing prices
    ax.plot(df.index, df["Close"],
            label="Actual Close", color="#1f77b4", linewidth=1.5)

    # Orange dashed line — model's predictions on the test portion of history
    # test_dates aligns predictions back to their real calendar dates
    test_dates = df.index[len(X_train):]
    ax.plot(test_dates, y_pred_test,
            label="Test Predictions", color="#ff7f0e",
            linewidth=1.5, linestyle="--")

    # Green dash-dot line — future forecast beyond the last known date
    ax.plot(forecast_df.index, forecast_df["Predicted_Close"],
            label=f"Forecast ({forecast_days}d)", color="#2ca02c",
            linewidth=2, linestyle="-.")

    # Light green shading over the forecast region for visual clarity
    ax.axvspan(forecast_df.index[0], forecast_df.index[-1], alpha=0.08, color="#2ca02c")

    ax.set_xlabel("Date")
    ax.set_ylabel("Price (USD)")
    ax.set_title(f"{ticker} — Linear Regression Price Prediction")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    st.pyplot(fig)
    plt.close(fig)  # Free memory — important in long-running Streamlit apps

    # ── Forecast table ────────────────────────────────────────────────────────
    # Collapsible table showing the predicted price for each future business day
    with st.expander(f"📋 Forecast Table ({forecast_days} business days)"):
        display_df = forecast_df.copy()
        display_df.index   = display_df.index.strftime("%Y-%m-%d")  # Human-readable dates
        display_df.columns = ["Predicted Close (USD)"]
        display_df["Predicted Close (USD)"] = display_df["Predicted Close (USD)"].map("${:.2f}".format)
        st.dataframe(display_df, use_container_width=True)

    # ── Model coefficients ────────────────────────────────────────────────────
    # Shows how much each feature contributes to the prediction.
    # Large absolute values = high influence on the output price.
    with st.expander("🔍 Model Coefficients"):
        coef_df = pd.DataFrame({
            "Feature":     feature_cols,
            "Coefficient": model.coef_,
        }).sort_values("Coefficient", key=abs, ascending=False)  # Most influential first
        st.dataframe(coef_df, use_container_width=True)

else:
    # Shown before the user clicks Run — acts as a welcome/instruction message
    st.info("👈 Configure the settings in the sidebar and click **Run Prediction** to get started.")
