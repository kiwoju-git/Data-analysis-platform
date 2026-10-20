export async function copyDoeEquation(
  text: string,
  clipboard: () => Pick<Clipboard, "writeText"> | undefined = () =>
    typeof navigator === "undefined" ? undefined : navigator.clipboard,
): Promise<boolean> {
  try {
    const target = clipboard();
    if (!target || typeof target.writeText !== "function") return false;
    await target.writeText(text);
    return true;
  } catch {
    return false;
  }
}
