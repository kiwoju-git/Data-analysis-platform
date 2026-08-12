import {
  Fragment,
  jsxDEV as reactJsxDEV,
  type JSX,
} from "react/jsx-dev-runtime";

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

export const jsxDEV: typeof reactJsxDEV = (
  type,
  props,
  key,
  isStaticChildren,
  source,
  self,
) => reactJsxDEV(type, localizedProps(props), key, isStaticChildren, source, self);
export { Fragment };
export type { JSX };
