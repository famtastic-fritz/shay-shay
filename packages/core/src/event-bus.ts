import { EventEmitter } from 'events';

export interface ShayEvent {
  type: string;
  payload: unknown;
  timestamp: string;
}

export class EventBus {
  private emitter: EventEmitter = new EventEmitter();

  emit<T extends ShayEvent>(event: T): void {
    this.emitter.emit(event.type, event);
  }

  on<T extends ShayEvent>(
    type: T['type'],
    handler: (event: T) => void
  ): void {
    this.emitter.on(type, handler);
  }

  off(type: string, handler: (...args: unknown[]) => void): void {
    this.emitter.off(type, handler);
  }

  removeAllListeners(type?: string): void {
    if (type) {
      this.emitter.removeAllListeners(type);
    } else {
      this.emitter.removeAllListeners();
    }
  }
}
