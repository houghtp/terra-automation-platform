"""GA4 client using Google Analytics Data API (beta)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List
import logging

try:
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import DateRange, Metric, Dimension, RunReportRequest, MetricAggregation
    from google.oauth2.credentials import Credentials
except ModuleNotFoundError:  # pragma: no cover - handled at runtime
    BetaAnalyticsDataClient = None  # type: ignore
    Credentials = None  # type: ignore
    DateRange = Metric = Dimension = RunReportRequest = MetricAggregation = None  # type: ignore


class Ga4Client:
    """Minimal interface to fetch GA4 daily metrics."""

    def __init__(self, credentials: Credentials):
        if not BetaAnalyticsDataClient or not Credentials:
            raise ImportError(
                "GA4 client dependencies are missing. Install google-analytics-data, google-auth, and googleapis-common-protos."
            )
        self.credentials = credentials
        self.client = BetaAnalyticsDataClient(credentials=credentials)

    @classmethod
    def from_tokens(
        cls,
        access_token: str,
        refresh_token: str,
        client_id: str,
        client_secret: str,
        access_token_expires_at: str | None = None,
    ) -> "Ga4Client":
        expiry = None
        if access_token_expires_at:
            try:
                expiry = datetime.fromisoformat(access_token_expires_at)
            except ValueError:
                expiry = None
        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/analytics.readonly"],
            expiry=expiry,
        )
        return cls(creds)

    def current_token_data(self) -> Dict[str, Any]:
        """Return the current access token/expiry (after any refresh)."""
        token = getattr(self.credentials, "token", None)
        expiry = getattr(self.credentials, "expiry", None)
        return {
            "access_token": token,
            "access_token_expires_at": expiry.isoformat() if expiry else None,
        }

    @staticmethod
    def _parse_ga4_date(raw_date: str) -> date:
        """Parse GA4 date dimension values (GA4 returns YYYYMMDD, but also accept ISO)."""
        if not raw_date:
            raise ValueError("GA4 date value is empty")

        raw_date = raw_date.strip()
        try:
            return date.fromisoformat(raw_date)
        except ValueError:
            digits = "".join(ch for ch in raw_date if ch.isdigit())
            if len(digits) == 8:
                return date(int(digits[0:4]), int(digits[4:6]), int(digits[6:8]))
            raise ValueError(f"Unexpected GA4 date format: {raw_date!r}")

    async def fetch_daily_metrics(self, property_id: str, start: date, end: date) -> List[Dict[str, Any]]:
        """Fetch basic daily metrics for the given property."""
        # BetaAnalyticsDataClient is sync; wrap in thread if needed.
        request = RunReportRequest(
            property=property_id,
            date_ranges=[DateRange(start_date=start.isoformat(), end_date=end.isoformat())],
            dimensions=[Dimension(name="date")],
            metrics=[
                Metric(name="sessions"),
                Metric(name="totalUsers"),
                Metric(name="newUsers"),
                Metric(name="conversions"),
                Metric(name="engagementRate"),
                Metric(name="bounceRate"),
                Metric(name="averageSessionDuration"),
            ],
            metric_aggregations=[MetricAggregation.TOTAL],
        )
        response = self.client.run_report(request)

        results: List[Dict[str, Any]] = []
        if not response.rows:
            logging.getLogger(__name__).warning(
                "GA4 run_report returned no rows",
                extra={
                    "property_id": property_id,
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "row_count": response.row_count,
                    "totals_present": bool(response.totals),
                    "metadata": str(response.metadata),
                },
            )
            if response.totals:
                for total in response.totals:
                    metric_values = [float(m.value) if m.value else None for m in total.metric_values]
                    sessions_val = metric_values[0]
                    conversions_val = metric_values[3]
                    conversion_rate = (conversions_val / sessions_val) if sessions_val not in (None, 0) else None
                    conversions_per_1k = ((conversions_val / sessions_val) * 1000) if sessions_val not in (None, 0) else None
                    results.append(
                        {
                            "date": None,
                            "sessions": metric_values[0],
                            "users": metric_values[1],
                            "new_users": metric_values[2],
                            "conversions": metric_values[3],
                            "engagement_rate": metric_values[4],
                            "bounce_rate": metric_values[5],
                            "avg_engagement_time": metric_values[6],
                            "conversion_rate": conversion_rate,
                            "conversions_per_1k": conversions_per_1k,
                        }
                    )
            return results

        for row in response.rows:
            dim_values = [d.value for d in row.dimension_values]
            metric_values = [float(m.value) if m.value else None for m in row.metric_values]
            sessions_val = metric_values[0]
            conversions_val = metric_values[3]
            conversion_rate = (conversions_val / sessions_val) if sessions_val not in (None, 0) else None
            conversions_per_1k = ((conversions_val / sessions_val) * 1000) if sessions_val not in (None, 0) else None
            results.append(
                {
                    "date": self._parse_ga4_date(dim_values[0]),
                    "sessions": sessions_val,
                    "users": metric_values[1],
                    "new_users": metric_values[2],
                    "conversions": conversions_val,
                    "engagement_rate": metric_values[4],
                    "bounce_rate": metric_values[5],
                    "avg_engagement_time": metric_values[6],  # seconds
                    "conversion_rate": conversion_rate,
                    "conversions_per_1k": conversions_per_1k,
                }
            )
        return results
