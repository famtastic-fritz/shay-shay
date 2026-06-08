/**
 * @shay/bridge — OASF round-trip tests
 */

import { describe, it, expect } from 'vitest';
import { oasfToManifest, manifestToOasf } from '../src/oasf.js';
import type { OasfDescriptor } from '../src/oasf.js';
import type { CapabilityManifest } from '@shay/capabilities';

const fullDescriptor: OasfDescriptor = {
  id: 'oasf-cap',
  version: '1.2.3',
  name: 'OASF Cap',
  description: 'A capability described in OASF format',
  permissions: ['read', 'write'],
  dependencies: ['dep-a'],
  entrypoint: 'src/main.ts',
};

const minimalDescriptor: OasfDescriptor = {
  id: 'minimal',
  version: '0.1.0',
  name: 'Minimal',
  description: 'No optional fields',
};

describe('oasfToManifest()', () => {
  it('converts a full descriptor to a CapabilityManifest', () => {
    const manifest = oasfToManifest(fullDescriptor);
    expect(manifest.id).toBe('oasf-cap');
    expect(manifest.version).toBe('1.2.3');
    expect(manifest.name).toBe('OASF Cap');
    expect(manifest.permissions).toEqual(['read', 'write']);
    expect(manifest.dependencies).toEqual(['dep-a']);
    expect(manifest.entrypoint).toBe('src/main.ts');
  });

  it('converts a minimal descriptor without optional fields', () => {
    const manifest = oasfToManifest(minimalDescriptor);
    expect(manifest.id).toBe('minimal');
    expect(manifest.permissions).toBeUndefined();
    expect(manifest.dependencies).toBeUndefined();
    expect(manifest.entrypoint).toBeUndefined();
  });
});

describe('manifestToOasf()', () => {
  it('converts a CapabilityManifest to an OASF descriptor', () => {
    const manifest: CapabilityManifest = {
      id: 'cap-a',
      version: '2.0.0',
      name: 'Cap A',
      description: 'Description A',
      permissions: ['exec'],
    };
    const descriptor = manifestToOasf(manifest);
    expect(descriptor.id).toBe('cap-a');
    expect(descriptor.permissions).toEqual(['exec']);
  });
});

describe('oasf round-trip', () => {
  it('manifestToOasf(oasfToManifest(d)) === d for full descriptor', () => {
    const roundTripped = manifestToOasf(oasfToManifest(fullDescriptor));
    expect(roundTripped).toEqual(fullDescriptor);
  });

  it('oasfToManifest(manifestToOasf(m)) === m for a full manifest', () => {
    const manifest: CapabilityManifest = {
      id: 'cap-rt',
      version: '3.0.0',
      name: 'Cap RT',
      description: 'Round-trip test',
      permissions: ['p'],
      dependencies: ['d'],
      entrypoint: 'index.ts',
    };
    const roundTripped = oasfToManifest(manifestToOasf(manifest));
    expect(roundTripped).toEqual(manifest);
  });

  it('round-trip preserves absence of optional fields', () => {
    const rt = manifestToOasf(oasfToManifest(minimalDescriptor));
    expect(rt.permissions).toBeUndefined();
    expect(rt.dependencies).toBeUndefined();
    expect(rt.entrypoint).toBeUndefined();
  });
});
