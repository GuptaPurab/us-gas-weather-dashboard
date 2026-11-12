# US Natural Gas Weather Monitor

A mobile-friendly Streamlit dashboard for the latest seven complete days of
daily mean and minimum temperatures across ten US urban markets.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy

1. Push `app.py`, `requirements.txt`, and this README to a GitHub repository.
2. In Streamlit Community Cloud, create an app from that repository.
3. Select `app.py` as the entry point.
4. Deploy and open the generated URL on your phone.

The dashboard uses Open-Meteo and refreshes its cached data hourly. Use
**Refresh data now** in the sidebar for an immediate refresh.
