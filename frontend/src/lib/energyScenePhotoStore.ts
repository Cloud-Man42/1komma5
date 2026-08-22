const DB_NAME = "energy-scene";
const DB_VERSION = 1;
const STORE = "assets";
const PHOTO_KEY = "custom-photo";

function hasIndexedDb(): boolean {  return typeof indexedDB !== "undefined";
}

function openDb(): Promise<IDBDatabase> {
  if (!hasIndexedDb()) {
    return Promise.reject(new Error("IndexedDB is not available"));
  }

  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onerror = () => reject(request.error ?? new Error("Could not open scene photo store"));
    request.onupgradeneeded = () => {
      request.result.createObjectStore(STORE);
    };
    request.onsuccess = () => resolve(request.result);
  });
}

export async function saveCustomScenePhoto(dataUrl: string): Promise<void> {
  if (!hasIndexedDb()) return;
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error ?? new Error("Could not save custom scene photo"));
    tx.objectStore(STORE).put(dataUrl, PHOTO_KEY);
  });
  db.close();
}

export async function loadCustomScenePhoto(): Promise<string | null> {
  if (!hasIndexedDb()) return null;
  const db = await openDb();
  const photo = await new Promise<string | null>((resolve, reject) => {
    const tx = db.transaction(STORE, "readonly");
    const request = tx.objectStore(STORE).get(PHOTO_KEY);
    request.onerror = () => reject(request.error ?? new Error("Could not load custom scene photo"));
    request.onsuccess = () => resolve(typeof request.result === "string" ? request.result : null);
  });
  db.close();
  return photo;
}

export async function clearCustomScenePhoto(): Promise<void> {
  if (!hasIndexedDb()) return;
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error ?? new Error("Could not clear custom scene photo"));
    tx.objectStore(STORE).delete(PHOTO_KEY);
  });
  db.close();
}
