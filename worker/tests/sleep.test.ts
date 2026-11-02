import assert from 'node:assert/strict';
import { test } from 'node:test';
import { formatSleepMessage } from '../src/sleep.ts';

test('23:00 Vietnam adds 15 minutes then shows exactly five wake-up times', () => {
  const text = formatSleepMessage(new Date('2026-11-01T16:00:00Z'));
  const lines = text.split('\n').filter(line => /^• \d chu kỳ/.test(line));
  assert.equal(lines.length, 5);
  for (const [index, time] of ['00:45', '02:15', '03:45', '05:15', '06:45'].entries()) {
    assert.match(lines[index], new RegExp(`${index + 1} chu kỳ`));
    assert.ok(lines[index].includes(`<code>${time}</code> thức dậy`), lines[index]);
  }
  assert.match(lines[0], /1 giờ 30 phút/);
  assert.match(lines[4], /7 giờ 30 phút/);
  assert.match(text, /15 phút/);
  assert.match(text, /ước tính/);
});

test('daytime sleep formats wake-up times correctly', () => {
  const text = formatSleepMessage(new Date('2026-11-01T03:00:00Z'));
  assert.match(text, /<code>11:45<\/code> thức dậy/);
  assert.match(text, /<code>17:45<\/code> thức dậy/);
});

test('a wake-up exactly at midnight uses 00:00', () => {
  const text = formatSleepMessage(new Date('2026-11-01T15:15:00Z'));
  assert.match(text, /<code>00:00<\/code> thức dậy/);
  assert.doesNotMatch(text, /24:00/);
});

test('default time uses the current instant', (t) => {
  t.mock.timers.enable({ apis: ['Date'], now: new Date('2026-11-01T16:00:00Z') });
  assert.match(formatSleepMessage(), /<code>06:45<\/code> thức dậy/);
});
