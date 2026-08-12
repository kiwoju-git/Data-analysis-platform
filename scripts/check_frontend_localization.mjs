import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import ts from "../frontend/node_modules/typescript/lib/typescript.js";

const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/(?:[A-Za-z]:)/, (value) => value.slice(1))), "..");
const frontendRoot = path.join(repoRoot, "frontend", "src");
const catalogPath = path.join(frontendRoot, "i18n", "catalog.generated.json");
const hangulPattern = /[\uac00-\ud7a3]/u;

export function localizationKeyForSource(source) {
  return `ui.${crypto.createHash("sha256").update(source, "utf8").digest("hex").slice(0, 16)}`;
}

function localizableFragment(value) {
  const trimmed = value.replace(/\s+/gu, " ").trim();
  return hangulPattern.test(trimmed) ? trimmed : null;
}

function sourceFiles(directory) {
  const files = [];
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      if (entry.name !== "i18n") files.push(...sourceFiles(absolute));
      continue;
    }
    if (!/\.(?:ts|tsx)$/u.test(entry.name) || entry.name.includes(".test.")) continue;
    files.push(absolute);
  }
  return files;
}

export function collectLocalizableSources() {
  const sources = new Map();
  for (const filename of sourceFiles(frontendRoot)) {
    const sourceText = fs.readFileSync(filename, "utf8");
    const sourceFile = ts.createSourceFile(
      filename,
      sourceText,
      ts.ScriptTarget.Latest,
      true,
      filename.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS,
    );
    function record(value, kind) {
      const source = localizableFragment(value);
      if (source === null) return;
      const recordValue = sources.get(source) ?? { files: new Set(), kinds: new Set() };
      recordValue.files.add(path.relative(repoRoot, filename).replaceAll("\\", "/"));
      recordValue.kinds.add(kind);
      sources.set(source, recordValue);
    }
    function visit(node) {
      if (ts.isJsxText(node)) {
        record(node.text, "jsx_text");
      } else if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) {
        const parent = node.parent;
        const isPropertyName =
          (ts.isPropertyAssignment(parent) || ts.isPropertyDeclaration(parent)) &&
          parent.name === node;
        const isModuleSpecifier =
          (ts.isImportDeclaration(parent) || ts.isExportDeclaration(parent)) &&
          parent.moduleSpecifier === node;
        if (!isPropertyName && !isModuleSpecifier) record(node.text, "string");
      } else if (
        ts.isTemplateHead(node) ||
        ts.isTemplateMiddle(node) ||
        ts.isTemplateTail(node)
      ) {
        record(node.text, "template_fragment");
      }
      ts.forEachChild(node, visit);
    }
    visit(sourceFile);
  }
  return new Map(
    [...sources.entries()].sort(([left], [right]) => left.localeCompare(right, "ko")),
  );
}

function placeholders(value) {
  return [...value.matchAll(/\{([A-Za-z][A-Za-z0-9_]*)\}/gu)]
    .map((match) => match[1])
    .sort();
}

function sameItems(left, right) {
  return left.length === right.length && left.every((value, index) => value === right[index]);
}

function runCheck() {
  if (!fs.existsSync(catalogPath)) {
    throw new Error(`Localization catalog is missing: ${catalogPath}`);
  }
  const catalog = JSON.parse(fs.readFileSync(catalogPath, "utf8"));
  const enKeys = Object.keys(catalog.en).sort();
  const koKeys = Object.keys(catalog.ko).sort();
  if (!sameItems(enKeys, koKeys)) {
    throw new Error("English and Korean localization keys do not match.");
  }
  for (const key of enKeys) {
    const english = catalog.en[key];
    const korean = catalog.ko[key];
    if (typeof english !== "string" || english.trim() === "") {
      throw new Error(`English translation is empty: ${key}`);
    }
    if (typeof korean !== "string" || korean.trim() === "") {
      throw new Error(`Korean translation is empty: ${key}`);
    }
    if (!sameItems(placeholders(english), placeholders(korean))) {
      throw new Error(`Translation placeholders do not match: ${key}`);
    }
    if (hangulPattern.test(english)) {
      throw new Error(`English translation still contains Hangul: ${key}`);
    }
  }
  const sources = collectLocalizableSources();
  const rawBackendMessageFiles = sourceFiles(frontendRoot)
    .filter((filename) => !filename.replaceAll("\\", "/").endsWith("/api/client.ts"))
    .filter((filename) => fs.readFileSync(filename, "utf8").includes("backendMessage"));
  const missing = [...sources.keys()].filter((source) => catalog.sourceToKey[source] === undefined);
  const invalidMappings = Object.entries(catalog.sourceToKey).filter(
    ([, key]) => catalog.en[key] === undefined || catalog.ko[key] === undefined,
  );
  const orphanMappings = Object.keys(catalog.sourceToKey).filter(
    (source) => !sources.has(source),
  );
  if (missing.length > 0) {
    const preview = missing.slice(0, 20).map((source) => JSON.stringify(source)).join("\n  ");
    throw new Error(`Unregistered user-facing Korean strings (${missing.length}):\n  ${preview}`);
  }
  if (invalidMappings.length > 0) {
    throw new Error(`Localization source mappings reference unknown keys: ${invalidMappings.length}`);
  }
  if (orphanMappings.length > 0) {
    throw new Error(`Localization source mappings are no longer used: ${orphanMappings.length}`);
  }
  if (rawBackendMessageFiles.length > 0) {
    throw new Error(
      `Raw backend messages may only be handled at the API localization boundary:\n  ${rawBackendMessageFiles.join("\n  ")}`,
    );
  }
  console.log(
    `Verified ${sources.size} localized frontend source strings and ${enKeys.length} translation keys.`,
  );
}

function writeInventory(target) {
  const sources = collectLocalizableSources();
  const inventory = [...sources.entries()].map(([source, metadata]) => ({
    key: localizationKeyForSource(source),
    source,
    files: [...metadata.files],
    kinds: [...metadata.kinds],
  }));
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, `${JSON.stringify(inventory, null, 2)}\n`, "utf8");
  console.log(`Wrote ${inventory.length} localization inventory entries to ${target}`);
}

const inventoryIndex = process.argv.indexOf("--write-inventory");
if (inventoryIndex >= 0) {
  const requested = process.argv[inventoryIndex + 1];
  if (!requested) throw new Error("--write-inventory requires a path");
  writeInventory(path.resolve(repoRoot, requested));
} else {
  runCheck();
}
