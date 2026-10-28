// Copies MediaPipe's WASM runtime from node_modules into public/, so the face tracker loads from this
// site instead of a CDN (the demo then works on a slow or offline network). Runs on `npm install`.
import { cpSync, existsSync, mkdirSync } from "node:fs";

const from = "node_modules/@mediapipe/tasks-vision/wasm";
const to = "public/mediapipe/wasm";
if (!existsSync(from)) {
  console.warn("copy-mediapipe: package not installed yet, skipping");
} else {
  mkdirSync(to, { recursive: true });
  cpSync(from, to, { recursive: true });
  console.log("copy-mediapipe: wasm copied to", to);
}
