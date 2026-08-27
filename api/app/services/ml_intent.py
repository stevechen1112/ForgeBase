"""
ML Intent Scoring  (3.2.1 + 3.2.2)

Trains a RandomForestClassifier on historical visitor event data to predict
conversion probability (likelihood to submit RFQ).

Feature space (per visitor):
  - event counts: page_view, product_view, application_view, spec_download,
    faq_expand, comparison_view, return_visit, rfq_start
  - aggregate: total_page_views, total_visits, intent_score (rule-based)
  - recency: days_since_first_seen, days_since_last_active

Label: has_rfq_submit (1 = at least one rfq_submit event)

Score blending (3.2.2):
  blended = round(alpha * rule_score + (1-alpha) * ml_prob * 100)
  default alpha = 0.65 (rule-based weighted higher initially)
"""
import logging
import os
import pickle
from datetime import datetime, timezone
from typing import Any

import numpy as np
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

logger = logging.getLogger(__name__)

ML_MODEL_DIR = os.getenv("ML_MODEL_DIR", "/tmp/ml_models")
ML_MODEL_FILE = os.path.join(ML_MODEL_DIR, "intent_v1.pkl")
ML_METADATA_FILE = os.path.join(ML_MODEL_DIR, "intent_v1_meta.json")

FEATURE_NAMES = [
    "ev_page_view",
    "ev_product_view",
    "ev_application_view",
    "ev_spec_download",
    "ev_faq_expand",
    "ev_comparison_view",
    "ev_return_visit",
    "ev_rfq_start",
    "total_page_views",
    "total_visits",
    "rule_intent_score",
    "days_since_first_seen",
    "days_since_last_active",
]

BLEND_ALPHA = 0.65  # weight for rule-based score

# ── Load cached model at startup ──────────────────────────────────────────────

_model_cache: Any = None
_model_meta: dict = {}


def _load_model() -> Any | None:
    global _model_cache, _model_meta
    if _model_cache is not None:
        return _model_cache
    if not os.path.exists(ML_MODEL_FILE):
        return None
    try:
        import json
        with open(ML_MODEL_FILE, "rb") as f:
            _model_cache = pickle.load(f)
        if os.path.exists(ML_METADATA_FILE):
            with open(ML_METADATA_FILE) as f:
                _model_meta = json.load(f)
        logger.info("ML intent model loaded from disk")
        return _model_cache
    except (OSError, pickle.UnpicklingError, json.JSONDecodeError) as exc:
        logger.warning("Failed to load ML model: %s", exc)
        return None


# ── Feature Extraction ────────────────────────────────────────────────────────

async def extract_features_for_visitor(
    visitor_row: dict[str, Any],
    event_counts: dict[str, int],
    now: datetime | None = None,
) -> np.ndarray:
    """
    Build feature vector for a single visitor.

    Args:
        visitor_row: dict with keys matching Visitor model columns
        event_counts: dict mapping event_name → count for this visitor
    """
    if now is None:
        now = datetime.now(timezone.utc)

    def _days(dt_str: Any) -> float:
        if dt_str is None:
            return 999.0
        if isinstance(dt_str, datetime):
            dt = dt_str
        else:
            dt = datetime.fromisoformat(str(dt_str))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0.0, (now - dt).total_seconds() / 86400)

    features = [
        float(event_counts.get("page_view", 0)),
        float(event_counts.get("product_view", 0)),
        float(event_counts.get("application_view", 0)),
        float(event_counts.get("spec_download", 0)),
        float(event_counts.get("faq_expand", 0)),
        float(event_counts.get("comparison_view", 0)),
        float(event_counts.get("return_visit", 0)),
        float(event_counts.get("rfq_start", 0)),
        float(visitor_row.get("total_page_views", 0)),
        float(visitor_row.get("total_visits", 0)),
        float(visitor_row.get("intent_score", 0)),
        _days(visitor_row.get("first_seen")),
        _days(visitor_row.get("last_activity_at") or visitor_row.get("last_seen")),
    ]
    return np.array(features, dtype=np.float32).reshape(1, -1)


# ── Inference ─────────────────────────────────────────────────────────────────

async def predict_ml_score(
    visitor_row: dict[str, Any],
    event_counts: dict[str, int],
) -> float:
    """
    Predict conversion probability (0.0 – 1.0) for a visitor.
    Returns 0.5 if model is not trained yet.
    """
    model = _load_model()
    if model is None:
        return estimate_score_from_heuristic(visitor_row, event_counts)

    try:
        features = await extract_features_for_visitor(visitor_row, event_counts)
        prob = float(model.predict_proba(features)[0][1])
        return round(prob, 4)
    except Exception:
        logger.exception("ML prediction failed")
        return estimate_score_from_heuristic(visitor_row, event_counts)


def estimate_score_from_heuristic(
    visitor_row: dict[str, Any],
    event_counts: dict[str, int],
) -> float:
    """
    Simple heuristic proxy when model is unavailable.
    Returns a rough probability in [0, 1].
    """
    score = visitor_row.get("intent_score", 0)
    downloads = event_counts.get("spec_download", 0)
    rfq_starts = event_counts.get("rfq_start", 0)
    prob = min(1.0, (score / 60.0) * 0.7 + downloads * 0.1 + rfq_starts * 0.2)
    return round(prob, 4)


