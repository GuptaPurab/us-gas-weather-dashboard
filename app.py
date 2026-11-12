from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(
    page_title="US Natural Gas Weather Monitor",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CITIES = {
    "Houston": (29.7604, -95.3698),
    "New York City": (40.7128, -74.0060),
    "Chicago": (41.8781, -87.6298),
    "Los Angeles": (34.0522, -118.2437),
    "Dallas–Fort Worth": (32.7767, -96.7970),
    "Philadelphia": (39.9526, -75.1652),
    "Detroit": (42.3314, -83.0458),
    "Boston": (42.3601, -71.0589),
    "San Francisco Bay Area": (37.7749, -122.4194),
    "Atlanta": (33.7490, -84.3880),
}
API_URL = "https://api.open-meteo.com/v1/forecast"


st.markdown(
    """
    <style>
      .block-container {padding-top: 1.2rem; padding-bottom: 2rem;
                        max-width: 1150px;}
      [data-testid="stMetric"] {
        background: rgba(128,128,128,0.08);
        border: 1px solid rgba(128,128,128,0.18);
        padding: 14px; border-radius: 12px;
      }
      h1 {font-size: clamp(1.55rem, 5vw, 2.25rem) !important;}
      h2 {font-size: clamp(1.2rem, 4vw, 1.6rem) !important;}
      @media (max-width: 640px) {
        .block-container {padding-left: 0.8rem; padding-right: 0.8rem;}
      }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("US Natural Gas Weather Monitor")
st.caption("Seven-day temperature dashboard · 10 US urban markets · °C")

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_city(city, latitude, longitude):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": ["temperature_2m_mean", "temperature_2m_min"],
        "past_days": 7,
        "forecast_days": 1,
        "timezone": "auto",
        "temperature_unit": "celsius",
    }
    response = requests.get(API_URL, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    daily = payload["daily"]

    frame = pd.DataFrame({
        "date": pd.to_datetime(daily["time"]),
        "average_temperature_c": daily["temperature_2m_mean"],
        "lowest_temperature_c": daily["temperature_2m_min"],
    })

    timezone_name = payload.get("timezone", "UTC")
    local_today = datetime.now(ZoneInfo(timezone_name)).date()
    frame = frame[frame["date"].dt.date < local_today].tail(7).copy()

    if len(frame) != 7:
        raise ValueError(f"{city}: expected 7 complete days, got {len(frame)}")

    frame["city"] = city
    return frame


@st.cache_data(ttl=3600, show_spinner=False)
def load_all_data():
    results = []
    failures = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        jobs = {
            pool.submit(fetch_city, name, lat, lon): name
            for name, (lat, lon) in CITIES.items()
        }
        for job in as_completed(jobs):
            city = jobs[job]
            try:
                results.append(job.result())
            except Exception as error:
                failures.append(f"{city}: {error}")
    if failures:
        raise RuntimeError("Some city data could not be retrieved: " + "; ".join(failures))
    return pd.concat(results, ignore_index=True).sort_values(["date", "city"])


with st.sidebar:
    st.header("Dashboard controls")
    if st.button("Refresh data now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.caption("Data refreshes automatically from the API cache every hour.")
    st.caption("The current incomplete local day is excluded.")

try:
    with st.spinner("Loading the latest seven complete days for all 10 cities..."):
        data = load_all_data()
except Exception as exc:
    st.error(f"Unable to load the complete dataset: {exc}")
    st.stop()

daily = (
    data.groupby("date")
    .agg(
        average_daily_temperature_c=("average_temperature_c", "mean"),
        average_daily_low_c=("lowest_temperature_c", "mean"),
    )
    .sort_index()
)
city_summary = (
    data.groupby("city")
    .agg(
        average_temperature_c=("average_temperature_c", "mean"),
        average_daily_low_c=("lowest_temperature_c", "mean"),
    )
    .reindex(list(CITIES.keys()))
)

overall_avg = data["average_temperature_c"].mean()
overall_low = data["lowest_temperature_c"].mean()
date_min = data["date"].min().strftime("%d %b %Y")
date_max = data["date"].max().strftime("%d %b %Y")

st.caption(f"Reporting period: {date_min} – {date_max}")

m1, m2, m3 = st.columns(3)
m1.metric("10-city average", f"{overall_avg:.2f} °C")
m2.metric("Average daily low", f"{overall_low:.2f} °C")
m3.metric("Cities monitored", "10")

st.divider()
st.subheader("Daily temperature summary")
daily_display = daily.copy()
daily_display.index = daily_display.index.strftime("%b %d")
daily_display.index.name = "Date"
daily_display = daily_display.rename(columns={
    "average_daily_temperature_c": "Average temperature (°C)",
    "average_daily_low_c": "Average lowest temperature (°C)",
})
st.dataframe(
    daily_display.round(2),
    use_container_width=True,
)

st.subheader("Average daily temperature")
bar_data = daily.reset_index()
bar_data["date_label"] = bar_data["date"].dt.strftime("%b %d")
bar = px.bar(
    bar_data,
    x="date_label",
    y="average_daily_temperature_c",
    text=bar_data["average_daily_temperature_c"].map(lambda x: f"{x:.2f}°C"),
    labels={
        "date_label": "Date",
        "average_daily_temperature_c": "Average temperature (°C)",
    },
)
bar.update_traces(textposition="outside", cliponaxis=False)
bar.update_layout(
    height=390,
    margin=dict(l=10, r=10, t=25, b=10),
    yaxis_title="Temperature (°C)",
    xaxis_title="Date",
)
st.plotly_chart(bar, use_container_width=True)

st.subheader("Seven-day temperature trend")
line = px.line(
    bar_data,
    x="date_label",
    y="average_daily_temperature_c",
    markers=True,
    labels={
        "date_label": "Date",
        "average_daily_temperature_c": "Average temperature (°C)",
    },
)
line.update_traces(
    mode="lines+markers+text",
    text=bar_data["average_daily_temperature_c"].map(lambda x: f"{x:.2f}°"),
    textposition="top center",
)
line.update_layout(
    height=350,
    margin=dict(l=10, r=10, t=25, b=10),
    yaxis_title="Temperature (°C)",
    xaxis_title="Date",
)
st.plotly_chart(line, use_container_width=True)

st.subheader("Daily lowest temperature by city")
low_table = data.pivot(
    index="date", columns="city", values="lowest_temperature_c"
).reindex(columns=list(CITIES.keys()))
low_table.index = low_table.index.strftime("%b %d")
low_table.index.name = "Date"
st.dataframe(low_table.round(2), use_container_width=True)

st.subheader("Seven-day city comparison")
summary_display = city_summary.rename(columns={
    "average_temperature_c": "Average temperature (°C)",
    "average_daily_low_c": "Average daily low (°C)",
})
summary_display.loc["10-city average"] = [overall_avg, overall_low]
st.dataframe(summary_display.round(2), use_container_width=True)

st.subheader("Explore an individual city")
selected_city = st.selectbox("Select city", list(CITIES.keys()))
city_data = data[data["city"] == selected_city].sort_values("date").copy()
city_data["date_label"] = city_data["date"].dt.strftime("%b %d")
city_fig = px.line(
    city_data,
    x="date_label",
    y=["average_temperature_c", "lowest_temperature_c"],
    markers=True,
    labels={
        "date_label": "Date",
        "value": "Temperature (°C)",
        "variable": "Metric",
    },
)
city_fig.update_layout(height=350, margin=dict(l=10, r=10, t=25, b=10))
st.plotly_chart(city_fig, use_container_width=True)

csv = data.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download raw data (CSV)",
    data=csv,
    file_name="us_city_daily_temperature.csv",
    mime="text/csv",
    use_container_width=True,
)

st.caption(
    "Source: Open-Meteo. Daily mean and minimum 2 m air temperatures. "
    "San Francisco represents the wider Bay Area; Dallas represents "
    "the Dallas–Fort Worth market."
)
