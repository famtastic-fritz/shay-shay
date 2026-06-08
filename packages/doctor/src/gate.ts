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

  // Check 9: schemas/ directory exists at repo root
  const schemasDir = path.join(targetDir, 'schemas');
  let check9Pass = false;
  try {
    const stat = fs.statSync(schemasDir);
    check9Pass = stat.isDirectory();
    checks.push({
      name: 'schemas/ directory exists at repo root',
      pass: check9Pass,
      message: check9Pass ? 'schemas/ directory found' : 'schemas/ is not a directory',
    });
  } catch {
    checks.push({
      name: 'schemas/ directory exists at repo root',
      pass: false,
      message: 'schemas/ directory does not exist',
    });
    issues.push('schemas/ directory not found at repo root');
  }

  // Check 10: spine schema files present
  const requiredSchemaFiles = [
    'event.schema.json',
    'config.schema.json',
    'capability-manifest.schema.json',
  ];
  let check10Pass = true;
  const missingSchemaFiles: string[] = [];
  for (const schemaFile of requiredSchemaFiles) {
    const schemaPath = path.join(schemasDir, schemaFile);
    if (!fs.existsSync(schemaPath)) {
      check10Pass = false;
      missingSchemaFiles.push(schemaFile);
    }
  }
  checks.push({
    name: 'spine schema files present',
    pass: check10Pass,
    message: check10Pass
      ? 'All required schema files found'
      : `Missing schema files: ${missingSchemaFiles.join(', ')}`,
  });
  if (!check10Pass) {
    issues.push(`Missing schema files: ${missingSchemaFiles.join(', ')}`);
  }

  // Check 11: core exports spine contracts
  let check11Pass = false;
  const missingExports: string[] = [];
  try {
    const coreIndexPath = path.join(
      targetDir,
      'packages',
      'core',
      'dist',
      'index.js'
    );
    const coreModule = await import(coreIndexPath);

    const requiredExports = [
      'loadConfig',
      'SchemaRegistry',
      'EventBus',
      'CredentialVault',
      'ValidationError',
      'CredentialNotFoundError',
    ];

    for (const exportName of requiredExports) {
      if (!(exportName in coreModule)) {
        missingExports.push(exportName);
      }
    }

    check11Pass = missingExports.length === 0;
    checks.push({
      name: 'core exports spine contracts',
      pass: check11Pass,
      message: check11Pass
        ? 'All required exports found in @shay/core'
        : `Missing exports: ${missingExports.join(', ')}`,
    });
  } catch (err) {
    checks.push({
      name: 'core exports spine contracts',
      pass: false,
      message: `Failed to import @shay/core: ${err instanceof Error ? err.message : String(err)}`,
    });
    issues.push(
      `Failed to import @shay/core or verify exports: ${err instanceof Error ? err.message : String(err)}`
    );
  }

  // Check 12: authority exports present in @shay/core source
  let check12Pass = false;
  try {
    const coreIndexSourcePath = path.join(
      targetDir,
      'packages',
      'core',
      'src',
      'index.ts'
    );
    const coreSourceContent = fs.readFileSync(coreIndexSourcePath, 'utf-8');
    check12Pass = coreSourceContent.includes('authority.js');
    checks.push({
      name: 'authority exports present in @shay/core source',
      pass: check12Pass,
      message: check12Pass
        ? 'authority.js export found in @shay/core/src/index.ts'
        : 'authority.js export not found in @shay/core/src/index.ts',
    });
    if (!check12Pass) {
      issues.push('authority.js export missing from @shay/core/src/index.ts');
    }
  } catch (err) {
    checks.push({
      name: 'authority exports present in @shay/core source',
      pass: false,
      message: `Failed to read @shay/core source: ${err instanceof Error ? err.message : String(err)}`,
    });
    issues.push(
      `Failed to read @shay/core/src/index.ts: ${err instanceof Error ? err.message : String(err)}`
    );
  }

  // Check 13: @shay/memory exports MemoryStore and EmbeddingProvider
  let check13Pass = false;
  try {
    const memoryIndexSourcePath = path.join(
      targetDir,
      'packages',
      'memory',
      'src',
      'index.ts'
    );
    const memorySourceContent = fs.readFileSync(memoryIndexSourcePath, 'utf-8');
    const hasMemoryStore = memorySourceContent.includes('MemoryStore');
    const hasEmbeddingProvider = memorySourceContent.includes('EmbeddingProvider');
    check13Pass = hasMemoryStore && hasEmbeddingProvider;
    checks.push({
      name: '@shay/memory exports MemoryStore and EmbeddingProvider',
      pass: check13Pass,
      message: check13Pass
        ? 'Both MemoryStore and EmbeddingProvider exports found in @shay/memory/src/index.ts'
        : `Missing exports: ${!hasMemoryStore ? 'MemoryStore' : ''}${!hasMemoryStore && !hasEmbeddingProvider ? ', ' : ''}${!hasEmbeddingProvider ? 'EmbeddingProvider' : ''}`,
    });
    if (!check13Pass) {
      const missing: string[] = [];
      if (!hasMemoryStore) missing.push('MemoryStore');
      if (!hasEmbeddingProvider) missing.push('EmbeddingProvider');
      issues.push(`Missing exports in @shay/memory/src/index.ts: ${missing.join(', ')}`);
    }
  } catch (err) {
    checks.push({
      name: '@shay/memory exports MemoryStore and EmbeddingProvider',
      pass: false,
      message: `Failed to read @shay/memory source: ${err instanceof Error ? err.message : String(err)}`,
    });
    issues.push(
      `Failed to read @shay/memory/src/index.ts: ${err instanceof Error ? err.message : String(err)}`
    );
  }

  // Check 14: @shay/brain exports Phase-3 exports (BrainRouter, ResumableRunner, ContextBudgetManager, AnticipationEngine)
  let check14Pass = false;
  try {
    const brainIndexSourcePath = path.join(
      targetDir,
      'packages',
      'brain',
      'src',
      'index.ts'
    );
    const brainSourceContent = fs.readFileSync(brainIndexSourcePath, 'utf-8');
    const requiredPhase3Exports = [
      'BrainRouter',
      'ResumableRunner',
      'ContextBudgetManager',
      'AnticipationEngine',
    ];
    const missingPhase3Exports: string[] = [];
    for (const exportName of requiredPhase3Exports) {
      if (!brainSourceContent.includes(exportName)) {
        missingPhase3Exports.push(exportName);
      }
    }
    check14Pass = missingPhase3Exports.length === 0;
    checks.push({
      name: '@shay/brain exports Phase-3 exports',
      pass: check14Pass,
      message: check14Pass
        ? 'All Phase-3 exports found in @shay/brain/src/index.ts: BrainRouter, ResumableRunner, ContextBudgetManager, AnticipationEngine'
        : `Missing Phase-3 exports: ${missingPhase3Exports.join(', ')}`,
    });
    if (!check14Pass) {
      issues.push(`Missing Phase-3 exports in @shay/brain/src/index.ts: ${missingPhase3Exports.join(', ')}`);
    }
  } catch (err) {
    checks.push({
      name: '@shay/brain exports Phase-3 exports',
      pass: false,
      message: `Failed to read @shay/brain source: ${err instanceof Error ? err.message : String(err)}`,
    });
    issues.push(
      `Failed to read @shay/brain/src/index.ts: ${err instanceof Error ? err.message : String(err)}`
    );
  }

  // Check 15: @shay/ingestion exports IngestionProtocol and adapters
  let check15Pass = false;
  try {
    const ingestionIndexSourcePath = path.join(
      targetDir,
      'packages',
      'ingestion',
      'src',
      'index.ts'
    );
    const ingestionSourceContent = fs.readFileSync(ingestionIndexSourcePath, 'utf-8');
    const requiredIngestionExports = [
      'IngestionProtocol',
      'HermesSkillAdapter',
      'ClaudeSkillAdapter',
      'McpToolAdapter',
      'A2aCardAdapter',
      'AdapterRegistry',
    ];
    const missingIngestionExports: string[] = [];
    for (const exportName of requiredIngestionExports) {
      if (!ingestionSourceContent.includes(exportName)) {
        missingIngestionExports.push(exportName);
      }
    }
    check15Pass = missingIngestionExports.length === 0;
    checks.push({
      name: '@shay/ingestion exports IngestionProtocol and adapters',
      pass: check15Pass,
      message: check15Pass
        ? 'All required exports found in @shay/ingestion/src/index.ts: IngestionProtocol, HermesSkillAdapter, ClaudeSkillAdapter, McpToolAdapter, A2aCardAdapter, AdapterRegistry'
        : `Missing exports: ${missingIngestionExports.join(', ')}`,
    });
    if (!check15Pass) {
      issues.push(`Missing exports in @shay/ingestion/src/index.ts: ${missingIngestionExports.join(', ')}`);
    }
  } catch (err) {
    checks.push({
      name: '@shay/ingestion exports IngestionProtocol and adapters',
      pass: false,
      message: `Failed to read @shay/ingestion source: ${err instanceof Error ? err.message : String(err)}`,
    });
    issues.push(
      `Failed to read @shay/ingestion/src/index.ts: ${err instanceof Error ? err.message : String(err)}`
    );
  }

  // Check 16: IngestionManifest schema exists at schemas/ingestion-manifest.schema.json
  let check16Pass = false;
  try {
    const ingestionManifestSchemaPath = path.join(targetDir, 'schemas', 'ingestion-manifest.schema.json');
    if (fs.existsSync(ingestionManifestSchemaPath)) {
      const schemaContent = fs.readFileSync(ingestionManifestSchemaPath, 'utf-8');
      const schema = JSON.parse(schemaContent);

      // Verify $id equals 'shay:ingestion-manifest'
      const hasCorrectId = schema.$id === 'shay:ingestion-manifest';

      // Verify required array includes 'source', 'version', 'ingestionDate'
      const hasRequiredFields =
        Array.isArray(schema.required) &&
        schema.required.includes('source') &&
        schema.required.includes('version') &&
        schema.required.includes('ingestionDate');

      check16Pass = hasCorrectId && hasRequiredFields;

      if (check16Pass) {
        checks.push({
          name: 'IngestionManifest schema exists at schemas/ingestion-manifest.schema.json',
          pass: true,
          message: 'ingestion-manifest.schema.json is valid with correct $id and required fields',
        });
      } else {
        const missingDetails: string[] = [];
        if (!hasCorrectId) missingDetails.push('$id is not "shay:ingestion-manifest"');
        if (!hasRequiredFields) missingDetails.push('required array missing source/version/ingestionDate');
        checks.push({
          name: 'IngestionManifest schema exists at schemas/ingestion-manifest.schema.json',
          pass: false,
          message: `ingestion-manifest.schema.json is invalid: ${missingDetails.join(', ')}`,
        });
        issues.push(`ingestion-manifest.schema.json validation failed: ${missingDetails.join(', ')}`);
      }
    } else {
      checks.push({
        name: 'IngestionManifest schema exists at schemas/ingestion-manifest.schema.json',
        pass: false,
        message: 'ingestion-manifest.schema.json not found',
      });
      issues.push('ingestion-manifest.schema.json is missing');
    }
  } catch (err) {
    checks.push({
      name: 'IngestionManifest schema exists at schemas/ingestion-manifest.schema.json',
      pass: false,
      message: `Failed to read or parse ingestion-manifest.schema.json: ${err instanceof Error ? err.message : String(err)}`,
    });
    issues.push(
      `Failed to validate ingestion-manifest.schema.json: ${err instanceof Error ? err.message : String(err)}`
    );
  }

  // Check 17 (Phase 5): @shay/capabilities exports CapabilityRegistry
  let check17Pass = false;
  try {
    const capIndexSourcePath = path.join(
      targetDir,
      'packages',
      'capabilities',
      'src',
      'index.ts'
    );
    const capSourceContent = fs.readFileSync(capIndexSourcePath, 'utf-8');
    check17Pass = capSourceContent.includes('CapabilityRegistry');
    checks.push({
      name: '@shay/capabilities exports CapabilityRegistry',
      pass: check17Pass,
      message: check17Pass
        ? 'CapabilityRegistry export found in @shay/capabilities/src/index.ts'
        : 'CapabilityRegistry export not found in @shay/capabilities/src/index.ts',
    });
    if (!check17Pass) {
      issues.push('CapabilityRegistry export missing from @shay/capabilities/src/index.ts');
    }
  } catch (err) {
    checks.push({
      name: '@shay/capabilities exports CapabilityRegistry',
      pass: false,
      message: `Failed to read @shay/capabilities source: ${err instanceof Error ? err.message : String(err)}`,
    });
    issues.push(
      `Failed to read @shay/capabilities/src/index.ts: ${err instanceof Error ? err.message : String(err)}`
    );
  }

  // Check 18 (Phase 5): @shay/bridge exports McpClient, a2a helpers, and oasf helpers
  let check18Pass = false;
  try {
    const bridgeIndexSourcePath = path.join(
      targetDir,
      'packages',
      'bridge',
      'src',
      'index.ts'
    );
    const bridgeSourceContent = fs.readFileSync(bridgeIndexSourcePath, 'utf-8');
    const requiredBridgeExports = [
      'McpClient',
      'parseAgentCard',
      'toCapabilityManifests',
      'produceAgentCard',
      'oasfToManifest',
      'manifestToOasf',
    ];
    const missingBridgeExports: string[] = [];
    for (const exportName of requiredBridgeExports) {
      if (!bridgeSourceContent.includes(exportName)) {
        missingBridgeExports.push(exportName);
      }
    }
    check18Pass = missingBridgeExports.length === 0;
    checks.push({
      name: '@shay/bridge exports McpClient + a2a + oasf helpers',
      pass: check18Pass,
      message: check18Pass
        ? 'All required Phase-5 bridge exports found in @shay/bridge/src/index.ts'
        : `Missing bridge exports: ${missingBridgeExports.join(', ')}`,
    });
    if (!check18Pass) {
      issues.push(`Missing exports in @shay/bridge/src/index.ts: ${missingBridgeExports.join(', ')}`);
    }
  } catch (err) {
    checks.push({
      name: '@shay/bridge exports McpClient + a2a + oasf helpers',
      pass: false,
      message: `Failed to read @shay/bridge source: ${err instanceof Error ? err.message : String(err)}`,
    });
    issues.push(
      `Failed to read @shay/bridge/src/index.ts: ${err instanceof Error ? err.message : String(err)}`
    );
  }

  // Check 19 (Phase 5): Phase-5 schemas exist (agent-card + oasf-descriptor)
  let check19Pass = false;
  const requiredPhase5Schemas = ['agent-card.schema.json', 'oasf-descriptor.schema.json'];
  const missingPhase5Schemas: string[] = [];
  for (const schemaFile of requiredPhase5Schemas) {
    const schemaPath = path.join(schemasDir, schemaFile);
    if (!fs.existsSync(schemaPath)) {
      missingPhase5Schemas.push(schemaFile);
    }
  }
  check19Pass = missingPhase5Schemas.length === 0;
  checks.push({
    name: 'Phase-5 schemas exist (agent-card, oasf-descriptor)',
    pass: check19Pass,
    message: check19Pass
      ? 'agent-card.schema.json and oasf-descriptor.schema.json found'
      : `Missing Phase-5 schema files: ${missingPhase5Schemas.join(', ')}`,
  });
  if (!check19Pass) {
    issues.push(`Missing Phase-5 schema files: ${missingPhase5Schemas.join(', ')}`);
  }

  // Check 20 (Phase 6): @shay/senses exports ReleaseMonitor and fetcher types
  let check20Pass = false;
  try {
    const sensesIndexSourcePath = path.join(
      targetDir,
      'packages',
      'senses',
      'src',
      'index.ts'
    );
    const sensesSourceContent = fs.readFileSync(sensesIndexSourcePath, 'utf-8');
    const requiredSensesExports = ['ReleaseMonitor', 'GithubReleasesFetcher', 'MockFetcher'];
    const missingSensesExports: string[] = [];
    for (const exportName of requiredSensesExports) {
      if (!sensesSourceContent.includes(exportName)) {
        missingSensesExports.push(exportName);
      }
    }
    check20Pass = missingSensesExports.length === 0;
    checks.push({
      name: '@shay/senses exports ReleaseMonitor + fetcher',
      pass: check20Pass,
      message: check20Pass
        ? 'ReleaseMonitor, GithubReleasesFetcher, MockFetcher exports found in @shay/senses/src/index.ts'
        : `Missing senses exports: ${missingSensesExports.join(', ')}`,
    });
    if (!check20Pass) {
      issues.push(`Missing exports in @shay/senses/src/index.ts: ${missingSensesExports.join(', ')}`);
    }
  } catch (err) {
    checks.push({
      name: '@shay/senses exports ReleaseMonitor + fetcher',
      pass: false,
      message: `Failed to read @shay/senses source: ${err instanceof Error ? err.message : String(err)}`,
    });
    issues.push(
      `Failed to read @shay/senses/src/index.ts: ${err instanceof Error ? err.message : String(err)}`
    );
  }

  // Check 21 (Phase 6): Phase-6 schemas exist (release-event + release-alert)
  let check21Pass = false;
  const requiredPhase6Schemas = ['release-event.schema.json', 'release-alert.schema.json'];
  const missingPhase6Schemas: string[] = [];
  for (const schemaFile of requiredPhase6Schemas) {
    const schemaPath = path.join(schemasDir, schemaFile);
    if (!fs.existsSync(schemaPath)) {
      missingPhase6Schemas.push(schemaFile);
    }
  }
  check21Pass = missingPhase6Schemas.length === 0;
  checks.push({
    name: 'Phase-6 schemas exist (release-event, release-alert)',
    pass: check21Pass,
    message: check21Pass
      ? 'release-event.schema.json and release-alert.schema.json found'
      : `Missing Phase-6 schema files: ${missingPhase6Schemas.join(', ')}`,
  });
  if (!check21Pass) {
    issues.push(`Missing Phase-6 schema files: ${missingPhase6Schemas.join(', ')}`);
  }

  const pass = checks.every((c) => c.pass);

  return {
    pass,
    checks,
    issues,
  };
}
