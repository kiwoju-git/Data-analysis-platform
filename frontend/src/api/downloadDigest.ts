/** Hash downloaded bytes in both secure and trusted HTTP LAN browser contexts. */
export async function downloadSha256(bytes: ArrayBuffer): Promise<string> {
  const subtle = globalThis.crypto?.subtle;
  const digest = typeof subtle?.digest === "function"
    ? new Uint8Array(await subtle.digest("SHA-256", bytes))
    : (await import("@noble/hashes/sha2.js")).sha256(new Uint8Array(bytes));
  return Array.from(digest, (value) => value.toString(16).padStart(2, "0")).join("");
}
