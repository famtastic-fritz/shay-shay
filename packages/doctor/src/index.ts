export * from './types.js';
export { runGate, GateVerdict } from './gate.js';
export { Doctor } from './doctor.js';
export { memoryCheck, capabilityCheck, ingestionCheck, connectorCheck, authorityCheck, currencyCheck, configCheck } from './checks/index.js';

export function printVerdict(verdict: any): void {
  const status = verdict.pass ? '✓ PASS' : '✗ FAIL';
  console.log(`\n${status}\n`);

  if (verdict.checks && verdict.checks.length > 0) {
    console.log('Checks:');
    for (const check of verdict.checks) {
      const marker = check.pass ? '  ✓' : '  ✗';
      console.log(`${marker} ${check.name}`);
      console.log(`     ${check.message}`);
    }
  }

  if (verdict.issues && verdict.issues.length > 0) {
    console.log('\nIssues:');
    for (const issue of verdict.issues) {
      console.log(`  - ${issue}`);
    }
  }

  console.log('');
}
