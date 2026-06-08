import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import os from 'node:os';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { EventBus, ShayEvent } from '../src/event-bus.js';
import { SchemaRegistry, ValidationError } from '../src/schema-registry.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const schemasDir = path.resolve(__dirname, '../../../schemas');

describe('EventBus', () => {
  let registry: SchemaRegistry;
  let eventBus: EventBus;
  let logFilePath: string;

  beforeEach(() => {
    registry = new SchemaRegistry();
    registry.loadFromDir(schemasDir);

    logFilePath = path.join(os.tmpdir(), `event-log-${Date.now()}.jsonl`);
    eventBus = new EventBus(registry, logFilePath);
  });

  afterEach(() => {
    if (fs.existsSync(logFilePath)) {
      fs.unlinkSync(logFilePath);
    }
  });

  it('emit appends a JSON line to the log file', () => {
    const event: ShayEvent = {
      id: '550e8400-e29b-41d4-a716-446655440000',
      type: 'test:created',
      payload: { msg: 'hello' },
      timestamp: '2026-06-08T12:00:00Z',
      source: 'test-runner',
    };

    eventBus.emit(event);

    expect(fs.existsSync(logFilePath)).toBe(true);
    const content = fs.readFileSync(logFilePath, 'utf-8');
    const line = content.trim();
    const parsed = JSON.parse(line);

    expect(parsed.type).toBe('test:created');
    expect(parsed.id).toBe('550e8400-e29b-41d4-a716-446655440000');
  });

  it('subscriber is called on matching event type', () => {
    let called = false;
    let receivedEvent: ShayEvent | undefined;

    eventBus.subscribe('test:event', (event) => {
      called = true;
      receivedEvent = event;
    });

    const event: ShayEvent = {
      id: '550e8400-e29b-41d4-a716-446655440001',
      type: 'test:event',
      payload: { data: 'test' },
      timestamp: '2026-06-08T12:00:00Z',
      source: 'test-runner',
    };

    eventBus.emit(event);

    expect(called).toBe(true);
    expect(receivedEvent?.type).toBe('test:event');
  });

  it('emit throws ValidationError for invalid event (missing required fields)', () => {
    const invalidEvent = {
      type: 'test:event',
      payload: { data: 'test' },
    };

    expect(() => {
      eventBus.emit(invalidEvent as ShayEvent);
    }).toThrow(ValidationError);
  });

  it('unsubscribe function prevents further handler calls', () => {
    let callCount = 0;

    const unsub = eventBus.subscribe('test:unsubscribe', () => {
      callCount++;
    });

    const event: ShayEvent = {
      id: '550e8400-e29b-41d4-a716-446655440002',
      type: 'test:unsubscribe',
      payload: {},
      timestamp: '2026-06-08T12:00:00Z',
      source: 'test-runner',
    };

    eventBus.emit(event);
    expect(callCount).toBe(1);

    unsub();

    eventBus.emit(event);
    expect(callCount).toBe(1);
  });

  it('multiple subscribers on same type all receive the event', () => {
    let count1 = 0;
    let count2 = 0;

    eventBus.subscribe('test:multi', () => {
      count1++;
    });

    eventBus.subscribe('test:multi', () => {
      count2++;
    });

    const event: ShayEvent = {
      id: '550e8400-e29b-41d4-a716-446655440003',
      type: 'test:multi',
      payload: {},
      timestamp: '2026-06-08T12:00:00Z',
      source: 'test-runner',
    };

    eventBus.emit(event);

    expect(count1).toBe(1);
    expect(count2).toBe(1);
  });
});
