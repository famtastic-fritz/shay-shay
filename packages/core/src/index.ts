export * from './config.js';
export * from './schema-registry.js';
export * from './event-bus.js';
export * from './credential-vault.js';

import { ShayConfig, loadConfig } from './config.js';
import { SchemaRegistry } from './schema-registry.js';
import { EventBus } from './event-bus.js';
import { CredentialVault } from './credential-vault.js';

export interface CoreContext {
  config: ShayConfig;
  schemaRegistry: SchemaRegistry;
  eventBus: EventBus;
  credentialVault: CredentialVault;
}

export function createCore(configPath?: string): CoreContext {
  const config = loadConfig(configPath);
  const schemaRegistry = new SchemaRegistry();
  const eventBus = new EventBus();
  const credentialVault = new CredentialVault();

  return {
    config,
    schemaRegistry,
    eventBus,
    credentialVault,
  };
}
