"""
Liveness Detection Module
Uses Eye Aspect Ratio (EAR) and micro-movement tracking
to prevent photo/screen spoofing during face recognition.
"""

import math
import numpy as np


def _euclidean(p1, p2):
    """Euclidean distance between two (x, y) points."""
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def compute_ear(eye_points):
    """
    Compute Eye Aspect Ratio (EAR) for a single eye.

    Args:
        eye_points: list of 6 (x, y) tuples from face_recognition landmarks

    Returns:
        float: EAR value (typically 0.2-0.4 for open eyes, <0.2 for closed)
    """
    A = _euclidean(eye_points[1], eye_points[5])
    B = _euclidean(eye_points[2], eye_points[4])
    C = _euclidean(eye_points[0], eye_points[3])

    if C == 0:
        return 0.0

    return (A + B) / (2.0 * C)


def get_ear_from_landmarks(landmarks):
    """
    Get average EAR from a face_recognition landmarks dict.

    Args:
        landmarks: dict with 'left_eye' and 'right_eye' keys

    Returns:
        float or None if eyes not found
    """
    if not landmarks:
        return None
    if "left_eye" not in landmarks or "right_eye" not in landmarks:
        return None

    left_ear = compute_ear(landmarks["left_eye"])
    right_ear = compute_ear(landmarks["right_eye"])

    return (left_ear + right_ear) / 2.0


class LivenessChecker:
    """
    Tracks facial movement over multiple frames to determine if a face
    belongs to a live person vs a static photo or phone screen.

    Checks performed:
        1. EAR variance — natural eyes fluctuate slightly between frames
        2. Position variance — live faces have micro head movements
        3. Blink detection — at least one blink observed
    """

    EAR_BLINK_THRESHOLD = 0.22
    MIN_EAR_VARIANCE = 0.004
    MIN_POSITION_VARIANCE = 2.5
    HISTORY_SIZE = 15
    MIN_FRAMES = 8

    def __init__(self):
        self.tracking = {}

    def update(self, student_id, landmarks, face_location):
        """
        Feed a new frame's data for a given student.

        Args:
            student_id: int — database student id
            landmarks: dict from face_recognition.face_landmarks()
            face_location: (top, right, bottom, left) tuple

        Returns:
            (is_live: bool, reason: str)
        """
        if student_id not in self.tracking:
            self.tracking[student_id] = {
                "ear_history": [],
                "position_history": [],
                "blink_count": 0,
                "last_ear": None,
                "frames_seen": 0,
            }

        track = self.tracking[student_id]
        track["frames_seen"] += 1

        ear = get_ear_from_landmarks(landmarks)
        if ear is None:
            return True, "no_landmarks"

        # Detect blink transitions (open -> closed)
        if track["last_ear"] is not None:
            if (
                track["last_ear"] > self.EAR_BLINK_THRESHOLD
                and ear < self.EAR_BLINK_THRESHOLD
            ):
                track["blink_count"] += 1
        track["last_ear"] = ear

        # Store EAR history
        track["ear_history"].append(ear)
        if len(track["ear_history"]) > self.HISTORY_SIZE:
            track["ear_history"].pop(0)

        # Store face center position
        top, right, bottom, left = face_location
        cx = (left + right) / 2
        cy = (top + bottom) / 2
        track["position_history"].append((cx, cy))
        if len(track["position_history"]) > self.HISTORY_SIZE:
            track["position_history"].pop(0)

        # Need enough frames before making a determination
        if track["frames_seen"] < self.MIN_FRAMES:
            return True, "gathering_data"

        # Check 1: EAR variance (eyes naturally fluctuate)
        ear_variance = float(np.std(track["ear_history"]))

        # Check 2: Position variance (head micro-movement)
        positions = np.array(track["position_history"])
        pos_variance = float(np.mean(np.std(positions, axis=0)))

        # Check 3: Blink detected
        has_blink = track["blink_count"] > 0

        checks_passed = sum(
            [
                ear_variance > self.MIN_EAR_VARIANCE,
                pos_variance > self.MIN_POSITION_VARIANCE,
                has_blink,
            ]
        )

        is_live = checks_passed >= 2

        if is_live:
            return True, "live"
        elif track["frames_seen"] < self.HISTORY_SIZE:
            return True, "analyzing"
        else:
            return False, "suspected_spoof"

    def is_confirmed_live(self, student_id):
        """Check if student has been confirmed as live."""
        track = self.tracking.get(student_id)
        if not track or track["frames_seen"] < self.MIN_FRAMES:
            return False
        return True

    def reset(self, student_id=None):
        """Reset tracking for a specific student or all students."""
        if student_id is not None:
            self.tracking.pop(student_id, None)
        else:
            self.tracking.clear()

