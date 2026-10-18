#!/usr/bin/env node
// T260: fail the build if the JS that index.html loads eagerly (the entry module
// script plus any modulepreload chunks) grows past a budget. Lazy-loaded screens
// (handoff, pattern library, tour — see App.tsx) are fetched on demand and are not
// part of this sum; that's the point of #237's lazy-loading.
import { readFileSync, existsSync } from 'node:fs'
import { gzipSync } from 'node:zlib'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

// Started as the gzipped entry chunk + modulepreload chunks on main right after
// #237 landed (83848 bytes), rounded up ~10%. Raised for T442: the redesign
// shell, the person view and the replays added 2026-10-17 are always-on screens
// and measured 92536 bytes together, over the old 92200 budget; T421's eager
// resident-detail charts took that to 94908. Raised again for T432: the live
// session's task map became a node graph (a layered layout and an SVG edge
// layer, +1600 bytes), and main was already at 95899 of the old 96000 budget —
// 101 bytes of headroom. 98500 leaves about a kilobyte, which is as much as the
// always-on screens have ever had. Raise this only alongside a PR that explains
// the growth (a new eager dependency, a new always-on screen); do not raise it
// to silence this check — a new screen off the demo path still has to be lazy().
const BUDGET_BYTES = 98_500

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
