// Pure functions that turn MediaPipe's per-frame output into the per-answer summary sent to the backend.
// No DOM or MediaPipe imports here, so everything can be unit-tested with `npm test`.
//
// Thresholds are hand-set starting points, not tuned on real recordings. Treat the scores as a coaching aid.

export const LIMITS = {
  yawDeg: 25,        // head turned further than this = not facing the screen
  pitchDeg: 22,      // head tilted up/down further than this = not facing the screen
  gazeSide: 0.5,     // eyes turned sideways (blendshape 0..1)
  gazeUp: 0.5,
  gazeDown: 0.65,    // looking down at a screen is normal, so this is more lenient
  smile: 0.35,       // mouthSmile blendshape above this counts as a smiling frame
  lookAwayMs: 1000,  // a look-away episode must last at least this long to be counted
};

/**
 * Where the face points, from MediaPipe's 4x4 facial transformation matrix (column-major, 16 numbers).
 * The face's forward axis is the third column; yaw is its sideways angle, pitch its up/down angle.
 * Only the size of the angles is used, so the sign convention does not matter.
 */
export function headDirection(m) {
  const fx = m[8], fy = m[9], fz = m[10];
  const yaw = (Math.atan2(fx, Math.abs(fz)) * 180) / Math.PI;
  const pitch = (Math.atan2(fy, Math.hypot(fx, fz)) * 180) / Math.PI;
  return { yaw, pitch };
}

/** blendshapes: [{categoryName, score}] -> plain object name -> score. */
export function blendMap(categories = []) {
  const o = {};
  for (const c of categories) o[c.categoryName] = c.score;
  return o;
}

/** Are the eyes turned well away from straight ahead? */
export function gazeAway(b) {
  const g = (k) => b[k] ?? 0;
  const side = Math.max((g("eyeLookOutLeft") + g("eyeLookInRight")) / 2, (g("eyeLookInLeft") + g("eyeLookOutRight")) / 2);
  const up = (g("eyeLookUpLeft") + g("eyeLookUpRight")) / 2;
  const down = (g("eyeLookDownLeft") + g("eyeLookDownRight")) / 2;
  return side > LIMITS.gazeSide || up > LIMITS.gazeUp || down > LIMITS.gazeDown;
}

/** One sampled frame -> {t, present, contact, smile, yaw, pitch}. t is milliseconds. */
export function classifyFrame(t, result) {
  const present = !!(result && result.faceLandmarks && result.faceLandmarks.length);
  if (!present) return { t, present: false, contact: false, smile: false, yaw: 0, pitch: 0 };
  const matrix = result.facialTransformationMatrixes?.[0]?.data;
  const { yaw, pitch } = matrix ? headDirection(matrix) : { yaw: 0, pitch: 0 };
  const b = blendMap(result.faceBlendshapes?.[0]?.categories);
  const headOk = Math.abs(yaw) <= LIMITS.yawDeg && Math.abs(pitch) <= LIMITS.pitchDeg;
  return {
    t, present: true, yaw, pitch,
    contact: headOk && !gazeAway(b),
    smile: ((b.mouthSmileLeft ?? 0) + (b.mouthSmileRight ?? 0)) / 2 > LIMITS.smile,
  };
}

const std = (xs) => {
  if (xs.length < 2) return 0;
  const mean = xs.reduce((a, c) => a + c, 0) / xs.length;
  return Math.sqrt(xs.reduce((a, c) => a + (c - mean) ** 2, 0) / xs.length);
};

/** Frames of one answer -> summary for the backend, or null if there is too little to judge. */
export function summarize(frames) {
  const n = frames.length;
  if (n < 5) return null;
  const present = frames.filter((f) => f.present);
  const pct = (k) => (100 * k) / n;

  // look-away episodes: runs of no-contact frames lasting at least LIMITS.lookAwayMs
  let events = 0, runStart = null;
  for (let i = 0; i <= n; i++) {
    const away = i < n && !frames[i].contact;
    if (away && runStart === null) runStart = frames[i].t;
    if (!away && runStart !== null) {
      const end = i < n ? frames[i].t : frames[n - 1].t;
      if (end - runStart >= LIMITS.lookAwayMs) events++;
      runStart = null;
    }
  }

  return {
    frames: n,
    face_present_pct: round1(pct(present.length)),
    eye_contact_pct: round1(pct(frames.filter((f) => f.contact).length)),
    smile_pct: round1(present.length ? (100 * present.filter((f) => f.smile).length) / present.length : 0),
    head_motion: round1(Math.hypot(std(present.map((f) => f.yaw)), std(present.map((f) => f.pitch)))),
    look_away_events: events,
  };
}

const round1 = (x) => Math.round(x * 10) / 10;
