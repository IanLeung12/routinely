#!/usr/bin/env node
// T260: fail the build if the JS that index.html loads eagerly (the entry module
// script plus any modulepreload chunks) grows past a budget. Lazy-loaded screens
// (handoff, pattern library, tour — see App.tsx) are fetched on demand and are not
// part of this sum; that's the point of #237's lazy-loading.
import { readFileSync, existsSync } from 'node:fs'
import { gzipSync } from 'node:zlib'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

// Measured as the gzipped size of the entry chunk + its modulepreload chunks on
// main right after #237 landed (83848 bytes), rounded up ~10%. Raised for T421:
// merging main alone (other screens' eager growth since the last raise) already
// measured 92536, over the old 92200 budget before this PR's change; the resident
// detail screen (eager, not lazy) also now renders BaselineChart and DriftCard on
// the shared LineChart chart kit, for 94908 total measured. Raise this only
// alongside a PR that explains the growth (new eager dependency, new always-on
// screen); do not raise it to silence this check.
const BUDGET_BYTES = 95_200

const webDir = dirname(dirname(fileURLToPath(import.meta.url)))
const distDir = join(webDir, 'dist')
const indexHtmlPath = join(distDir, 'index.html')

if (!existsSync(indexHtmlPath)) {
  console.error(`check-bundle: ${indexHtmlPath} not found. Run "npm run build" first.`)
  process.exit(1)
}

const html = readFileSync(indexHtmlPath, 'utf8')

/** Finds every `href="..."` or `src="..."` attribute on tags matching `tagRe`. */
function collectUrls(html, tagRe) {
  const urls = []
  const attrRe = /(?:href|src)="([^"]+)"/i
  for (const match of html.matchAll(tagRe)) {
    const attrMatch = attrRe.exec(match[0])
    if (attrMatch) urls.push(attrMatch[1])
  }
  return urls
}

// The entry module script, plus anything the browser is told to fetch eagerly
// via modulepreload — both load before first paint, unlike lazy route chunks.
const eagerUrls = [
  ...collectUrls(html, /<script\b[^>]*type="module"[^>]*>/gi),
  ...collectUrls(html, /<link\b[^>]*rel="modulepreload"[^>]*>/gi),
]

if (eagerUrls.length === 0) {
  console.error('check-bundle: found no <script type="module"> or modulepreload links in index.html.')
  process.exit(1)
}

let totalBytes = 0
console.log('First-load JS (gzipped):')
for (const url of eagerUrls) {
  const relativePath = url.replace(/^\//, '')
  const filePath = join(distDir, relativePath)
  const contents = readFileSync(filePath)
  const gzipped = gzipSync(contents)
  totalBytes += gzipped.length
  console.log(`  ${relativePath}: ${gzipped.length} bytes`)
}

console.log(`Total: ${totalBytes} bytes`)
console.log(`Budget: ${BUDGET_BYTES} bytes`)

if (totalBytes > BUDGET_BYTES) {
  console.error(
    `check-bundle: first-load JS is ${totalBytes - BUDGET_BYTES} bytes over budget. ` +
      'See web/README.md for how to investigate or raise the budget.',
  )
  process.exit(1)
}
