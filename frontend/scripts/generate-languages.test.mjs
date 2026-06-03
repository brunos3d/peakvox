import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"

import { parseLanguages } from "./generate-languages.mjs"

const __dirname = dirname(fileURLToPath(import.meta.url))
const SOURCE = readFileSync(join(__dirname, "languages.source.md"), "utf8")

test("parses all 646 languages", () => {
  const langs = parseLanguages(SOURCE)
  assert.equal(langs.length, 646)
})

test("ignores header and separator rows", () => {
  const langs = parseLanguages(SOURCE)
  assert.ok(langs.every((l) => l.name !== "Language"))
  assert.ok(langs.every((l) => !l.id.includes("-")))
})

test("parses English with OmniVoice id, ISO code, and training hours", () => {
  const langs = parseLanguages(SOURCE)
  const english = langs.find((l) => l.name === "English")
  assert.deepEqual(english, {
    name: "English",
    id: "en",
    isoCode: "eng",
    trainingHours: 206061.1,
  })
})

test("preserves names with spaces and punctuation", () => {
  const langs = parseLanguages(SOURCE)
  assert.ok(langs.find((l) => l.name === "Adamawa Fulfulde"))
  assert.ok(langs.find((l) => l.name === "Aja (Benin)"))
})

test("every entry has non-empty id, name, isoCode", () => {
  const langs = parseLanguages(SOURCE)
  for (const l of langs) {
    assert.ok(l.id && l.id.length > 0, `empty id for ${l.name}`)
    assert.ok(l.name && l.name.length > 0)
    assert.ok(l.isoCode && l.isoCode.length > 0)
    assert.equal(typeof l.trainingHours, "number")
  }
})

test("ids are unique", () => {
  const langs = parseLanguages(SOURCE)
  const ids = new Set(langs.map((l) => l.id))
  assert.equal(ids.size, langs.length)
})
