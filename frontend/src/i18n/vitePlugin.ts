import ts from "typescript";
import type { Plugin } from "vite";

const hangulPattern = /[\uac00-\ud7a3]/u;
const displayAttributes = new Set([
  "title", "aria-label", "aria-description", "placeholder", "alt",
  "label", "description", "emptyLabel", "heading", "subtitle",
  "xLabel", "yLabel", "valueLabel", "chartTitle", "ariaLabel", "summary", "annotations",
  "helper", "summaryText", "preflightButtonLabel", "buttonLabel",
]);
const displayCollections: Readonly<Record<string, ReadonlySet<string>>> = {
  DoeSettingsTable: new Set(["fields"]),
  DefinitionRows: new Set(["rows"]),
};
const componentDisplayAttributes: Readonly<Record<string, ReadonlySet<string>>> = {
  HomeQuickCard: new Set(["action", "detail"]),
  ProjectResource: new Set(["loadingLabel"]),
  ExportFormatAction: new Set(["unsupportedReason"]),
  ExportStatus: new Set(["sizeText"]),
};

function normalize(value: string): string {
  return value.replace(/\s+/gu, " ").trim();
}

function isDisplayAttribute(node: ts.JsxAttribute): boolean {
  if (!ts.isIdentifier(node.name)) return false;
  if (displayAttributes.has(node.name.text)) return true;
  const element = node.parent.parent;
  return (ts.isJsxOpeningElement(element) || ts.isJsxSelfClosingElement(element))
    && ts.isIdentifier(element.tagName)
    && (componentDisplayAttributes[element.tagName.text]?.has(node.name.text) ?? false);
}

function isDeclaredCollectionLabel(node: ts.Node): boolean {
  let ancestor = node.parent;
  if (ts.isPropertyAssignment(ancestor)) {
    if (!ts.isIdentifier(ancestor.name) || (!displayAttributes.has(ancestor.name.text) && ancestor.name.text !== "helper")
      || ancestor.initializer !== node) return false;
    ancestor = ancestor.parent;
  } else if (ts.isArrayLiteralExpression(ancestor)) {
    // DefinitionRows tuples have a presentation label at position zero only.
    if (ancestor.elements[0] !== node || !ts.isArrayLiteralExpression(ancestor.parent)) return false;
  } else return false;
  while (ts.isObjectLiteralExpression(ancestor) || ts.isArrayLiteralExpression(ancestor)
    || ts.isAsExpression(ancestor) || ts.isParenthesizedExpression(ancestor)
    || ts.isSpreadElement(ancestor)
    || (ts.isConditionalExpression(ancestor) && ancestor.condition !== node)) ancestor = ancestor.parent;
  if (!ts.isJsxExpression(ancestor) || !ts.isJsxAttribute(ancestor.parent)) return false;
  const attribute = ancestor.parent;
  const element = attribute.parent.parent;
  if ((!ts.isJsxOpeningElement(element) && !ts.isJsxSelfClosingElement(element))
    || !ts.isIdentifier(element.tagName) || !ts.isIdentifier(attribute.name)) return false;
  return displayCollections[element.tagName.text]?.has(attribute.name.text) ?? false;
}

// Follow value expressions only, never conditions, function arguments or objects.
function isDisplayExpression(node: ts.Node): boolean {
  if (isDeclaredCollectionLabel(node)) return true;
  const parent = node.parent;
  if (parent === undefined) return false;
  if (ts.isJsxExpression(parent)) {
    return ts.isJsxAttribute(parent.parent)
      ? isDisplayAttribute(parent.parent)
      : ts.isJsxElement(parent.parent) || ts.isJsxFragment(parent.parent);
  }
  if (ts.isConditionalExpression(parent)) {
    return parent.condition !== node && isDisplayExpression(parent);
  }
  if (ts.isBinaryExpression(parent)) {
    const operator = parent.operatorToken.kind;
    const valueOperand = operator === ts.SyntaxKind.PlusToken
      || (parent.right === node && (operator === ts.SyntaxKind.QuestionQuestionToken
        || operator === ts.SyntaxKind.BarBarToken || operator === ts.SyntaxKind.AmpersandAmpersandToken));
    return valueOperand && isDisplayExpression(parent);
  }
  if (ts.isArrayLiteralExpression(parent)) return isDisplayExpression(parent);
  if (ts.isTemplateSpan(parent) && parent.expression === node) return isDisplayExpression(parent.parent);
  return (ts.isParenthesizedExpression(parent) || ts.isAsExpression(parent)
    || ts.isNonNullExpression(parent)) && isDisplayExpression(parent);
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
        let translated = false;
        const factory = context.factory;
        const helper = factory.createUniqueName("__datalabUiText");
        const fragment = (value: string): ts.Expression => {
          const normalized = normalize(value);
          const key = hangulPattern.test(normalized) ? sourceToKey[normalized] : undefined;
          if (key === undefined) return factory.createStringLiteral(value);
          translated = true;
          let result: ts.Expression = factory.createCallExpression(helper, undefined, [factory.createStringLiteral(key)]);
          const leading = value.slice(0, value.length - value.trimStart().length);
          const trailing = value.slice(value.trimEnd().length);
          if (leading) result = factory.createBinaryExpression(factory.createStringLiteral(leading), ts.SyntaxKind.PlusToken, result);
          if (trailing) result = factory.createBinaryExpression(result, ts.SyntaxKind.PlusToken, factory.createStringLiteral(trailing));
          return result;
        };
        const visit: ts.Visitor = (node) => {
          if (ts.isJsxText(node)) {
            if (sourceToKey[normalize(node.text)] === undefined) return node;
            return factory.createJsxExpression(undefined, fragment(node.text));
          }
          if (ts.isJsxAttribute(node) && isDisplayAttribute(node)
            && node.initializer !== undefined && ts.isStringLiteral(node.initializer)) {
            if (sourceToKey[normalize(node.initializer.text)] !== undefined) {
              return factory.updateJsxAttribute(node, node.name,
                factory.createJsxExpression(undefined, fragment(node.initializer.text)));
            }
          }
          if ((ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) && isDisplayExpression(node)) {
            return fragment(node.text);
          }
          if (ts.isTemplateExpression(node) && isDisplayExpression(node)) {
            let result = fragment(node.head.text);
            for (const span of node.templateSpans) {
              result = factory.createBinaryExpression(result, ts.SyntaxKind.PlusToken,
                ts.visitNode(span.expression, visit) as ts.Expression);
              result = factory.createBinaryExpression(result, ts.SyntaxKind.PlusToken, fragment(span.literal.text));
            }
            return result;
          }
          return ts.visitEachChild(node, visit, context);
        };
        return (node) => {
          const output = ts.visitNode(node, visit) as ts.SourceFile;
          if (!translated) return output;
          const importDeclaration = factory.createImportDeclaration(undefined,
            factory.createImportClause(false, undefined, factory.createNamedImports([
              factory.createImportSpecifier(false, factory.createIdentifier("t"), helper),
            ])), factory.createStringLiteral("statistical-twin-i18n/translate"));
          return factory.updateSourceFile(output, [importDeclaration, ...output.statements]);
        };
      };
      const result = ts.transform(sourceFile, [transformer]);
      const output = ts.createPrinter().printFile(result.transformed[0]);
      result.dispose();
      return { code: output, map: null };
    },
  };
}
