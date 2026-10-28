"""Real, open-source computer-vision biometric provider for Xenova Identity
Assurance.

- **Face detection + recognition**: InsightFace's `buffalo_l` model pack
  (SCRFD detector + ArcFace/w600k_r50 recognition, ONNX, Apache-2.0-licensed
  project — https://github.com/deepinsight/insightface). Produces a 512-d,
  L2-normalized embedding per face; identity is cosine similarity between
  embeddings.
- **Liveness / presentation-attack detection**: the MiniFASNetV2 + MiniFASNetV1SE
  models from minivision-ai's Silent-Face-Anti-Spoofing project (Apache 2.0,
  vendored under `app/biometrics/_vendor/silent_face_anti_spoofing/`, model
  weights and license file included verbatim). This is passive, single-frame
  presentation-attack detection (print/replay attacks) — it is NOT challenge-
  response liveness (no blink/head-turn prompt) and has the detection limits
  that implies; see the module's own README for its published evaluation.

Both model families are genuine, published, pretrained open-source models —
this is real face recognition and real presentation-attack detection, not a
placeholder. What is NOT done, and must happen before any production use:

- No calibration/validation was run against this deployment's own population,
  cameras or lighting conditions. The match threshold and liveness decision
  below use the upstream projects' own published defaults/conventions, which
  is a starting point, not a validated operating point for Xenova.
- No presentation-attack test set (printed photos, screen replays, masks) was
  run against this installation to measure its actual false-accept rate here.
- Templates (`template_ref`, a base64-encoded float32 embedding) are stored as
  plain text in the database today — encryption at rest for this column is
  still an open item (see backend/README.md "Remaining work").
"""

import base64
import pathlib

import cv2
import numpy as np
import torch
import torch.nn.functional as torch_F
from insightface.app import FaceAnalysis

from app.biometrics._vendor.silent_face_anti_spoofing.src.generate_patches import CropImage
from app.biometrics._vendor.silent_face_anti_spoofing.src.model_lib.MiniFASNet import (
    MiniFASNetV1,
    MiniFASNetV1SE,
    MiniFASNetV2,
    MiniFASNetV2SE,
)
from app.biometrics._vendor.silent_face_anti_spoofing.src.utility import get_kernel, parse_model_name
from app.biometrics.base import (
    BiometricVerificationProvider,
    EnrollmentReference,
    HeadPose,
    LivenessDecision,
    LivenessResult,
    MatchDecision,
    MatchResult,
    ProviderHealth,
    QualityDecision,
    QualityResult,
)
from app.core.config import settings

_MODEL_MAPPING = {
    "MiniFASNetV1": MiniFASNetV1,
    "MiniFASNetV2": MiniFASNetV2,
    "MiniFASNetV1SE": MiniFASNetV1SE,
    "MiniFASNetV2SE": MiniFASNetV2SE,
}
_LIVENESS_MODEL_DIR = pathlib.Path(__file__).parent / "_vendor" / "silent_face_anti_spoofing" / "resources" / "anti_spoof_models"

MIN_FACE_SIZE_PX = 80
MIN_DETECTION_SCORE = 0.5
# Liveness "real" class index 1, per the upstream project's test.py convention.
REAL_LABEL = 1


def _load_liveness_models() -> list[tuple[torch.nn.Module, float | None, tuple[int, int]]]:
    models = []
    for path in sorted(_LIVENESS_MODEL_DIR.glob("*.pth")):
        h_input, w_input, model_type, scale = parse_model_name(path.name)
        kernel = get_kernel(h_input, w_input)
        model = _MODEL_MAPPING[model_type](conv6_kernel=kernel)
        state_dict = torch.load(path, map_location="cpu", weights_only=True)
        first_key = next(iter(state_dict))
        if first_key.startswith("module."):
            state_dict = {k[len("module."):]: v for k, v in state_dict.items()}
        model.load_state_dict(state_dict)
        model.eval()
        models.append((model, scale, (h_input, w_input)))
    if not models:
        raise RuntimeError(f"No liveness model weights found under {_LIVENESS_MODEL_DIR}")
    return models


def _to_tensor(patch_bgr_uint8: np.ndarray) -> torch.Tensor:
    # Equivalent to the upstream project's `trans.ToTensor()`: HWC uint8
    # [0,255] -> CHW float32 [0,1]. Channel order is left as BGR (OpenCV's
    # native order) because the upstream models were trained on BGR frames
    # read with cv2.imread, with no RGB conversion anywhere in their pipeline.
    arr = patch_bgr_uint8.transpose(2, 0, 1).astype(np.float32) / 255.0
    return torch.from_numpy(arr).unsqueeze(0)


def _decode_image(image_bytes: bytes) -> np.ndarray | None:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)  # BGR, matches upstream convention
    return img


