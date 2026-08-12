import {
  Fragment,
  jsx as reactJsx,
  jsxs as reactJsxs,
  type JSX,
} from "react/jsx-runtime";

import { resolveLocalizedText } from "./translate";

function localizedProps(props: unknown): unknown {
  if (props === null || typeof props !== "object") return props;
  const source = props as Record<string, unknown>;
  let changed = false;
  const localized: Record<string, unknown> = {};
  for (const [name, value] of Object.entries(source)) {
    const nextValue = localizedValue(value);
    localized[name] = nextValue;
    if (nextValue !== value) changed = true;
  }
  return changed ? localized : props;
}

function localizedValue(value: unknown): unknown {
  if (typeof value === "string") return resolveLocalizedText(value);
  if (Array.isArray(value)) {
    const localized = value.map(localizedValue);
    return localized.some((item, index) => item !== value[index]) ? localized : value;
  }
  return value;
}

export const jsx: typeof reactJsx = (type, props, key) =>
  reactJsx(type, localizedProps(props), key);
export const jsxs: typeof reactJsxs = (type, props, key) =>
  reactJsxs(type, localizedProps(props), key);
export { Fragment };
export type { JSX };
