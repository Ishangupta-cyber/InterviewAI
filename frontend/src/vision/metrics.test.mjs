// Run: npm test   (plain node, no test framework)
import assert from "node:assert/strict";
import { blendMap, classifyFrame, gazeAway, headDirection, summarize } from "./metrics.js";

const deg = (d) => (d * Math.PI) / 180;
const near = (a, b, tol = 0.01) => assert.ok(Math.abs(a - b) <= tol, `${a} is not within ${tol} of ${b}`);

// 4x4 matrix, column-major, rotating the face about the vertical (Y) or horizontal (X) axis
const rotY = (d) => [Math.cos(deg(d)), 0, -Math.sin(deg(d)), 0, 0, 1, 0, 0, Math.sin(deg(d)), 0, Math.cos(deg(d)), 0, 0, 0, 0, 1];
const rotX = (d) => [1, 0, 0, 0, 0, Math.cos(deg(d)), Math.sin(deg(d)), 0, 0, -Math.sin(deg(d)), Math.cos(deg(d)), 0, 0, 0, 0, 1];

const tests = {
  "head facing the screen has zero angles"() {
    const { yaw, pitch } = headDirection(rotY(0));
    near(yaw, 0); near(pitch, 0);
  },
  "head turned 30 degrees sideways reads as yaw 30"() {
    near(Math.abs(headDirection(rotY(30)).yaw), 30);
    near(Math.abs(headDirection(rotY(-30)).yaw), 30);
  },
  "head tilted 20 degrees reads as pitch 20"() {
    near(Math.abs(headDirection(rotX(20)).pitch), 20);
  },
  "blendMap and gazeAway"() {
    assert.equal(blendMap([{ categoryName: "a", score: 0.2 }]).a, 0.2);
    assert.equal(gazeAway({}), false);                                                    // looking straight ahead
    assert.equal(gazeAway({ eyeLookOutLeft: 0.9, eyeLookInRight: 0.9 }), true);           // eyes far to one side
    assert.equal(gazeAway({ eyeLookDownLeft: 0.4, eyeLookDownRight: 0.4 }), false);       // reading the screen
  },
  "classifyFrame: attentive, smiling face"() {
    const f = classifyFrame(0, {
      faceLandmarks: [[]], facialTransformationMatrixes: [{ data: rotY(5) }],
      faceBlendshapes: [{ categories: [{ categoryName: "mouthSmileLeft", score: 0.6 }, { categoryName: "mouthSmileRight", score: 0.6 }] }],
    });
    assert.deepEqual([f.present, f.contact, f.smile], [true, true, true]);
  },
  "classifyFrame: head turned away is not eye contact"() {
    const f = classifyFrame(0, { faceLandmarks: [[]], facialTransformationMatrixes: [{ data: rotY(40) }], faceBlendshapes: [{ categories: [] }] });
    assert.deepEqual([f.present, f.contact], [true, false]);
  },
  "classifyFrame: eyes to the side is not eye contact"() {
    const cats = [{ categoryName: "eyeLookOutLeft", score: 0.9 }, { categoryName: "eyeLookInRight", score: 0.9 }];
    const f = classifyFrame(0, { faceLandmarks: [[]], facialTransformationMatrixes: [{ data: rotY(0) }], faceBlendshapes: [{ categories: cats }] });
    assert.equal(f.contact, false);
  },
  "classifyFrame: no face"() {
    const f = classifyFrame(0, { faceLandmarks: [] });
    assert.deepEqual([f.present, f.contact, f.smile], [false, false, false]);
    assert.equal(classifyFrame(0, null).present, false);
  },
  "summarize: too few frames returns null"() {
    assert.equal(summarize([{ t: 0, present: true, contact: true, smile: false, yaw: 0, pitch: 0 }]), null);
  },
};

// frames every 400 ms; `away` lists indices without eye contact, `absent` lists indices with no face
const frames = (n, { away = [], absent = [], smile = [] } = {}) =>
  Array.from({ length: n }, (_, i) => ({
    t: i * 400, present: !absent.includes(i), contact: !away.includes(i) && !absent.includes(i),
    smile: smile.includes(i), yaw: 0, pitch: 0,
  }));

Object.assign(tests, {
  "summarize: steady attentive answer"() {
    const s = summarize(frames(20));
    assert.deepEqual([s.frames, s.face_present_pct, s.eye_contact_pct, s.look_away_events], [20, 100, 100, 0]);
  },
  "summarize: percentages"() {
    const s = summarize(frames(20, { away: [0, 1, 2, 3, 4], smile: [10, 11, 12, 13, 14] }));
    assert.equal(s.eye_contact_pct, 75);
    assert.equal(s.smile_pct, 25);
  },
  "summarize: a look-away must last a second to count"() {
    assert.equal(summarize(frames(20, { away: [5, 6] })).look_away_events, 0);          // 0.8 s
    assert.equal(summarize(frames(20, { away: [5, 6, 7] })).look_away_events, 1);       // 1.2 s
    assert.equal(summarize(frames(20, { away: [2, 3, 4, 10, 11, 12] })).look_away_events, 2);
  },
  "summarize: absent face lowers presence and contact"() {
    const s = summarize(frames(10, { absent: [0, 1, 2, 3, 4] }));
    assert.deepEqual([s.face_present_pct, s.eye_contact_pct], [50, 50]);
  },
  "summarize: head motion is the spread of the head angles"() {
    const still = summarize(frames(10));
    const moving = summarize(frames(10).map((f, i) => ({ ...f, yaw: i % 2 ? 10 : -10 })));
    assert.equal(still.head_motion, 0);
    near(moving.head_motion, 10, 0.1);
  },
});

let failed = 0;
for (const [name, fn] of Object.entries(tests)) {
  try { fn(); console.log("ok  ", name); } catch (e) { failed++; console.log("FAIL", name, "\n    ", e.message); }
}
console.log(failed ? `${failed} failed` : `${Object.keys(tests).length} tests passed`);
process.exit(failed ? 1 : 0);
