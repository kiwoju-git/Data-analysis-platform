export const appLocationChangeEvent = "datalab:location-change";

export function pushAppLocation(path: string): void {
  if (typeof window === "undefined") return;
  window.history.pushState(null, "", path);
  window.dispatchEvent(new Event(appLocationChangeEvent));
}

export function replaceAppLocation(path: string): void {
  if (typeof window === "undefined") return;
  window.history.replaceState(null, "", path);
  window.dispatchEvent(new Event(appLocationChangeEvent));
}
