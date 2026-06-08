import { describe, it, expect, beforeEach } from 'vitest';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  SchemaRegistry,
  ValidationError,
  SchemaAlreadyRegisteredError,
} from '../src/schema-registry.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const schemasDir = path.resolve(__dirname, '../../../schemas');

describe('SchemaRegistry', () => {
  let registry: SchemaRegistry;

  beforeEach(() => {
    registry = new SchemaRegistry();
  });

  it('registers and validates a valid payload', () => {
    const schema = {
      type: 'object',
      required: ['name'],
      properties: {
        name: { type: 'string' },
        age: { type: 'number' },
      },
    };

    registry.register('test:person', schema);
    const validPayload = { name: 'Alice', age: 30 };

    expect(() => {
      registry.validate('test:person', validPayload);
    }).not.toThrow();
  });

  it('throws ValidationError for invalid payload', () => {
    const schema = {
      type: 'object',
      required: ['name'],
      properties: {
        name: { type: 'string' },
        age: { type: 'number' },
      },
    };

    registry.register('test:person', schema);
    const invalidPayload = { age: 30 };

    expect(() => {
      registry.validate('test:person', invalidPayload);
    }).toThrow(ValidationError);
  });

  it('throws SchemaAlreadyRegisteredError on duplicate register', () => {
    const schema = {
      type: 'object',
      properties: {
        id: { type: 'string' },
      },
    };

    registry.register('test:duplicate', schema);

    expect(() => {
      registry.register('test:duplicate', schema);
    }).toThrow(SchemaAlreadyRegisteredError);
  });

  it('loadFromDir loads schemas from the repo schemas/ dir', () => {
    registry.loadFromDir(schemasDir);

    expect(registry.has('shay:event')).toBe(true);
    expect(registry.has('shay:config')).toBe(true);
    expect(registry.has('shay:capability-manifest')).toBe(true);
  });

  it('validate rejects an event missing required fields', () => {
    registry.loadFromDir(schemasDir);
    const emptyEvent = {};

    expect(() => {
      registry.validate('shay:event', emptyEvent);
    }).toThrow(ValidationError);
  });
});
