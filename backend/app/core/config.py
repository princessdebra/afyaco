from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://afyaco:afyaco@localhost:5432/afyaco"
    jwt_secret: str = "change-me-in-prod"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    environment: str = "development"

    # Xenova Identity Assurance (XIA)
    biometric_provider_key: str = "mock"
    xia_challenge_ttl_seconds: int = 120
    xia_default_geofence_meters: int = 300
    xia_max_location_age_seconds: int = 120
    xia_max_gps_accuracy_meters: int = 150
    # Cosine-similarity cutoff for the open-source CV provider's ArcFace
    # embeddings. This is the upstream model family's commonly cited starting
    # point, NOT a value calibrated against Xenova's own population/cameras —
    # see app/biometrics/opensource_cv.py module docstring.
    xia_face_match_threshold: float = 0.36

    # Challenge-response liveness ("turn your head left/right", "nod") — see
    # app/services/liveness_challenge.py. Thresholds are a starting point, not
    # empirically calibrated against real users in this environment.
    # Covers capture burst + the location permission prompt + GPS fix time,
    # which on a real phone (vs. a quick local test) routinely exceeds 30s —
    # observed expiring on a genuine real-time attempt during testing.
    xia_liveness_challenge_ttl_seconds: int = 120
    xia_challenge_min_frames: int = 3
    xia_challenge_yaw_threshold_deg: float = 15.0
    xia_challenge_pitch_threshold_deg: float = 12.0

    # Passive single-frame liveness (app/biometrics/opensource_cv.py) is known
    # to misfire on real phone-selfie captures (trained mostly on webcam-
    # distance imagery) — observed producing a confident false "spoof" on a
    # genuine live face during testing. "hard" = blocks on failure; "soft" =
    # a failure here routes to manual review instead of an automatic hard
    # block (challenge-response liveness remains a hard gate either way).
    # Default stays "hard"; set XIA_PASSIVE_LIVENESS_ENFORCEMENT=soft via env
    # for a deployment where this has been observed to misfire, as a
    # disclosed, deliberate tradeoff — not a general production recommendation.
    xia_passive_liveness_enforcement: str = "hard"

    # Swahili/English chat translation (app/services/translation.py) — calls a
    # self-hosted Qwen model via Ollama on the devserver. CPU-only (num_gpu=0
    # in the request) deliberately: the shared devserver's GPU had ~2.6GB
    # free at the time this was set up, not enough headroom to claim safely.
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_translate_model: str = "qwen2.5:1.5b"


settings = Settings()
