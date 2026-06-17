#!/usr/bin/env node
/**
 * migrate_api_base.mjs — Complete file.
 *
 * One-time codemod for the entire frontend/src tree.
 * Replaces every hardcoded http://localhost:8000 and ws://localhost:8000
 * with API_BASE / WS_BASE imported from src/config/api.ts, and inserts
 * the import automatically with the correct relative path.
 *
 * This exists specifically for files whose current content isn't known
 * ahead of time (any component/page not manually rewritten already) —
 * it scans and fixes them safely without guessing at their logic.
 *
 * Run from inside the frontend/ directory:
 *   node migrate_api_base.mjs
 */
import fs from 'fs'
import path from 'path'

const SRC_DIR    = path.resolve('src')
const CONFIG_DIR = path.join(SRC_DIR, 'config')
const EXTENSIONS = ['.ts', '.tsx']
const SKIP_DIRS  = new Set(['node_modules', 'dist', '.git'])

let filesScanned = 0
let filesChanged = 0
const changedFiles = []

function walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (SKIP_DIRS.has(entry.name)) continue
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      walk(full)
    } else if (EXTENSIONS.includes(path.extname(entry.name))) {
      processFile(full)
    }
  }
}

function relativeImportPath(fromFile) {
  const fromDir = path.dirname(fromFile)
  let rel = path.relative(fromDir, CONFIG_DIR)
  rel = rel.split(path.sep).join('/')
  if (!rel.startsWith('.')) rel = './' + rel
  return rel + '/api'
}

function processFile(filePath) {
  filesScanned++

  // Never touch the config file itself — it legitimately contains
  // the literal fallback string "http://localhost:8000"
  if (path.resolve(filePath) === path.resolve(CONFIG_DIR, 'api.ts')) return

  let content = fs.readFileSync(filePath, 'utf8')
  const original = content

  if (!content.includes('localhost:8000')) return

  // Quoted strings: 'http://localhost:8000/...' or "http://localhost:8000/..."
  content = content.replace(
    /(['"])http:\/\/localhost:8000([^'"]*)\1/g,
    (_m, _q, suffix) => `\`\${API_BASE}${suffix}\``
  )
  content = content.replace(
    /(['"])ws:\/\/localhost:8000([^'"]*)\1/g,
    (_m, _q, suffix) => `\`\${WS_BASE}${suffix}\``
  )

  // Backtick literals with no existing interpolation:
  // `http://localhost:8000/...`
  content = content.replace(
    /`http:\/\/localhost:8000([^`]*)`/g,
    (_m, suffix) => `\`\${API_BASE}${suffix}\``
  )
  content = content.replace(
    /`ws:\/\/localhost:8000([^`]*)`/g,
    (_m, suffix) => `\`\${WS_BASE}${suffix}\``
  )

  const usesApiBase = content.includes('${API_BASE}')
  const usesWsBase  = content.includes('${WS_BASE}')
  const names = []
  if (usesApiBase) names.push('API_BASE')
  if (usesWsBase)  names.push('WS_BASE')

  if (names.length === 0) {
    if (content !== original) {
      fs.writeFileSync(filePath, content, 'utf8')
      filesChanged++
      changedFiles.push(path.relative(process.cwd(), filePath))
    }
    return
  }

  const importPath = relativeImportPath(filePath)
  const escapedPath = importPath.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const alreadyImported = new RegExp(
    `import\\s*\\{[^}]*\\}\\s*from\\s*['"]${escapedPath}['"]`
  ).test(content)

  if (!alreadyImported) {
    const importLine = `import { ${names.join(', ')} } from '${importPath}'\n`
    const importLines = content.match(/^import .*\n/gm) || []
    if (importLines.length > 0) {
      const lastImport = importLines[importLines.length - 1]
      const idx = content.lastIndexOf(lastImport) + lastImport.length
      content = content.slice(0, idx) + importLine + content.slice(idx)
    } else {
      content = importLine + content
    }
  }

  if (content !== original) {
    fs.writeFileSync(filePath, content, 'utf8')
    filesChanged++
    changedFiles.push(path.relative(process.cwd(), filePath))
  }
}

console.log('Scanning src/ for hardcoded localhost:8000 references...\n')
walk(SRC_DIR)

console.log(`Scanned ${filesScanned} files.`)
console.log(`Updated ${filesChanged} files:\n`)
changedFiles.forEach(f => console.log(`  ✔ ${f}`))

console.log('\nNext steps:')
console.log('  1. grep -R "localhost:8000" src --exclude-dir=config')
console.log('     (the only acceptable match is the fallback inside config/api.ts itself)')
console.log('  2. npx tsc -b --noEmit')
console.log('  3. npm run build')
