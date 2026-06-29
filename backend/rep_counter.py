"""
Rep counter state machine for real-time pushup counting.

Classification strategy:
  - Form label (correct/wrong) is decided ONCE per completed repetition,
    not per frame. A rep is complete when: up → down → up.
  - During the DOWN phase, form labels from each frame are accumulated.
  - On rep completion, the majority vote across all DOWN-phase frames
    determines whether the rep was correct or wrong.
  - This prevents flicker and avoids penalising momentary detection noise.
"""

from collections import Counter
from config import ELBOW_ANGLE_DOWN, ELBOW_ANGLE_UP

# Hysteresis band to avoid flickering at threshold boundaries
_HYST = 5  # degrees


class RepCounter:
    """
    State machine: idle → up → down → up (rep counted + labelled)

    Attributes
    ----------
    count           : total reps completed
    correct_count   : reps classified as correct
    incorrect_count : reps classified as wrong
    state           : current phase ("idle" | "up" | "down")
    last_angle      : most recent average elbow angle
    last_rep_label  : form label of the last completed rep ("correct"|"wrong"|None)
    rep_history     : list of {"rep": n, "label": str} for every completed rep
    """

    def __init__(self):
        self.reset()

    # ------------------------------------------------------------------
    def reset(self):
        self.count           = 0
        self.correct_count   = 0
        self.incorrect_count = 0
        self.state           = "idle"
        self.last_angle      = None
        self.last_rep_label  = None
        self.rep_history     = []
        self._down_labels    = []   # frame-level labels collected during DOWN phase

    # ------------------------------------------------------------------
    def update(self, left_angle: float, right_angle: float,
               frame_label: str | None = None) -> dict:
        """
        Call once per processed frame.

        Parameters
        ----------
        left_angle, right_angle : elbow angles (degrees)
        frame_label             : per-frame ML prediction ("correct"|"wrong"|None)
                                  Collect during DOWN phase for majority-vote.

        Returns get_state() dict (always consistent snapshot).
        """
        avg = (left_angle + right_angle) / 2
        self.last_angle = avg

        if self.state == "idle":
            # Wait until arms are extended before starting
            if avg > ELBOW_ANGLE_UP:
                self.state = "up"

        elif self.state == "up":
            # Transition to DOWN with hysteresis
            if avg < ELBOW_ANGLE_DOWN + _HYST:
                self.state = "down"
                self._down_labels = []

        elif self.state == "down":
            # Accumulate form labels while in the down phase
            if frame_label in ("correct", "wrong"):
                self._down_labels.append(frame_label)

            # Transition back to UP → rep complete
            if avg > ELBOW_ANGLE_UP - _HYST:
                self._complete_rep()
                self.state = "up"

        return self.get_state()

    # ------------------------------------------------------------------
    def _complete_rep(self):
        """Increment counter and assign form label via majority vote."""
        self.count += 1

        if self._down_labels:
            vote = Counter(self._down_labels).most_common(1)[0][0]
        else:
            # No frames collected → cannot decide, default wrong
            vote = "wrong"

        self.last_rep_label = vote
        if vote == "correct":
            self.correct_count += 1
        else:
            self.incorrect_count += 1

        self.rep_history.append({"rep": self.count, "label": vote})

    # ------------------------------------------------------------------
    def get_state(self) -> dict:
        return {
            "count":           self.count,
            "correct_count":   self.correct_count,
            "incorrect_count": self.incorrect_count,
            "state":           self.state,
            "avg_elbow_angle": round(self.last_angle, 1) if self.last_angle is not None else None,
            "last_rep_label":  self.last_rep_label,
        }
