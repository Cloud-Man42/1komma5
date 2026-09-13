import fs from "node:fs";
import path from "node:path";
import sharp from "sharp";

const OUT_DIR = path.join(process.cwd(), "public", "icons");
const SOURCE = path.join(OUT_DIR, "emic-logo-source.png");

async function main() {
  if (!fs.existsSync(SOURCE)) {
    throw new Error(`Missing logo source: ${SOURCE}`);
  }

  fs.mkdirSync(OUT_DIR, { recursive: true });

  const sizes = [
    { size: 512, name: "emic-icon-512.png" },
    { size: 192, name: "emic-icon-192.png" },
    { size: 32, name: "favicon.png" },
  ];

  for (const { size, name } of sizes) {
    const file = path.join(OUT_DIR, name);
    await sharp(SOURCE)
      .resize(size, size, { fit: "cover", position: "centre" })
      .png({ compressionLevel: 9 })
      .toFile(file);
    console.log(`Wrote ${file}`);
  }

  const logo = path.join(OUT_DIR, "emic-logo.png");
  await sharp(SOURCE)
    .resize(640, 640, { fit: "inside", withoutEnlargement: true })
    .png({ compressionLevel: 9 })
    .toFile(logo);
  console.log(`Wrote ${logo}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