class OpenSourceCvProvider(BiometricVerificationProvider):
    key = "opensource_cv"

    def __init__(self):
        self._face_app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        self._face_app.prepare(ctx_id=-1, det_size=(640, 640))
        self._liveness_models = _load_liveness_models()
        self._match_threshold = settings.xia_face_match_threshold

    def _detect_single_face(self, img: np.ndarray):
        faces = self._face_app.get(img)
        if len(faces) == 0:
            return None, "no face detected"
        if len(faces) > 1:
            return None, "more than one face detected"
        face = faces[0]
        if face.det_score < MIN_DETECTION_SCORE:
            return None, f"low detection confidence ({face.det_score:.2f})"
        x1, y1, x2, y2 = face.bbox
        if min(x2 - x1, y2 - y1) < MIN_FACE_SIZE_PX:
            return None, "face too small in frame"
        return face, None

    async def assess_capture_quality(self, image_bytes: bytes) -> QualityResult:
        img = _decode_image(image_bytes)
        if img is None:
            return QualityResult(QualityDecision.REJECTED, reason="could not decode image")
        _, reason = self._detect_single_face(img)
        if reason is not None:
            return QualityResult(QualityDecision.REJECTED, reason=reason)
        return QualityResult(QualityDecision.ACCEPTABLE)

    async def perform_liveness_check(self, image_bytes: bytes) -> LivenessResult:
        img = _decode_image(image_bytes)
        if img is None:
            return LivenessResult(LivenessDecision.UNAVAILABLE, reason="could not decode image")
        face, reason = self._detect_single_face(img)
        if face is None:
            return LivenessResult(LivenessDecision.UNAVAILABLE, reason=reason)

        x1, y1, x2, y2 = face.bbox
        bbox_xywh = [int(x1), int(y1), int(x2 - x1), int(y2 - y1)]
        cropper = CropImage()
        total = np.zeros((1, 3), dtype=np.float32)
        for model, scale, (h, w) in self._liveness_models:
            patch = cropper.crop(org_img=img, bbox=bbox_xywh, scale=scale, out_w=w, out_h=h, crop=scale is not None)
            tensor = _to_tensor(patch)
            with torch.no_grad():
                probs = torch_F.softmax(model(tensor), dim=1).numpy()
            total += probs

        label = int(np.argmax(total))
        confidence = float(total[0][label]) / len(self._liveness_models)
        if label == REAL_LABEL:
            return LivenessResult(LivenessDecision.PASSED, reason=f"real, confidence={confidence:.2f}")
        return LivenessResult(LivenessDecision.FAILED, reason=f"spoof suspected (label={label}, confidence={confidence:.2f})")

    async def create_enrollment_reference(self, image_bytes: bytes) -> EnrollmentReference:
        img = _decode_image(image_bytes)
        face, reason = self._detect_single_face(img) if img is not None else (None, "could not decode image")
        if face is None:
            raise ValueError(f"Cannot create enrollment reference: {reason}")
        embedding = face.normed_embedding.astype(np.float32)  # already L2-normalized by insightface
        template_ref = base64.b64encode(embedding.tobytes()).decode("ascii")
        return EnrollmentReference(template_ref=template_ref, template_version="insightface-buffalo_l-arcface-v1")

    async def compare_with_enrollment(self, template_ref: str, probe_image_bytes: bytes) -> MatchResult:
        img = _decode_image(probe_image_bytes)
        face, reason = self._detect_single_face(img) if img is not None else (None, "could not decode image")
        if face is None:
            return MatchResult(decision=MatchDecision.NO_MATCH, score=None, threshold=self._match_threshold)

        enrolled = np.frombuffer(base64.b64decode(template_ref), dtype=np.float32)
        probe = face.normed_embedding.astype(np.float32)
        similarity = float(np.dot(enrolled, probe))  # both L2-normalized -> dot product == cosine similarity
        decision = MatchDecision.MATCH if similarity >= self._match_threshold else MatchDecision.NO_MATCH
        return MatchResult(decision=decision, score=similarity, threshold=self._match_threshold)

    async def get_provider_health(self) -> ProviderHealth:
        return ProviderHealth(healthy=True, detail="insightface buffalo_l + Silent-Face-Anti-Spoofing loaded")

    async def estimate_head_pose(self, image_bytes: bytes) -> HeadPose | None:
        """Uses InsightFace's `Face.pose` — derived from the 3D-68 landmark
        model included in the buffalo_l pack — rather than a second model.

        Caveat disclosed, not glossed over: the exact sign convention for
        "turned left" vs "turned right" in InsightFace's `pose` output has not
        been empirically confirmed against a real human face in this
        environment (no real face photos were available to test with). The
        direction mapping in `services/liveness_challenge.py` is my best-
        documented reading of the convention and should be verified against a
        real camera before this is trusted for anything beyond "did the
        measured angle change substantially in *some* direction."
        """
        img = _decode_image(image_bytes)
        if img is None:
            return None
        face, _ = self._detect_single_face(img)
        if face is None:
            return None
        pose = getattr(face, "pose", None)
        if pose is None:
            return None
        pitch, yaw, roll = (float(v) for v in pose)
        return HeadPose(yaw=yaw, pitch=pitch, roll=roll)
