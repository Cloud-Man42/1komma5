import fs from "node:fs";
import { PNG } from "pngjs";

const buf = fs.readFileSync("public/energy-scene-photo.png");
const png = PNG.sync.read(buf);
const { width: w, height: h, data } = png;

function isConduit(x, y) {
  const i = (w * y + x) * 4;
  const r = data[i];
  const g = data[i + 1];
  const b = data[i + 2];
  const lum = 0.299 * r + 0.587 * g + 0.114 * b;
  return lum < 88 && Math.max(r, g, b) - Math.min(r, g, b) < 35;
}

function n(x, y) {
  return { x: Number(((x / w) * 100).toFixed(2)), y: Number(((y / h) * 66.6667).toFixed(2)) };
}

// Find thin horizontal conduit rows (small span)
console.log("THIN HORIZONTAL (span 15-120px) y 400-560");
for (let y = 400; y <= 560; y += 2) {
  const xs = [];
  for (let x = Math.floor(w * 0.36); x < Math.floor(w * 0.58); x++) {
    if (isConduit(x, y)) xs.push(x);
  }
  if (xs.length < 15 || xs.length > 120) continue;
  xs.sort((a, b) => a - b);
  console.log(`y=${n(0, y).y} left=${n(xs[0], y).x} right=${n(xs[xs.length - 1], y).x} len=${xs.length}`);
}

console.log("\nGRID DOWN x 670-730 y 540-720");
for (let y = 540; y <= 720; y += 4) {
  let best = null;
  let count = 0;
  for (let x = 670; x <= 730; x++) {
    if (isConduit(x, y)) {
      count++;
      best = x;
    }
  }
  if (count >= 3) console.log(n(best, y));
}

console.log("\nSOLAR full vertical");
for (let y = 150; y <= 340; y += 5) {
  let best = null;
  let count = 0;
  for (let x = 660; x <= 710; x++) if (isConduit(x, y)) { count++; best = x; }
  if (count >= 2) console.log(n(best, y));
}

console.log("\nINVERTER DROP x 760-810 y 480-560");
for (let y = 480; y <= 560; y += 3) {
  let best = null;
  let count = 0;
  for (let x = 760; x <= 810; x++) if (isConduit(x, y)) { count++; best = x; }
  if (count >= 2) console.log(n(best, y));
}

console.log("\nBATTERY DROP x 600-650 y 480-560");
for (let y = 480; y <= 560; y += 3) {
  let best = null;
  let count = 0;
  for (let x = 600; x <= 650; x++) if (isConduit(x, y)) { count++; best = x; }
  if (count >= 2) console.log(n(best, y));
}