# ── Score Blending (3.2.2) ────────────────────────────────────────────────────

def blend_scores(rule_score: int, ml_prob: float, alpha: float = BLEND_ALPHA) -> int:
    """
    Blend rule-based integer score with ML probability (0-1).

    blended = alpha * rule_score + (1 - alpha) * ml_prob * 100
    Clamped to [0, 100] and rounded.
    """
    blended = alpha * rule_score + (1.0 - alpha) * ml_prob * 100.0
    return int(round(max(0.0, min(100.0, blended))))


# ── Training  (3.2.1) ─────────────────────────────────────────────────────────

async def train_model(session: AsyncSession) -> dict[str, Any]:
    """
    Train RandomForestClassifier on all historical visitor data.

    Returns training metadata: accuracy, auc, sample_size, trained_at, feature_importance.
    """
    import json

    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import roc_auc_score
        from sklearn.model_selection import train_test_split
    except ImportError:
        logger.error("scikit-learn not installed. Cannot train ML model.")
        return {"error": "scikit-learn not available"}

    now = datetime.now(timezone.utc)

    # ── Fetch all visitor event counts ──────────────────────────────────────
    events_sql = text("""
        SELECT
            e.visitor_id::text,
            e.event_name,
            COUNT(*) as cnt
        FROM tracking_events e
        GROUP BY e.visitor_id, e.event_name
    """)
    events_result = await session.exec(events_sql)
    events_rows = events_result.mappings().all()

    # Build per-visitor event count dict
    visitor_events: dict[str, dict[str, int]] = {}
    for row in events_rows:
        vid = row["visitor_id"]
        if vid not in visitor_events:
            visitor_events[vid] = {}
        visitor_events[vid][row["event_name"]] = int(row["cnt"])

    if not visitor_events:
        return {"error": "No event data available for training"}

    # ── Fetch visitor records ────────────────────────────────────────────────
    visitors_sql = text("""
        SELECT
            v.visitor_id::text,
            v.total_page_views,
            v.total_visits,
            v.intent_score,
            v.first_seen,
            v.last_activity_at,
            v.last_seen,
            CASE WHEN EXISTS (
                SELECT 1 FROM tracking_events te
                WHERE te.visitor_id = v.visitor_id
                  AND te.event_name = 'rfq_submit'
            ) THEN 1 ELSE 0 END as has_rfq_submit
        FROM visitors v
        WHERE v.visitor_id::text IN :visitor_ids
    """)
    visitor_ids = list(visitor_events.keys())

    visitors_result = await session.exec(
        visitors_sql, params={"visitor_ids": tuple(visitor_ids)}
    )
    visitor_rows = visitors_result.mappings().all()

    if len(visitor_rows) < 20:
        return {
            "error": f"Insufficient data: only {len(visitor_rows)} visitors. Need at least 20."
        }

    # ── Build feature matrix ─────────────────────────────────────────────────
    X_list = []
    y_list = []

    for vrow in visitor_rows:
        vid = vrow["visitor_id"]
        ev = visitor_events.get(vid, {})
        features_arr = await extract_features_for_visitor(dict(vrow), ev, now=now)
        X_list.append(features_arr[0])
        y_list.append(int(vrow["has_rfq_submit"]))

    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.int32)

    # ── Train model ──────────────────────────────────────────────────────────
    positive_rate = y.mean()
    if positive_rate == 0 or positive_rate == 1:
        return {"error": "Labels are all one class — need both positive and negative examples"}

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=100, max_depth=8, random_state=42, n_jobs=-1,
        class_weight="balanced",
    )
    model.fit(X_train, y_train)

    # ── Evaluation ───────────────────────────────────────────────────────────
    y_prob = model.predict_proba(X_test)[:, 1]
    auc = float(roc_auc_score(y_test, y_prob))
    accuracy = float(model.score(X_test, y_test))

    importances = {
        name: round(float(imp), 4)
        for name, imp in zip(FEATURE_NAMES, model.feature_importances_)
    }

    # ── Persist model ────────────────────────────────────────────────────────
    os.makedirs(ML_MODEL_DIR, exist_ok=True)
    global _model_cache, _model_meta

    with open(ML_MODEL_FILE, "wb") as f:
        pickle.dump(model, f)
    _model_cache = model

    meta = {
        "model_type": "intent_v1",
        "algorithm": "RandomForestClassifier",
        "accuracy": round(accuracy, 4),
        "auc_score": round(auc, 4),
        "sample_size": len(X),
        "positive_rate": round(positive_rate, 4),
        "feature_names": FEATURE_NAMES,
        "feature_importance": importances,
        "trained_at": now.isoformat(),
        "blend_alpha": BLEND_ALPHA,
    }
    with open(ML_METADATA_FILE, "w") as f:
        json.dump(meta, f, indent=2)
    _model_meta = meta

    logger.info(f"ML model trained: acc={accuracy:.3f} auc={auc:.3f} n={len(X)}")
    return meta


def get_model_status() -> dict[str, Any]:
    """Return current model metadata / status."""
    import json
    if os.path.exists(ML_METADATA_FILE):
        try:
            with open(ML_METADATA_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "model_type": "intent_v1",
        "trained": False,
        "message": "模型尚未訓練。請累積足夠的訪客行為與 RFQ 資料後，點擊「重新訓練」開始首次訓練。",
    }
