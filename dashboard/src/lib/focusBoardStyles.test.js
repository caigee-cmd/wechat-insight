import assert from "assert";
import fs from "fs";

const CSS_PATH = new URL("../styles.css", import.meta.url);

function ruleBlocksForSelector(css, selector) {
  const rulePattern = /([^{}]+)\{([^{}]*)\}/g;
  return Array.from(css.matchAll(rulePattern)).filter((match) => {
    return match[1].split(",").map((item) => item.trim()).includes(selector);
  });
}

function lastDeclarationForSelector(css, selector, property) {
  const rules = ruleBlocksForSelector(css, selector);
  const declarations = rules
    .map((match) => match[2])
    .flatMap((body) => body.split(";"))
    .map((line) => line.trim())
    .filter(Boolean);
  const matchingDeclarations = declarations.filter((line) => line.startsWith(`${property}:`));
  const declaration = matchingDeclarations[matchingDeclarations.length - 1];
  return declaration?.slice(property.length + 1).trim();
}

function run() {
  const css = fs.readFileSync(CSS_PATH, "utf8");

  assert.equal(lastDeclarationForSelector(css, ".focus-board", "color"), "var(--text)");
  console.log("focus-board style contrast check passed");
}

run();
