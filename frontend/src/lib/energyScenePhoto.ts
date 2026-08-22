import { SCENE_VIEW_H, SCENE_VIEW_W } from "./energySceneCoords";

export const DEFAULT_SCENE_PHOTO = "/energy-scene-photo.png";
export const SCENE_ASPECT = SCENE_VIEW_W / SCENE_VIEW_H;
export const SCENE_PHOTO_WIDTH = 1536;
export const SCENE_PHOTO_HEIGHT = 1024;

export async function cropPhotoToScene(file: File, quality = 0.82): Promise<string> {
  const bitmap = await loadImageFromFile(file);
  const canvas = document.createElement("canvas");
  canvas.width = SCENE_PHOTO_WIDTH;
  canvas.height = SCENE_PHOTO_HEIGHT;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas not supported");

  const sourceAspect = bitmap.width / bitmap.height;
  let sx = 0;
  let sy = 0;
  let sw = bitmap.width;
  let sh = bitmap.height;

  if (sourceAspect > SCENE_ASPECT) {
    sw = bitmap.height * SCENE_ASPECT;
    sx = (bitmap.width - sw) / 2;
  } else {
    sh = bitmap.width / SCENE_ASPECT;
    sy = (bitmap.height - sh) / 2;
  }

  ctx.drawImage(bitmap, sx, sy, sw, sh, 0, 0, SCENE_PHOTO_WIDTH, SCENE_PHOTO_HEIGHT);
  return canvas.toDataURL("image/jpeg", quality);
}

function loadImageFromFile(file: File): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      URL.revokeObjectURL(url);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Could not load image"));
    };
    image.src = url;
  });
}

export function isCustomPhotoUrl(url: string | null | undefined): boolean {
  return Boolean(url && url.startsWith("data:image/"));
}
