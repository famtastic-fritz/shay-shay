import fs from 'node:fs';
import path from 'node:path';
import { SchemaRegistry } from './schema-registry.js';

export interface ShayEvent {
  id: string;
  type: string;
  payload: unknown;
  timestamp: string;
  source: string;
}

export class EventBus {
  private subscribers: Map<string, Set<(e: ShayEvent) => void>> = new Map();
  private schemaRegistry: SchemaRegistry;
  private logPath: string;

  constructor(schemaRegistry: SchemaRegistry, logPath: string) {
    this.schemaRegistry = schemaRegistry;
    this.logPath = logPath;
  }

  emit(event: ShayEvent): void {
    this.schemaRegistry.validate('shay:event', event);

    fs.appendFileSync(this.logPath, JSON.stringify(event) + '\n');

    const handlers = this.subscribers.get(event.type);
    if (handlers) {
      for (const handler of handlers) {
        handler(event);
      }
    }
  }

  subscribe(type: string, handler: (e: ShayEvent) => void): () => void {
    if (!this.subscribers.has(type)) {
      this.subscribers.set(type, new Set());
    }
    const handlers = this.subscribers.get(type)!;
    handlers.add(handler);

    return () => {
      handlers.delete(handler);
      if (handlers.size === 0) {
        this.subscribers.delete(type);
      }
    };
  }
}
