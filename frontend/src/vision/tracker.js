// Camera + MediaPipe FaceLandmarker, running entirely in the browser.
// Video frames are analysed locally and thrown away; only a handful of summary numbers are sent to the server.
import { classifyFrame, summarize } from "./metrics.js";

const WASM_DIR = "/mediapipe/wasm";                       // copied from node_modules by scripts/copy-mediapipe.mjs
const MODEL_LOCAL = "/models/face_landmarker.task";       // shipped in public/, so the demo needs no internet
const MODEL_CDN = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task";
const SAMPLE_MS = 400;

export class FaceTracker {
  constructor() {
    this.landmarker = null;
    this.stream = null;
    this.video = null;
    this.timer = null;
    this.frames = [];
    this.active = false;
  }

  /** Opens the camera, loads the model, starts sampling. Throws if the camera is blocked or no model loads. */
  async start(videoEl) {
    this.stream = await navigator.mediaDevices.getUserMedia({ video: { width: 320, height: 240, facingMode: "user" }, audio: false });
    this.video = videoEl;
    videoEl.srcObject = this.stream;
    await videoEl.play();

    const { FaceLandmarker, FilesetResolver } = await import("@mediapipe/tasks-vision");
    const fileset = await FilesetResolver.forVisionTasks(WASM_DIR);
    const create = (modelAssetPath, delegate) => FaceLandmarker.createFromOptions(fileset, {
      baseOptions: { modelAssetPath, delegate },
      runningMode: "VIDEO", numFaces: 1, outputFaceBlendshapes: true, outputFacialTransformationMatrixes: true,
    });
    let lastError;
    for (const [model, delegate] of [[MODEL_LOCAL, "GPU"], [MODEL_LOCAL, "CPU"], [MODEL_CDN, "CPU"]]) {
      try { this.landmarker = await create(model, delegate); break; } catch (e) { lastError = e; }
    }
    if (!this.landmarker) throw lastError || new Error("Face model failed to load");
    this.timer = setInterval(() => this._sample(), SAMPLE_MS);
  }

  _sample() {
    if (!this.active || !this.landmarker || !this.video || this.video.readyState < 2) return;
    try {
      const now = performance.now();
      this.frames.push(classifyFrame(now, this.landmarker.detectForVideo(this.video, now)));
    } catch { /* one bad frame is not worth surfacing */ }
  }

  /** Start (true) or pause (false) collecting frames. Turning it on clears the previous answer's frames. */
  setActive(on) {
    this.active = on;
    if (on) this.frames = [];
  }

  /** Summary of the frames collected since setActive(true), or null if there were too few. */
  takeSummary() {
    const s = summarize(this.frames);
    this.frames = [];
    return s;
  }

  stop() {
    clearInterval(this.timer);
    this.active = false;
    this.stream?.getTracks().forEach((t) => t.stop());
    try { this.landmarker?.close(); } catch { /* already closed */ }
    if (this.video) this.video.srcObject = null;
    this.landmarker = this.stream = this.video = null;
  }
}
