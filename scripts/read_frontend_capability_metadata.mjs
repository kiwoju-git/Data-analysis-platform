import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(resolve(repositoryRoot, "frontend/package.json"));
const ts = require("typescript");

function unwrap(node) {
  while (ts.isAsExpression(node) || ts.isSatisfiesExpression(node) || ts.isParenthesizedExpression(node)) {
    node = node.expression;
  }
  return node;
}

function propertyName(node) {
  if (ts.isIdentifier(node) || ts.isStringLiteral(node)) return node.text;
  throw new Error("capability_frontend_computed_key");
}

export function readLiteralExpression(expression) {
  const node = unwrap(expression);
  if (ts.isStringLiteral(node)) return node.text;
  if (ts.isNumericLiteral(node)) return Number(node.text);
  if (node.kind === ts.SyntaxKind.TrueKeyword) return true;
  if (node.kind === ts.SyntaxKind.FalseKeyword) return false;
  if (node.kind === ts.SyntaxKind.NullKeyword) return null;
  if (ts.isArrayLiteralExpression(node)) return node.elements.map(readLiteralExpression);
  if (ts.isObjectLiteralExpression(node)) {
    const result = Object.create(null);
    for (const property of node.properties) {
      if (!ts.isPropertyAssignment(property)) throw new Error("capability_frontend_nonliteral_property");
      const key = propertyName(property.name);
      if (Object.hasOwn(result, key)) throw new Error("capability_frontend_duplicate_key");
      result[key] = readLiteralExpression(property.initializer);
    }
    return result;
  }
  throw new Error("capability_frontend_nonliteral_value");
}

export function findInitializer(source, name, filename = "fixture.ts") {
  const tree = ts.createSourceFile(filename, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  if (tree.parseDiagnostics.length) throw new Error("capability_frontend_parse_error");
  const matches = [];
  for (const statement of tree.statements) {
    if (!ts.isVariableStatement(statement)) continue;
    for (const declaration of statement.declarationList.declarations) {
      if (ts.isIdentifier(declaration.name) && declaration.name.text === name && declaration.initializer) {
        matches.push(declaration.initializer);
      }
    }
  }
  if (matches.length !== 1) throw new Error("capability_frontend_declaration_missing_or_duplicate");
  return unwrap(matches[0]);
}

export function readGuidanceIds(source) {
  const node = findInitializer(source, "analysisMethodGuidance");
  if (!ts.isObjectLiteralExpression(node)) throw new Error("capability_frontend_guidance_shape");
  const ids = node.properties.map((property) => {
    if (!ts.isPropertyAssignment(property)) throw new Error("capability_frontend_guidance_property");
    return propertyName(property.name);
  });
  if (new Set(ids).size !== ids.length) throw new Error("capability_frontend_duplicate_guidance");
  return ids;
}

export function readFrontendMetadata(root = repositoryRoot) {
  const source = (file) => readFileSync(resolve(root, "frontend/src", file), "utf8");
  const domains = readLiteralExpression(findInitializer(source("analysisDomains.ts"), "ANALYSIS_DOMAINS"));
  const guidance_method_ids = readGuidanceIds(source("analysisMethodGuidance.ts"));
  return { domains, guidance_method_ids };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    if (process.argv.length > 3) throw new Error("capability_frontend_arguments_invalid");
    process.stdout.write(`${JSON.stringify(readFrontendMetadata(process.argv[2]))}\n`);
  } catch (error) {
    process.stderr.write(`${error instanceof Error ? error.message : "capability_frontend_read_failed"}\n`);
    process.exitCode = 1;
  }
}
