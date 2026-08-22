/**
 * Build photorealistic energy scene: base photo + programmatic conduit overlay + path JSON.
 * Run: node scripts/generate-energy-scene.mjs [path-to-base.png]
 */
import fs from "node:fs";
import path from "node:path";
import { PNG } from "pngjs";
import {
  CABLE_PATHS,
  VIEW_H,
  VIEW_W,
  pathsToGeneratedJson,
} from "./energy-scene-spec.mjs";

const OUT_W = 1536;
const OUT_H = 1024;
const OUT_IMAGE = "public/energy-scene-photo.png";
const OUT_MASK = "public/energy-scene-cable-mask.png";
const OUT_PATHS = "src/lib/energyFlowPaths.generated.json";

const DEFAULT_BASE = path.resolve("assets/energy-scene-base.png");

function loadPng(filePath) {
  return PNG.sync.read(fs.readFileSync(filePath));
}

function normToPx(x, y) {
  return {
    x: Math.round((x / VIEW_W) * OUT_W),
    y: Math.round((y / VIEW_H) * OUT_H),
  };
}

/** Center-crop source to 3:2, then scale to OUT_W x OUT_H. */
function cropToScene(src) {
  const targetRatio = OUT_W / OUT_H;
  const srcRatio = src.width / src.height;
  let cropX = 0;
  let cropY = 0;
  let cropW = src.width;
  let cropH = src.height;

  if (srcRatio > targetRatio) {
    cropW = Math.round(src.height * targetRatio);
    cropX = Math.round((src.width - cropW) / 2);
  } else if (srcRatio < targetRatio) {
    cropH = Math.round(src.width / targetRatio);
    cropY = Math.round((src.height - cropH) / 2);
  }

  const dst = new PNG({ width: OUT_W, height: OUT_H });
  for (let dy = 0; dy < OUT_H; dy++) {
    for (let dx = 0; dx < OUT_W; dx++) {
      const sx = cropX + Math.floor((dx / OUT_W) * cropW);
      const sy = cropY + Math.floor((dy / OUT_H) * cropH);
      const si = (sy * src.width + sx) * 4;
      const di = (dy * OUT_W + dx) * 4;
      dst.data[di] = src.data[si];
      dst.data[di + 1] = src.data[si + 1];
      dst.data[di + 2] = src.data[si + 2];
      dst.data[di + 3] = 255;
    }
  }
  return dst;
}

function setPx(img, x, y, r, g, b, a = 255) {
  if (x < 0 || y < 0 || x >= img.width || y >= img.height) return;
  const i = (y * img.width + x) * 4;
  if (a >= 255) {
    img.data[i] = r;
    img.data[i + 1] = g;
    img.data[i + 2] = b;
    img.data[i + 3] = 255;
    return;
  }
  const alpha = a / 255;
  img.data[i] = Math.round(img.data[i] * (1 - alpha) + r * alpha);
  img.data[i + 1] = Math.round(img.data[i + 1] * (1 - alpha) + g * alpha);
  img.data[i + 2] = Math.round(img.data[i + 2] * (1 - alpha) + b * alpha);
}

function drawDisc(img, cx, cy, radius, r, g, b, a = 255) {
  const r2 = radius * radius;
  for (let y = cy - radius; y <= cy + radius; y++) {
    for (let x = cx - radius; x <= cx + radius; x++) {
      const dx = x - cx;
      const dy = y - cy;
      if (dx * dx + dy * dy <= r2) setPx(img, x, y, r, g, b, a);
    }
  }
}

function drawSegment(img, a, b, radius, core, highlight, shadow) {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const len = Math.hypot(dx, dy);
  if (len < 1) return;
  const steps = Math.max(Math.ceil(len * 2.5), 3);
  const nx = -dy / len;
  const ny = dx / len;

  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const cx = a.x + dx * t;
    const cy = a.y + dy * t;
    drawDisc(img, Math.round(cx + nx * 1.5 + 1.5), Math.round(cy + ny * 1.5 + 1.5), radius + 2, ...shadow, 70);
    drawDisc(img, cx, cy, radius + 1, ...shadow, 110);
    drawDisc(img, cx, cy, radius, ...core);
    drawDisc(img, Math.round(cx - nx * 1.0), Math.round(cy - ny * 1.0), Math.max(1, radius - 2), ...highlight, 180);
  }

  drawDisc(img, a.x, a.y, radius + 3, ...shadow, 100);
  drawDisc(img, a.x, a.y, radius + 2, ...core);
  drawDisc(img, b.x, b.y, radius + 3, ...shadow, 100);
  drawDisc(img, b.x, b.y, radius + 2, ...core);
}

function drawBracket(img, x, y, radius) {
  const w = radius + 4;
  for (let dy = -w; dy <= w; dy++) {
    for (let dx = -w; dx <= w; dx++) {
      if (Math.abs(dx) <= w - 2 || Math.abs(dy) <= w - 2) {
        setPx(img, x + dx, y + dy, 95, 98, 102, 220);
      }
    }
  }
}

function drawConduit(img, points, { radius = 6, lawn = false } = {}) {
  const pxPts = points.map((p) => normToPx(p.x, p.y));
  const core = lawn ? [36, 40, 34] : [48, 50, 54];
  const highlight = lawn ? [68, 74, 66] : [128, 132, 138];
  const shadow = lawn ? [16, 20, 14] : [18, 20, 24];

  for (let i = 0; i < pxPts.length - 1; i++) {
    drawSegment(img, pxPts[i], pxPts[i + 1], radius, core, highlight, shadow);
  }
  for (const p of pxPts) {
    drawBracket(img, p.x, p.y, radius);
  }
}

function drawMask(mask, points) {
  const pxPts = points.map((p) => normToPx(p.x, p.y));
  for (let i = 0; i < pxPts.length - 1; i++) {
    drawSegment(
      mask,
      pxPts[i],
      pxPts[i + 1],
      4,
      [0, 0, 0],
      [0, 0, 0],
      [0, 0, 0],
    );
  }
}

const basePath = process.argv[2] ?? DEFAULT_BASE;
if (!fs.existsSync(basePath)) {
  console.error("Base image not found:", basePath);
  process.exit(1);
}

console.log("Loading base:", basePath);
const base = loadPng(basePath);
const scene = cropToScene(base);

for (const [id, points] of Object.entries(CABLE_PATHS)) {
  drawConduit(scene, points, { lawn: id === "grid-lawn", radius: id === "grid-lawn" ? 6 : 5 });
}

const mask = new PNG({ width: OUT_W, height: OUT_H });
for (let i = 0; i < mask.data.length; i += 4) {
  mask.data[i] = 255;
  mask.data[i + 1] = 255;
  mask.data[i + 2] = 255;
  mask.data[i + 3] = 255;
}
for (const points of Object.values(CABLE_PATHS)) {
  drawMask(mask, points);
}

fs.writeFileSync(OUT_IMAGE, PNG.sync.write(scene));
fs.writeFileSync(OUT_MASK, PNG.sync.write(mask));
fs.writeFileSync(OUT_PATHS, JSON.stringify(pathsToGeneratedJson(), null, 2));

console.log("Wrote", OUT_IMAGE, `${OUT_W}x${OUT_H}`);
console.log("Wrote", OUT_MASK);
console.log("Wrote", OUT_PATHS);
for (const [id, pts] of Object.entries(CABLE_PATHS)) {
  console.log(`  ${id}: ${pts.length} pts`);
}
