import ts from "typescript";
import type { Plugin } from "vite";

const marker = (key: string) => `\uE000${key}\uE001`;
const hangulPattern = /[\uac00-\ud7a3]/u;

function normalize(value: string): string {
  return value.replace(/\s+/gu, " ").trim();
}

function replaceFragment(value: string, sourceToKey: Readonly<Record<string, string>>): string {
  const normalized = normalize(value);
  if (!hangulPattern.test(normalized)) return value;
  const key = sourceToKey[normalized];
  if (key === undefined) return value;
  const start = value.indexOf(value.trimStart());
  const end = value.length - value.trimEnd().length;
  return `${value.slice(0, start)}${marker(key)}${end === 0 ? "" : value.slice(-end)}`;
}

export function createLocalizationPlugin(
  sourceToKey: Readonly<Record<string, string>>,
): Plugin {
  return {
    name: "statistical-twin-localization",
    enforce: "pre",
    transform(code, id) {
      const normalizedId = id.replace(/\\/gu, "/").split("?", 1)[0];
      if (
        !normalizedId.includes("/frontend/src/") ||
        normalizedId.includes("/frontend/src/i18n/") ||
        normalizedId.includes(".test.") ||
        !/\.(?:ts|tsx)$/u.test(normalizedId)
      ) {
        return null;
      }
      const sourceFile = ts.createSourceFile(
        normalizedId,
        code,
        ts.ScriptTarget.Latest,
        true,
        normalizedId.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS,
      );
      const transformer: ts.TransformerFactory<ts.SourceFile> = (context) => {
        const visit: ts.Visitor = (node) => {
          if (ts.isJsxText(node)) {
            const next = replaceFragment(node.text, sourceToKey);
            return next === node.text ? node : context.factory.createJsxText(next, false);
          }
          if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) {
            const parent = node.parent;
            const isPropertyName =
              (ts.isPropertyAssignment(parent) || ts.isPropertyDeclaration(parent)) &&
              parent.name === node;
            const isModuleSpecifier =
              (ts.isImportDeclaration(parent) || ts.isExportDeclaration(parent)) &&
              parent.moduleSpecifier === node;
            if (!isPropertyName && !isModuleSpecifier) {
              const next = replaceFragment(node.text, sourceToKey);
              if (next !== node.text) return context.factory.createStringLiteral(next);
            }
          }
          if (ts.isTemplateExpression(node)) {
            const headText = replaceFragment(node.head.text, sourceToKey);
            const head =
              headText === node.head.text
                ? node.head
                : context.factory.createTemplateHead(headText, headText);
            const spans = node.templateSpans.map((span) => {
              const expression = ts.visitNode(span.expression, visit) as ts.Expression;
              const literalText = replaceFragment(span.literal.text, sourceToKey);
              const literal =
                literalText === span.literal.text
                  ? span.literal
                  : ts.isTemplateTail(span.literal)
                    ? context.factory.createTemplateTail(literalText, literalText)
                    : context.factory.createTemplateMiddle(literalText, literalText);
              return context.factory.updateTemplateSpan(span, expression, literal);
            });
            return context.factory.updateTemplateExpression(node, head, spans);
          }
          return ts.visitEachChild(node, visit, context);
        };
        return (node) => ts.visitNode(node, visit) as ts.SourceFile;
      };
      const result = ts.transform(sourceFile, [transformer]);
      const output = ts.createPrinter().printFile(result.transformed[0]);
      result.dispose();
      return { code: output, map: null };
    },
  };
}
