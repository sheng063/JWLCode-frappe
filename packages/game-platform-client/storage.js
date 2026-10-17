// Colyseus 0.18.5 Auth reads storage during Client construction. Opaque-origin
// iframes cannot use localStorage or IndexedDB. Never persist platform tickets.
const memory = new Map();
export function getItem(key, callback) { callback(memory.get(key)); }
export function setItem(key, value) { memory.set(key, value); }
export function removeItem(key) { memory.delete(key); }
