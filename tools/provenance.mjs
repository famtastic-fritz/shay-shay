#!/usr/bin/env node
import { createHash } from 'crypto';
import { readFileSync, writeFileSync, existsSync } from 'fs';
import { resolve } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = resolve(__filename, '..');
const repoRoot = resolve(__dirname, '..');

function stamp() {
  const args = process.argv.slice(2);

  if (args.length < 2) {
    console.error('Usage: node provenance.mjs <subsystem> <phase>');
    console.error('Example: node provenance.mjs core 1');
    process.exit(1);
  }

  const [subsystem, phaseArg] = args;
  const phase = parseInt(phaseArg, 10);

  if (isNaN(phase) || phase < 0) {
    console.error('Error: phase must be a non-negative integer');
    process.exit(1);
  }

  const lockedPath = resolve(repoRoot, 'LOCKED.json');
  let locked = {};

  if (existsSync(lockedPath)) {
    try {
      const content = readFileSync(lockedPath, 'utf-8');
      locked = JSON.parse(content);
    } catch (err) {
      console.error('Error reading LOCKED.json:', err.message);
      process.exit(1);
    }
  }

  const distPath = resolve(repoRoot, 'packages', subsystem, 'dist', 'index.js');
  let checksum = 'pending';

  if (existsSync(distPath)) {
    try {
      const content = readFileSync(distPath, 'utf-8');
      checksum = createHash('sha256').update(content).digest('hex');
    } catch (err) {
      console.error(`Error reading dist file for ${subsystem}:`, err.message);
      process.exit(1);
    }
  }

  const entry = {
    phase,
    shippedAt: new Date().toISOString(),
    checksum,
  };

  locked[subsystem] = entry;

  try {
    writeFileSync(lockedPath, JSON.stringify(locked, null, 2) + '\n', 'utf-8');
    console.log(`Stamped ${subsystem} phase ${phase} at ${entry.shippedAt}`);
    console.log(`Checksum: ${checksum}`);
    process.exit(0);
  } catch (err) {
    console.error('Error writing LOCKED.json:', err.message);
    process.exit(1);
  }
}

stamp();
