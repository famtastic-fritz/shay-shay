import fs from 'fs';
import path from 'path';

export interface CheckResult {
  name: string;
  pass: boolean;
  message: string;
}

export interface GateVerdict {
  pass: boolean;
  checks: CheckResult[];
  issues: string[];
}

const EXPECTED_PACKAGES = [
  'core',
  'memory',
  'brain',
  'ingestion',
  'doctor',
  'capabilities',
  'bridge',
  'surfaces',
];

export async function runGate(targetDir: string): Promise<GateVerdict> {
  const checks: CheckResult[] = [];
  const issues: string[] = [];

  // Check 1: targetDir exists and is a directory
  let check1Pass = false;
  try {
    const stat = fs.statSync(targetDir);
    check1Pass = stat.isDirectory();
    checks.push({
      name: 'Target directory exists',
      pass: check1Pass,
      message: check1Pass ? `${targetDir} is a valid directory` : `${targetDir} is not a directory`,
    });
  } catch {
    checks.push({
      name: 'Target directory exists',
      pass: false,
      message: `${targetDir} does not exist or is not accessible`,
    });
    issues.push(`Target directory ${targetDir} not found`);
  }

  if (!check1Pass) {
    return {
      pass: false,
      checks,
      issues,
    };
  }

  // Check 2: packages/ subdirectory exists
  const packagesDir = path.join(targetDir, 'packages');
  let check2Pass = false;
  try {
    const stat = fs.statSync(packagesDir);
    check2Pass = stat.isDirectory();
    checks.push({
      name: 'packages/ directory exists',
      pass: check2Pass,
      message: check2Pass ? 'packages/ directory found' : 'packages/ is not a directory',
    });
  } catch {
    checks.push({
      name: 'packages/ directory exists',
      pass: false,
      message: 'packages/ directory does not exist',
    });
    issues.push('packages/ subdirectory not found');
  }

  // Check 3: package.json at root exists and has workspaces field
  const rootPackageJsonPath = path.join(targetDir, 'package.json');
  let check3Pass = false;
  try {
    const content = fs.readFileSync(rootPackageJsonPath, 'utf-8');
    const pkg = JSON.parse(content);
    check3Pass = Array.isArray(pkg.workspaces) && pkg.workspaces.length > 0;
    checks.push({
      name: 'Root package.json with workspaces',
      pass: check3Pass,
      message: check3Pass ? 'workspaces field is defined' : 'workspaces field is missing or invalid',
    });
    if (!check3Pass) {
      issues.push('Root package.json does not define workspaces');
    }
  } catch (err) {
    checks.push({
      name: 'Root package.json with workspaces',
      pass: false,
      message: `Failed to read or parse root package.json: ${err instanceof Error ? err.message : String(err)}`,
    });
    issues.push('Root package.json is missing or invalid');
  }

  // Check 4: tsconfig.base.json exists
  const tsConfigPath = path.join(targetDir, 'tsconfig.base.json');
  let check4Pass = false;
  try {
    check4Pass = fs.existsSync(tsConfigPath);
    checks.push({
      name: 'tsconfig.base.json exists',
      pass: check4Pass,
      message: check4Pass ? 'tsconfig.base.json found' : 'tsconfig.base.json not found',
    });
    if (!check4Pass) {
      issues.push('tsconfig.base.json is missing');
    }
  } catch {
    checks.push({
      name: 'tsconfig.base.json exists',
      pass: false,
      message: 'Failed to check tsconfig.base.json',
    });
    issues.push('tsconfig.base.json check failed');
  }

  // Check 5: shay.config.yaml exists
  const shayConfigPath = path.join(targetDir, 'shay.config.yaml');
  let check5Pass = false;
  try {
    check5Pass = fs.existsSync(shayConfigPath);
    checks.push({
      name: 'shay.config.yaml exists',
      pass: check5Pass,
      message: check5Pass ? 'shay.config.yaml found' : 'shay.config.yaml not found',
    });
    if (!check5Pass) {
      issues.push('shay.config.yaml is missing');
    }
  } catch {
    checks.push({
      name: 'shay.config.yaml exists',
      pass: false,
      message: 'Failed to check shay.config.yaml',
    });
    issues.push('shay.config.yaml check failed');
  }

  // Check 6: LOCKED.json exists and is valid JSON
  const lockedPath = path.join(targetDir, 'LOCKED.json');
  let check6Pass = false;
  try {
    if (fs.existsSync(lockedPath)) {
      const content = fs.readFileSync(lockedPath, 'utf-8');
      JSON.parse(content);
      check6Pass = true;
      checks.push({
        name: 'LOCKED.json exists and is valid',
        pass: true,
        message: 'LOCKED.json is valid JSON',
      });
    } else {
      checks.push({
        name: 'LOCKED.json exists and is valid',
        pass: false,
        message: 'LOCKED.json not found',
      });
      issues.push('LOCKED.json is missing');
    }
  } catch (err) {
    checks.push({
      name: 'LOCKED.json exists and is valid',
      pass: false,
      message: `LOCKED.json is invalid JSON: ${err instanceof Error ? err.message : String(err)}`,
    });
    issues.push('LOCKED.json is not valid JSON');
  }

  // Check 7: each expected package directory exists
  let check7Pass = true;
  const missingPackages: string[] = [];
  for (const pkg of EXPECTED_PACKAGES) {
    const pkgPath = path.join(packagesDir, pkg);
    if (!fs.existsSync(pkgPath)) {
      check7Pass = false;
      missingPackages.push(pkg);
    }
  }
  checks.push({
    name: 'All expected package directories exist',
    pass: check7Pass,
    message: check7Pass
      ? `All ${EXPECTED_PACKAGES.length} expected packages found`
      : `Missing packages: ${missingPackages.join(', ')}`,
  });
  if (!check7Pass) {
    issues.push(`Missing package directories: ${missingPackages.join(', ')}`);
  }

  // Check 8: each package has src/index.ts
  let check8Pass = true;
  const packagesWithoutIndex: string[] = [];
  for (const pkg of EXPECTED_PACKAGES) {
    const indexPath = path.join(packagesDir, pkg, 'src', 'index.ts');
    if (!fs.existsSync(indexPath)) {
      check8Pass = false;
      packagesWithoutIndex.push(pkg);
    }
  }
  checks.push({
    name: 'All packages have src/index.ts',
    pass: check8Pass,
    message: check8Pass
      ? 'All packages have src/index.ts'
      : `Missing src/index.ts in: ${packagesWithoutIndex.join(', ')}`,
  });
  if (!check8Pass) {
    issues.push(`Missing src/index.ts in: ${packagesWithoutIndex.join(', ')}`);
  }

  const pass = checks.every((c) => c.pass);

  return {
    pass,
    checks,
    issues,
  };
}
